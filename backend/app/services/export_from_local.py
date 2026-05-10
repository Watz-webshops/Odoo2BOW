"""
XML export uit lokale Odoo-mirror data (geen Odoo connectie nodig).
Stelt een BelcotaxRequest samen door registraties te joinen met events + partners,
en delegeert naar de bestaande export pipeline.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.export import Export
from app.models.export_participation import ExportParticipation
from app.models.odoo_event import OdooEvent
from app.models.odoo_partner import OdooPartner
from app.models.odoo_registration import OdooRegistration
from app.models.organization import Organization
from app.schemas.export import (
    AddressSchema,
    BelcotaxRequest,
    ChildSchema,
    ContactSchema,
    ExportSummary,
    ExportSummaryWarning,
    OrganizationPayload,
    ParentSchema,
    ParticipationSchema,
)
from app.services.aggregation import aggregate
from app.services.rrn_validator import validate_rrn
from app.services.xml_generator import generate_bow_xml
from app.services.xsd_validator import validate_xml


async def _build_request_from_local(
    db: AsyncSession, org: Organization, income_year: int,
) -> BelcotaxRequest:
    """Bouw BelcotaxRequest uit lokale tabellen voor een specifiek jaar."""
    # Pak registraties + events binnen het jaar (state='open')
    year_start = date(income_year, 1, 1)
    year_end = date(income_year, 12, 31)

    stmt = (
        select(OdooRegistration, OdooEvent, OdooPartner)
        .join(OdooEvent,
              (OdooEvent.org_id == OdooRegistration.org_id)
              & (OdooEvent.odoo_id == OdooRegistration.event_odoo_id))
        .join(OdooPartner,
              (OdooPartner.org_id == OdooRegistration.org_id)
              & (OdooPartner.odoo_id == OdooRegistration.partner_odoo_id))
        .where(
            OdooRegistration.org_id == org.id,
            OdooRegistration.state == "open",
            OdooEvent.date_begin >= year_start,
            OdooEvent.date_begin <= year_end,
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    participations: list[ParticipationSchema] = []
    for reg, event, partner in rows:
        if not reg.child_rrn or not reg.parent_rrn:
            continue  # skip — vereist RRN's
        days = (event.date_end - event.date_begin).days + 1 if event.date_begin and event.date_end else 1
        amount_paid = (reg.ticket_price_cents or 0) / 100.0

        # Splits parent name in voornaam/achternaam
        parent_name = (partner.name or "").strip()
        parts = parent_name.split(" ", 1)
        parent_first = parts[0] if parts else ""
        parent_last = parts[1] if len(parts) > 1 else ""

        participations.append(ParticipationSchema(
            event_id=str(event.odoo_id),
            event_name=event.name or "",
            start_date=event.date_begin,
            end_date=event.date_end,
            days=days,
            amount_paid=amount_paid,
            status="confirmed",
            parent=ParentSchema(
                rrn=reg.parent_rrn,
                first_name=parent_first,
                last_name=parent_last,
                address=AddressSchema(
                    street=partner.street or "",
                    zip=partner.zip or "",
                    city=partner.city or "",
                    country_code=150,
                ),
            ),
            child=ChildSchema(
                rrn=reg.child_rrn,
                first_name=reg.child_first_name or "",
                last_name=reg.child_last_name or "",
            ),
        ))

    if not participations:
        raise ValueError(f"Geen geldige inschrijvingen gevonden voor {income_year}")

    return BelcotaxRequest(
        income_year=income_year,
        organization=OrganizationPayload(
            kbo=org.kbo,
            name=org.name,
            address=AddressSchema(
                street=org.street or "",
                zip=org.zip or "",
                city=org.city or "",
                country_code=org.country_code,
            ),
            language_code=org.language_code,
            contact=ContactSchema(
                name=org.contact_name or org.name,
                email=org.contact_email or "",
                phone=org.contact_phone or "",
            ),
        ),
        participations=participations,
    )


async def process_export_from_local(export_id: str, org_id: uuid.UUID, income_year: int) -> None:
    """BackgroundTask: bouw payload uit lokale data + delegeer aan export pipeline."""
    async with AsyncSessionLocal() as db:
        export = await db.get(Export, export_id)
        if not export:
            return

        export.status = "processing"
        await db.commit()

        try:
            org = await db.get(Organization, org_id)
            if not org:
                raise ValueError("Organisatie niet gevonden")

            request = await _build_request_from_local(db, org, income_year)

            # Valideer RRNs + bereken birth_dates
            errors: list[str] = []
            birth_dates: dict[str, str] = {}
            rrns = set()
            for p in request.participations:
                rrns.add(p.parent.rrn)
                rrns.add(p.child.rrn)
            for rrn in rrns:
                info = validate_rrn(rrn)
                if not info.is_valid:
                    errors.append(f"RRN fout: {info.error}")
                elif info.formatted:
                    birth_dates[rrn] = info.formatted

            if errors:
                export.status = "failed"
                export.error_detail = "\n".join(errors)
                export.summary_json = {"errors": errors, "warnings": []}
                export.completed_at = datetime.now(UTC)
                await db.commit()
                return

            result = aggregate(request, birth_dates)
            if not result.fiches:
                export.status = "failed"
                export.error_detail = "Geen geldige fiches na aggregatie"
                export.completed_at = datetime.now(UTC)
                await db.commit()
                return

            xml_bytes = generate_bow_xml(
                request.income_year, request.organization, result.fiches,
                export_ref=export_id,
            )

            xsd_ok, xsd_errors = validate_xml(xml_bytes)
            xsd_warnings = [f"XSD: {e}" for e in xsd_errors[:5]] if not xsd_ok else []

            warnings = [
                ExportSummaryWarning(
                    type=w["type"], parent_rrn=w["parent_rrn"],
                    child_rrn=w["child_rrn"], message=w["message"],
                )
                for w in result.warnings
            ]

            summary = ExportSummary(
                fiche_count=len(result.fiches),
                total_amount_cents=sum(f.total_amount_cents for f in result.fiches),
                total_days=sum(f.total_days for f in result.fiches),
                skipped_count=result.skipped_count,
                warnings=warnings,
                errors=[],
            )

            export.status = "completed"
            export.xml_content = xml_bytes.decode("utf-8")
            export.summary_json = summary.model_dump()
            export.completed_at = datetime.now(UTC)

            # Sla participaties op voor /me/participations + /me/beneficiaries query (legacy)
            for p in request.participations:
                rinfo = validate_rrn(p.child.rrn)
                db.add(ExportParticipation(
                    export_id=export_id,
                    event_id=p.event_id, event_name=p.event_name,
                    start_date=p.start_date, end_date=p.end_date,
                    days=p.days,
                    amount_paid_cents=round(p.amount_paid * 100),
                    status=p.status,
                    parent_rrn=p.parent.rrn,
                    parent_first_name=p.parent.first_name,
                    parent_last_name=p.parent.last_name,
                    child_rrn=p.child.rrn,
                    child_first_name=p.child.first_name,
                    child_last_name=p.child.last_name,
                    child_birth_date=rinfo.birth_date if rinfo.is_valid else None,
                ))

            await db.commit()

        except Exception as exc:
            export.status = "failed"
            export.error_detail = str(exc)
            export.completed_at = datetime.now(UTC)
            await db.commit()
            raise
