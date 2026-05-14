"""Schemas voor de XML-preview (raadpleeg-fase vóór effectieve generatie).

Velden volgen exact de XML-elementnamen zodat de frontend ze 1:1 kan tonen.
Bedragen blijven centen (int), datums DD-MM-YYYY (str).
"""
from __future__ import annotations

from pydantic import BaseModel


class VerzendingHeaderPreview(BaseModel):
    v0002_inkomstenjaar: int
    v0010_bestandtype: str
    v0011_aanmaakdatum: str
    v0014_naam: str
    v0015_adres: str
    v0016_postcode: str
    v0017_gemeente: str
    v0018_telefoonnummer: str
    v0021_contactpersoon: str
    v0022_taalcode: int
    v0023_emailadres: str
    v0024_nationaalnr: str
    v0025_typeenvoi: int = 0
    v0028_landwoonplaats: int


class AangifteHeaderPreview(BaseModel):
    a1002_inkomstenjaar: int
    a1005_registratienummer: str
    a1011_naamnl1: str
    a1013_adresnl: str
    a1014_postcodebelgisch: str
    a1015_gemeente: str
    a1016_landwoonplaats: int
    a1020_taalcode: int
    # Optioneel — alleen aanwezig als organisatie meertalige naam heeft
    a1027_naamfr1: str | None = None
    a1029_adresfr: str | None = None
    a1030_gemeentefr: str | None = None
    a1031_taalfr: int | None = None
    a1032_naamde1: str | None = None
    a1034_adresde: str | None = None
    a1035_gemeentede: str | None = None
    a1036_taalde: int | None = None


class PeriodPreview(BaseModel):
    begindate: str           # DD-MM-YYYY
    enddate: str
    amount_cents: int
    half_days: int           # raw teller (1 halve = 1, 1 volle = 2)
    xml_days: int            # ceil(half_days/2) — wat in f86_2110/2113 komt
    daily_tariff_cents: int  # amount_cents / xml_days


class FichePreview(BaseModel):
    # Identificatie
    seq: int
    f2008_typefiche: str = "28186"
    f2009_volgnummer: int
    f2010_referentie: str
    # Ouder
    f2011_nationaalnr: str       # parent_rrn
    f2013_naam: str              # parent_last_name
    f2114_voornamen: str         # parent_first_name
    f2015_adres: str
    f2016_postcodebelgisch: str
    f2017_gemeente: str
    f2018_landwoonplaats: int
    # Kind
    f86_2106_childname: str
    f86_2107_childfirstname: str
    f86_2153_nnchild: str
    f86_2163_childbirthdate: str
    f86_2101_childcountry: int
    f86_2102_childaddress: str
    f86_2139_childpostnr: str
    f86_2140_childmunicipality: str
    # Periodes (XML-mapping)
    period1: PeriodPreview
    period2: PeriodPreview | None = None
    # Totalen
    f86_2059_totaalcontrole: int
    f86_2064_totalamount: int
    # Per-fiche validatie-status
    missing_fields: list[str] = []   # bv. "parent_rrn", "child_address_zip"
    warnings: list[str] = []         # human-readable warnings per fiche


class TrailerPreview(BaseModel):
    r8010_aantalrecords: int
    r8011_controletotaal: int
    r8012_controletotaal: int
    r9010_aantallogbestanden: int
    r9011_totaalaantalrecords: int
    r9012_controletotaal: int
    r9013_controletotaal: int


class InvalidRegistration(BaseModel):
    """Eén inschrijving die niet in de XML komt, met de redenen waarom."""
    registration_odoo_id: int
    event_name: str
    event_date_begin: str | None = None   # DD-MM-YYYY
    event_date_end: str | None = None
    partner_name: str
    parent_rrn: str | None = None         # raw waarde — kan ongeldig zijn
    child_first_name: str | None = None
    child_last_name: str | None = None
    child_rrn: str | None = None
    reasons: list[str]                    # NL strings, zie reden-taxonomie


class PreviewSummary(BaseModel):
    fiche_count: int
    total_amount_cents: int
    total_xml_days: int
    skipped_count: int
    warnings: list[dict] = []
    errors: list[str] = []
    organization_missing: list[str] = []   # bv. ["name_fr", "cert_validity_start"]
    invalid_registrations: list[InvalidRegistration] = []


class ExportPreviewResponse(BaseModel):
    income_year: int
    test_mode: bool = False
    verzending: VerzendingHeaderPreview
    aangifte: AangifteHeaderPreview
    fiches: list[FichePreview]
    trailer: TrailerPreview
    summary: PreviewSummary
