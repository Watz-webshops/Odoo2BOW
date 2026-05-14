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
    MultilingualNameSchema,
    OrganizationPayload,
    ParentSchema,
    ParticipationSchema,
)
from app.schemas.export_preview import InvalidRegistration
from app.services.aggregation import aggregate
from app.services.day_classifier import classify_event
from app.services.rrn_validator import validate_rrn
from app.services.xml_generator import generate_bow_xml
from app.services.xsd_validator import validate_xml


async def _build_request_from_local(
    db: AsyncSession, org: Organization, income_year: int,
) -> BelcotaxRequest:
    """Bouw BelcotaxRequest uit lokale tabellen voor een specifiek jaar.

    Inkomstenjaar = het jaar waarin de LAATSTE dag van het event valt. Daarom
    filteren we op `OdooEvent.date_end` — een kamp 28/12/2021 → 05/01/2022 hoort
    bij inkomstenjaar 2022.
    """
    year_start = datetime(income_year, 1, 1)
    year_end = datetime(income_year, 12, 31, 23, 59, 59)

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
            OdooEvent.date_end >= year_start,
            OdooEvent.date_end <= year_end,
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    participations: list[ParticipationSchema] = []
    for reg, event, partner in rows:
        if not reg.child_rrn or not reg.parent_rrn:
            continue  # skip — vereist RRN's

        # Uren-classificatie via BOW halve-dag regel.
        classification = classify_event(event.date_begin, event.date_end)
        if classification is None:
            # Onbruikbare datetimes — registreer de registratie wel met 1 dag/2 halve dagen
            # zodat de aggregatie hem niet stilletjes overslaat; aggregate() voegt een warning toe.
            start_date = event.date_begin.date() if event.date_begin else None
            end_date = event.date_end.date() if event.date_end else start_date
            if not start_date or not end_date:
                continue
            days = (end_date - start_date).days + 1
            half_days = days * 2
            hours_total: float | None = None
        else:
            start_date = event.date_begin.date()
            end_date = event.date_end.date()
            days = classification.days_in_range
            half_days = classification.half_days
            hours_total = classification.total_hours

        amount_paid = (reg.ticket_price_cents or 0) / 100.0

        # Splits parent name in voornaam/achternaam
        parent_name = (partner.name or "").strip()
        parts = parent_name.split(" ", 1)
        parent_first = parts[0] if parts else ""
        parent_last = parts[1] if len(parts) > 1 else ""

        participations.append(ParticipationSchema(
            event_id=str(event.odoo_id),
            event_name=event.name or "",
            start_date=start_date,
            end_date=end_date,
            days=max(days, 1),
            amount_paid=amount_paid,
            status="confirmed",
            half_days=half_days,
            hours_total=hours_total,
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
        organization=_build_org_payload(org),
        participations=participations,
    )


def invalid_reasons_for_row(
    parent_rrn: str | None,
    child_rrn: str | None,
    event_date_begin: datetime | None,
    event_date_end: datetime | None,
) -> list[str]:
    """Pure reden-detectie voor één registratie/event-paar (XML-blokkers)."""
    reasons: list[str] = []
    if not parent_rrn:
        reasons.append("RRN ouder ontbreekt")
    elif not validate_rrn(parent_rrn).is_valid:
        reasons.append("RRN ouder ongeldig")
    if not child_rrn:
        reasons.append("RRN kind ontbreekt")
    elif not validate_rrn(child_rrn).is_valid:
        reasons.append("RRN kind ongeldig")
    if not event_date_begin or not event_date_end:
        reasons.append("Begin- of einddatum event ontbreekt")
    return reasons


async def list_invalid_registrations(
    db: AsyncSession, org: Organization, income_year: int,
) -> list[InvalidRegistration]:
    """Geeft per inschrijving die NIET in de XML zal komen de redenen waarom.

    Gebruikt dezelfde filters als `_build_request_from_local` (state == 'open',
    event.date_end in income_year) maar valt niet weg op missende RRN's / datums —
    in plaats daarvan worden die als reden toegevoegd.
    """
    year_start = datetime(income_year, 1, 1)
    year_end = datetime(income_year, 12, 31, 23, 59, 59)

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
            OdooEvent.date_end >= year_start,
            OdooEvent.date_end <= year_end,
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    invalid: list[InvalidRegistration] = []
    for reg, event, partner in rows:
        reasons = invalid_reasons_for_row(
            reg.parent_rrn, reg.child_rrn, event.date_begin, event.date_end,
        )
        if not reasons:
            continue

        invalid.append(InvalidRegistration(
            registration_odoo_id=reg.odoo_id,
            event_name=event.name or "",
            event_date_begin=event.date_begin.strftime("%d-%m-%Y") if event.date_begin else None,
            event_date_end=event.date_end.strftime("%d-%m-%Y") if event.date_end else None,
            partner_name=partner.name or "",
            parent_rrn=reg.parent_rrn,
            child_first_name=reg.child_first_name,
            child_last_name=reg.child_last_name,
            child_rrn=reg.child_rrn,
            reasons=reasons,
        ))

    return invalid


def _build_org_payload(org: Organization) -> OrganizationPayload:
    """Bouw OrganizationPayload uit Organization DB-model, inclusief optionele FR/DE namen + cert-validity."""
    name_fr = None
    if org.name_fr and org.street_fr and org.city_fr:
        name_fr = MultilingualNameSchema(name=org.name_fr, street=org.street_fr, city=org.city_fr)
    name_de = None
    if org.name_de and org.street_de and org.city_de:
        name_de = MultilingualNameSchema(name=org.name_de, street=org.street_de, city=org.city_de)
    return OrganizationPayload(
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
        name_fr=name_fr,
        name_de=name_de,
        cert_validity_start=org.cert_validity_start,
        cert_validity_end=org.cert_validity_end,
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
