"""Bouwt een ExportPreviewResponse zonder XML te genereren of een Export op te slaan.

Volgt dezelfde data-pipeline als export_from_local maar stopt vóór generate_bow_xml.
Voor elke fiche wordt een dict met exact dezelfde XML-veldnamen teruggegeven, zodat
de frontend 1:1 kan tonen wat er in de XML zal komen.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.schemas.export_preview import (
    AangifteHeaderPreview,
    ExportPreviewResponse,
    FichePreview,
    PeriodPreview,
    PreviewSummary,
    TrailerPreview,
    VerzendingHeaderPreview,
)
from app.services.aggregation import Fiche28186Data, PeriodData, aggregate
from app.services.export_from_local import _build_request_from_local
from app.services.rrn_validator import validate_rrn


def _fmt(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def _period_to_preview(p: PeriodData) -> PeriodPreview:
    return PeriodPreview(
        begindate=_fmt(p.start),
        enddate=_fmt(p.end),
        amount_cents=p.amount_cents,
        half_days=p.half_days,
        xml_days=p.xml_days,
        daily_tariff_cents=p.daily_tariff_cents,
    )


def _fiche_missing_fields(f: Fiche28186Data) -> list[str]:
    missing: list[str] = []
    if not f.parent_rrn:
        missing.append("parent_rrn")
    if not f.parent_last_name:
        missing.append("parent_last_name")
    if not f.parent_address.street:
        missing.append("parent_address_street")
    if not f.parent_address.zip:
        missing.append("parent_address_zip")
    if not f.parent_address.city:
        missing.append("parent_address_city")
    if not f.child_rrn:
        missing.append("child_rrn")
    if not f.child_last_name:
        missing.append("child_last_name")
    if not f.child_birth_date_formatted:
        missing.append("child_birth_date")
    if not f.child_address.zip:
        missing.append("child_address_zip")
    if f.period1.xml_days == 0:
        missing.append("period1_days")
    return missing


def _fiche_to_preview(
    f: Fiche28186Data, *, seq: int, export_ref: str,
    warnings_for_pair: list[str],
) -> FichePreview:
    amount1 = f.period1.amount_cents
    amount2 = f.period2.amount_cents if f.period2 else 0
    total = amount1 + amount2  # f86_2064_totalamount
    return FichePreview(
        seq=seq,
        f2009_volgnummer=seq,
        f2010_referentie=f"{export_ref}-{seq}" if export_ref else str(seq),
        f2011_nationaalnr=f.parent_rrn,
        f2013_naam=f.parent_last_name,
        f2114_voornamen=f.parent_first_name,
        f2015_adres=f.parent_address.street,
        f2016_postcodebelgisch=f.parent_address.zip,
        f2017_gemeente=f.parent_address.city,
        f2018_landwoonplaats=f.parent_address.country_code,
        f86_2106_childname=f.child_last_name,
        f86_2107_childfirstname=f.child_first_name,
        f86_2153_nnchild=f.child_rrn,
        f86_2163_childbirthdate=f.child_birth_date_formatted,
        f86_2101_childcountry=f.child_address.country_code,
        f86_2102_childaddress=f.child_address.street,
        f86_2139_childpostnr=f.child_address.zip,
        f86_2140_childmunicipality=f.child_address.city,
        period1=_period_to_preview(f.period1),
        period2=_period_to_preview(f.period2) if f.period2 else None,
        f86_2059_totaalcontrole=amount1 + amount2 + total,
        f86_2064_totalamount=total,
        missing_fields=_fiche_missing_fields(f),
        warnings=warnings_for_pair,
    )


def _org_missing_for_preview(org: Organization) -> list[str]:
    missing: list[str] = []
    if not org.name_fr or not org.street_fr or not org.city_fr:
        missing.append("multilingual_fr")
    if not org.name_de or not org.street_de or not org.city_de:
        missing.append("multilingual_de")
    if not org.cert_validity_start:
        missing.append("cert_validity_start")
    if not org.cert_validity_end:
        missing.append("cert_validity_end")
    if not org.contact_email:
        missing.append("contact_email")
    if not org.contact_phone:
        missing.append("contact_phone")
    if not org.contact_name:
        missing.append("contact_name")
    return missing


async def preview_export(
    db: AsyncSession, org_id: uuid.UUID, income_year: int,
    *, test_mode: bool = False, export_ref: str = "",
) -> ExportPreviewResponse:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisatie niet gevonden")

    try:
        request = await _build_request_from_local(db, org, income_year)
    except ValueError as exc:
        # Geen geldige inschrijvingen — geef lege preview terug met error.
        return _empty_preview(income_year, org, test_mode, str(exc))

    # Valideer RRNs + bereken birth_dates (zelfde flow als echte export)
    errors: list[str] = []
    birth_dates: dict[str, str] = {}
    rrns: set[str] = set()
    for p in request.participations:
        rrns.add(p.parent.rrn)
        rrns.add(p.child.rrn)
    for rrn in rrns:
        info = validate_rrn(rrn)
        if not info.is_valid:
            errors.append(f"RRN fout: {info.error}")
        elif info.formatted:
            birth_dates[rrn] = info.formatted

    result = aggregate(request, birth_dates)

    # Verzendings-header
    today = datetime.now(UTC).strftime("%d-%m-%Y")
    verz = VerzendingHeaderPreview(
        v0002_inkomstenjaar=income_year,
        v0010_bestandtype="BCTEST" if test_mode else "BELCOTAX",
        v0011_aanmaakdatum=today,
        v0014_naam=org.name,
        v0015_adres=org.street or "",
        v0016_postcode=org.zip or "",
        v0017_gemeente=org.city or "",
        v0018_telefoonnummer=org.contact_phone or "",
        v0021_contactpersoon=org.contact_name or "",
        v0022_taalcode=org.language_code,
        v0023_emailadres=org.contact_email or "",
        v0024_nationaalnr=org.kbo,
        v0028_landwoonplaats=org.country_code,
    )

    # Aangifte-header (incl. optionele meertalige blokken)
    aang_kwargs = dict(
        a1002_inkomstenjaar=income_year,
        a1005_registratienummer=org.kbo,
        a1011_naamnl1=org.name,
        a1013_adresnl=org.street or "",
        a1014_postcodebelgisch=org.zip or "",
        a1015_gemeente=org.city or "",
        a1016_landwoonplaats=org.country_code,
        a1020_taalcode=org.language_code,
    )
    if org.name_fr and org.street_fr and org.city_fr:
        aang_kwargs.update(
            a1027_naamfr1=org.name_fr,
            a1029_adresfr=org.street_fr,
            a1030_gemeentefr=org.city_fr,
            a1031_taalfr=2,
        )
    if org.name_de and org.street_de and org.city_de:
        aang_kwargs.update(
            a1032_naamde1=org.name_de,
            a1034_adresde=org.street_de,
            a1035_gemeentede=org.city_de,
            a1036_taalde=3,
        )
    aangifte = AangifteHeaderPreview(**aang_kwargs)

    # Warnings per parent/child paar — voor weergave in fiche-detail
    warnings_by_pair: dict[tuple[str, str], list[str]] = {}
    for w in result.warnings:
        key = (w.get("parent_rrn", ""), w.get("child_rrn", ""))
        warnings_by_pair.setdefault(key, []).append(w["message"])

    fiches_preview = [
        _fiche_to_preview(
            f, seq=i + 1, export_ref=export_ref,
            warnings_for_pair=warnings_by_pair.get((f.parent_rrn, f.child_rrn), []),
        )
        for i, f in enumerate(result.fiches)
    ]

    # Trailer berekenen (zelfde logica als xml_generator)
    n = len(result.fiches)
    fiche_ctrls = [fp.f86_2059_totaalcontrole for fp in fiches_preview]
    sum_ctrl = sum(fiche_ctrls)
    sum_volgnr = sum(i + 1 for i in range(n))

    trailer = TrailerPreview(
        r8010_aantalrecords=n + 2,
        r8011_controletotaal=sum_volgnr,
        r8012_controletotaal=sum_ctrl,
        r9010_aantallogbestanden=n,
        r9011_totaalaantalrecords=n + 4,
        r9012_controletotaal=sum_volgnr,
        r9013_controletotaal=sum_ctrl,
    )

    summary = PreviewSummary(
        fiche_count=n,
        total_amount_cents=sum(f.total_amount_cents for f in result.fiches),
        total_xml_days=sum(f.total_days for f in result.fiches),
        skipped_count=result.skipped_count,
        warnings=result.warnings,
        errors=errors,
        organization_missing=_org_missing_for_preview(org),
    )

    return ExportPreviewResponse(
        income_year=income_year,
        test_mode=test_mode,
        verzending=verz,
        aangifte=aangifte,
        fiches=fiches_preview,
        trailer=trailer,
        summary=summary,
    )


def _empty_preview(
    income_year: int, org: Organization, test_mode: bool, error_msg: str,
) -> ExportPreviewResponse:
    today = datetime.now(UTC).strftime("%d-%m-%Y")
    return ExportPreviewResponse(
        income_year=income_year,
        test_mode=test_mode,
        verzending=VerzendingHeaderPreview(
            v0002_inkomstenjaar=income_year,
            v0010_bestandtype="BCTEST" if test_mode else "BELCOTAX",
            v0011_aanmaakdatum=today,
            v0014_naam=org.name,
            v0015_adres=org.street or "",
            v0016_postcode=org.zip or "",
            v0017_gemeente=org.city or "",
            v0018_telefoonnummer=org.contact_phone or "",
            v0021_contactpersoon=org.contact_name or "",
            v0022_taalcode=org.language_code,
            v0023_emailadres=org.contact_email or "",
            v0024_nationaalnr=org.kbo,
            v0028_landwoonplaats=org.country_code,
        ),
        aangifte=AangifteHeaderPreview(
            a1002_inkomstenjaar=income_year,
            a1005_registratienummer=org.kbo,
            a1011_naamnl1=org.name,
            a1013_adresnl=org.street or "",
            a1014_postcodebelgisch=org.zip or "",
            a1015_gemeente=org.city or "",
            a1016_landwoonplaats=org.country_code,
            a1020_taalcode=org.language_code,
        ),
        fiches=[],
        trailer=TrailerPreview(
            r8010_aantalrecords=2,
            r8011_controletotaal=0,
            r8012_controletotaal=0,
            r9010_aantallogbestanden=0,
            r9011_totaalaantalrecords=4,
            r9012_controletotaal=0,
            r9013_controletotaal=0,
        ),
        summary=PreviewSummary(
            fiche_count=0, total_amount_cents=0, total_xml_days=0,
            skipped_count=0, warnings=[], errors=[error_msg],
            organization_missing=_org_missing_for_preview(org),
        ),
    )
