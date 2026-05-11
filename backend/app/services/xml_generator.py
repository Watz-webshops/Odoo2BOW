"""
BOW 281.86 XML generator — gebaseerd op officieel BOW2022_VoorbeeldXML_f86.xml.

Structuur:
  Verzendingen
    Verzending
      v0002..v0028 (verzender/organisatie header)
      Aangiften
        Aangifte
          a1002..a1036 (aangever header, optioneel meertalig)
          Opgaven
            Opgave32586
              Fiche28186 × N
          r8xxx (aangifte trailer)
      r9xxx (verzending trailer)

Bedragen: centen (integer).
Datums:   DD-MM-YYYY.
"""

from datetime import date, datetime, UTC
from lxml import etree

from app.schemas.export import OrganizationPayload
from app.services.aggregation import Fiche28186Data, PeriodData


def _fmt(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def _sub(parent: etree._Element, tag: str, text: str | int | None = None) -> etree._Element:
    el = etree.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def _fiche_totaalcontrole(fiche: Fiche28186Data) -> int:
    """f86_2059 = som van amount1 + (amount2 of 0) + totalamount."""
    total = fiche.total_amount_cents
    amount1 = fiche.period1.amount_cents
    amount2 = fiche.period2.amount_cents if fiche.period2 else 0
    return amount1 + amount2 + total


def _write_period(f: etree._Element, period: PeriodData, *, is_second: bool) -> None:
    if not is_second:
        _sub(f, "f86_2055_begindate1", _fmt(period.start))
        _sub(f, "f86_2056_enddate1", _fmt(period.end))
    else:
        _sub(f, "f86_2093_begindate2", _fmt(period.start))
        _sub(f, "f86_2144_enddate2", _fmt(period.end))


def generate_bow_xml(
    income_year: int,
    organization: OrganizationPayload,
    fiches: list[Fiche28186Data],
    export_ref: str = "",
    test_mode: bool = False,
) -> bytes:
    """
    Pure functie — geeft UTF-8 XML bytes terug.
    export_ref wordt als prefix gebruikt in f2010_referentie.
    """
    today = datetime.now(UTC).strftime("%d-%m-%Y")
    n_fiches = len(fiches)

    # Controletotaal per fiche (= som van alle amount-velden in fiche)
    fiche_ctrls = [_fiche_totaalcontrole(f) for f in fiches]
    sum_ctrl = sum(fiche_ctrls)
    sum_volgnr = sum(i + 1 for i in range(n_fiches))  # 1+2+...+n

    # r8010: 1 aangifte-header + n fiches + 1 trailer = n+2
    r8010 = n_fiches + 2
    # r9011: 1 verzending-header + (1 aangifte + n fiches + 1 r8) + 1 r9 = n+4
    r9011 = n_fiches + 4

    root = etree.Element("Verzendingen")
    verzending = etree.SubElement(root, "Verzending")

    # ── Verzending header ─────────────────────────────────────────────────────
    _sub(verzending, "v0002_inkomstenjaar", income_year)
    _sub(verzending, "v0010_bestandtype", "BCTEST" if test_mode else "BELCOTAX")
    _sub(verzending, "v0011_aanmaakdatum", today)
    _sub(verzending, "v0014_naam", organization.name)
    _sub(verzending, "v0015_adres", organization.address.street)
    _sub(verzending, "v0016_postcode", organization.address.zip)
    _sub(verzending, "v0017_gemeente", organization.address.city)
    _sub(verzending, "v0018_telefoonnummer", organization.contact.phone)
    _sub(verzending, "v0021_contactpersoon", organization.contact.name)
    _sub(verzending, "v0022_taalcode", organization.language_code)
    _sub(verzending, "v0023_emailadres", organization.contact.email)
    _sub(verzending, "v0024_nationaalnr", organization.kbo)
    _sub(verzending, "v0025_typeenvoi", 0)
    _sub(verzending, "v0028_landwoonplaats", organization.address.country_code)

    # ── Aangiften ─────────────────────────────────────────────────────────────
    aangiften = etree.SubElement(verzending, "Aangiften")
    aangifte = etree.SubElement(aangiften, "Aangifte")

    _sub(aangifte, "a1002_inkomstenjaar", income_year)
    _sub(aangifte, "a1005_registratienummer", organization.kbo)
    _sub(aangifte, "a1011_naamnl1", organization.name)
    _sub(aangifte, "a1013_adresnl", organization.address.street)
    _sub(aangifte, "a1014_postcodebelgisch", organization.address.zip)
    _sub(aangifte, "a1015_gemeente", organization.address.city)
    _sub(aangifte, "a1016_landwoonplaats", organization.address.country_code)
    _sub(aangifte, "a1020_taalcode", organization.language_code)

    # Optionele anderstalige aangever-blokken
    if organization.name_fr:
        _sub(aangifte, "a1027_naamfr1", organization.name_fr.name)
        _sub(aangifte, "a1029_adresfr", organization.name_fr.street)
        _sub(aangifte, "a1030_gemeentefr", organization.name_fr.city)
        _sub(aangifte, "a1031_taalfr", 2)
    if organization.name_de:
        _sub(aangifte, "a1032_naamde1", organization.name_de.name)
        _sub(aangifte, "a1034_adresde", organization.name_de.street)
        _sub(aangifte, "a1035_gemeentede", organization.name_de.city)
        _sub(aangifte, "a1036_taalde", 3)

    # ── Opgaven → Opgave32586 → Fiches ───────────────────────────────────────
    opgaven = etree.SubElement(aangifte, "Opgaven")
    opgave = etree.SubElement(opgaven, "Opgave32586")

    for seq, (fiche, ctrl) in enumerate(zip(fiches, fiche_ctrls), start=1):
        ref = f"{export_ref}-{seq}" if export_ref else str(seq)

        f = etree.SubElement(opgave, "Fiche28186")

        # ── Standaard fiche-header ────────────────────────────────────────────
        _sub(f, "f2002_inkomstenjaar", income_year)
        _sub(f, "f2005_registratienummer", organization.kbo)
        _sub(f, "f2007_division")               # altijd leeg
        _sub(f, "f2008_typefiche", "28186")
        _sub(f, "f2009_volgnummer", seq)
        _sub(f, "f2010_referentie", ref)

        # Ouder (belastingplichtige)
        _sub(f, "f2011_nationaalnr", fiche.parent_rrn)
        _sub(f, "f2013_naam", fiche.parent_last_name)
        _sub(f, "f2015_adres", fiche.parent_address.street)
        _sub(f, "f2016_postcodebelgisch", fiche.parent_address.zip)
        _sub(f, "f2017_gemeente", fiche.parent_address.city)
        _sub(f, "f2018_landwoonplaats", fiche.parent_address.country_code)
        _sub(f, "f2028_typetraitement", 0)
        _sub(f, "f2029_enkelopgave325", 0)
        _sub(f, "f2114_voornamen", fiche.parent_first_name)

        # ── f86-velden (kinderopvang) ─────────────────────────────────────────
        _sub(f, "f86_2031_certificationautorisation", 1)

        # Periode 1 (verplicht)
        _write_period(f, fiche.period1, is_second=False)
        _sub(f, "f86_2059_totaalcontrole", ctrl)
        _sub(f, "f86_2060_amount1", fiche.period1.amount_cents)
        if fiche.period2:
            _sub(f, "f86_2061_amount2", fiche.period2.amount_cents)
        _sub(f, "f86_2064_totalamount", fiche.total_amount_cents)
        if fiche.period2:
            _write_period(f, fiche.period2, is_second=True)

        # Certifier (= de organisatie zelf)
        _sub(f, "f86_2100_certifierpostnr", organization.address.zip)
        _sub(f, "f86_2101_childcountry", fiche.child_address.country_code)
        _sub(f, "f86_2102_childaddress", fiche.child_address.street)
        _sub(f, "f86_2106_childname", fiche.child_last_name)
        _sub(f, "f86_2107_childfirstname", fiche.child_first_name)
        _sub(f, "f86_2109_certifiercbenumber", organization.kbo)
        _sub(f, "f86_2110_numberofday1", fiche.period1.xml_days)
        _sub(f, "f86_2111_dailytariff1", fiche.period1.daily_tariff_cents)
        if fiche.period2:
            _sub(f, "f86_2113_numberofday2", fiche.period2.xml_days)
            _sub(f, "f86_2115_dailytariff2", fiche.period2.daily_tariff_cents)
        _sub(f, "f86_2139_childpostnr", fiche.child_address.zip)
        _sub(f, "f86_2140_childmunicipality", fiche.child_address.city)
        _sub(f, "f86_2153_nnchild", fiche.child_rrn)
        _sub(f, "f86_2154_certifiermunicipality", organization.address.city)
        _sub(f, "f86_2155_certifiername", organization.name)
        _sub(f, "f86_2156_certifieradres", organization.address.street)
        _sub(f, "f86_2163_childbirthdate", fiche.child_birth_date_formatted)

        # Certificeringsgeldigheid (optioneel, per organisatie ingesteld)
        if organization.cert_validity_start:
            _sub(f, "f86_2164_beginvaliditycertification", _fmt(organization.cert_validity_start))
        if organization.cert_validity_end:
            _sub(f, "f86_2171_endvaliditycertification", _fmt(organization.cert_validity_end))

    # ── Aangifte trailer (r8) ─────────────────────────────────────────────────
    _sub(aangifte, "r8002_inkomstenjaar", income_year)
    _sub(aangifte, "r8005_registratienummer", organization.kbo)
    _sub(aangifte, "r8007_division")
    _sub(aangifte, "r8010_aantalrecords", r8010)
    _sub(aangifte, "r8011_controletotaal", sum_volgnr)
    _sub(aangifte, "r8012_controletotaal", sum_ctrl)
    _sub(aangifte, "r8013_totaalvoorheffingen", 0)

    # ── Verzending trailer (r9) ───────────────────────────────────────────────
    _sub(verzending, "r9002_inkomstenjaar", income_year)
    _sub(verzending, "r9010_aantallogbestanden", n_fiches)
    _sub(verzending, "r9011_totaalaantalrecords", r9011)
    _sub(verzending, "r9012_controletotaal", sum_volgnr)
    _sub(verzending, "r9013_controletotaal", sum_ctrl)
    _sub(verzending, "r9014_controletotaal", 0)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")
