"""Verifieer dat de generator alle XML-elementen uit het officiële voorbeeld
BOW2022_VoorbeeldXML_f86.xml kan reproduceren wanneer hij overeenkomstige input krijgt.

We bouwen 3 fiches die qua structuur het voorbeeld weerspiegelen:
- fiche 1: 2 perioden + alle f86-velden ingevuld
- fiche 2: 1 periode (geen f86_2061/2113/2115/2093/2144)
- fiche 3: 1 periode + certificeringsgeldigheid (f86_2164/2171)

De assertions checken dat ELK element uit het voorbeeld ook in onze output
voorkomt. Tekst-waarden vergelijken we niet 1:1 (datums, namen, kbo verschillen),
maar de aanwezigheid van elke veldnaam moet kloppen.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from lxml import etree

from app.schemas.export import (
    AddressSchema,
    ContactSchema,
    MultilingualNameSchema,
    OrganizationPayload,
)
from app.services.aggregation import AddressData, Fiche28186Data, PeriodData
from app.services.xml_generator import generate_bow_xml


VOORBEELD = Path(__file__).resolve().parents[1] / "schemas" / "BOW2022_VoorbeeldXML_f86.xml"


def _all_tags(root: etree._Element) -> set[str]:
    return {el.tag for el in root.iter() if isinstance(el.tag, str)}


def _voorbeeld_root() -> etree._Element:
    return etree.fromstring(VOORBEELD.read_bytes())


def _addr(street="Teststraat, 1", zip="1000", city="Brussel") -> AddressData:
    return AddressData(street=street, zip=zip, city=city, country_code=150)


def _period(start: date, end: date, amount: int, half_days: int) -> PeriodData:
    return PeriodData(start=start, end=end, amount_cents=amount, half_days=half_days)


def _make_voorbeeld_equivalent_payload() -> tuple[OrganizationPayload, list[Fiche28186Data]]:
    """Bouw een payload met dezelfde *structuur* als het voorbeeld."""
    org = OrganizationPayload(
        kbo="0308357159",
        name="FOD FIN TEST",
        address=AddressSchema(street="Teststraat, 10", zip="1000", city="Brussel", country_code=150),
        language_code=1,
        contact=ContactSchema(name="Belcotax", email="belcotax@minfin.fed.be", phone="02 572 57 57"),
        name_fr=MultilingualNameSchema(name="SPF FIN TEST", street="Rue de test, 10", city="Bruxelles"),
        name_de=MultilingualNameSchema(name="FOD FIN TEST", street="Teststrasse, 1", city="Brussel"),
    )

    # Fiche 1: 2 perioden — overeenkomstig met eerste fiche in het voorbeeld
    fiche1 = Fiche28186Data(
        parent_rrn="99090999997",
        parent_last_name="Naam",
        parent_first_name="Voornaam",
        parent_address=_addr("Teststraat, 1", "1000", "Brussel"),
        child_rrn="00000000128",
        child_last_name="Naam Kind",
        child_first_name="Voornaam Kind",
        child_birth_date_formatted="01-01-2015",
        child_address=_addr("Teststraat, 1", "1000", "Brussel"),
        period1=_period(date(2021, 1, 1), date(2021, 6, 30), 60000, 120),
        period2=_period(date(2021, 9, 1), date(2021, 12, 31), 50000, 100),
    )

    # Fiche 2: 1 periode
    fiche2 = Fiche28186Data(
        parent_rrn="99090999997",
        parent_last_name="Nom",
        parent_first_name="Prenom",
        parent_address=_addr("Rue de test, 1", "1000", "Bruxelles"),
        child_rrn="00000000128",
        child_last_name="Nom Enfant",
        child_first_name="Prenom Enfant",
        child_birth_date_formatted="01-01-2015",
        child_address=_addr("Rue de test, 1", "1000", "Bruxelles"),
        period1=_period(date(2021, 7, 1), date(2021, 7, 11), 10000, 20),
    )

    # Fiche 3: 1 periode (cert validity wordt via org gezet, niet per fiche)
    fiche3 = Fiche28186Data(
        parent_rrn="99090999997",
        parent_last_name="Name",
        parent_first_name="Vorname",
        parent_address=_addr("Teststrasse, 1", "1000", "Brüssel"),
        child_rrn="00000000128",
        child_last_name="Name Kind",
        child_first_name="Vorname Kind",
        child_birth_date_formatted="01-01-2015",
        child_address=_addr("Teststrasse, 1", "1000", "Brüssel"),
        period1=_period(date(2021, 8, 10), date(2021, 8, 15), 5000, 10),
    )

    return org, [fiche1, fiche2, fiche3]


def test_voorbeeld_xml_loads():
    root = _voorbeeld_root()
    assert root.tag == "Verzendingen"


def test_all_voorbeeld_tags_are_emitted_when_inputs_match():
    """Alle XML-element-namen uit het voorbeeld moeten ook in onze gegenereerde XML voorkomen."""
    org, fiches = _make_voorbeeld_equivalent_payload()
    # Cert-validity uit voorbeeld fiche 3 zit op org-niveau (zelfde voor alle fiches in onze flow).
    org = org.model_copy(update={
        "cert_validity_start": date(2021, 8, 1),
        "cert_validity_end": date(2021, 8, 31),
    })

    expected = _all_tags(_voorbeeld_root())
    actual = _all_tags(etree.fromstring(generate_bow_xml(2022, org, fiches)))

    # Velden die strikt aan een specifieke fiche-vorm gekoppeld zijn en die we
    # via de equivalent-input ook genereren.
    missing = expected - actual
    assert not missing, f"Ontbrekende tags in onze output: {sorted(missing)}"


def test_field_count_matches_voorbeeld_within_tolerance():
    """Aantal Fiche28186 elementen moet overeenkomen."""
    voorbeeld_count = len(_voorbeeld_root().findall(".//Fiche28186"))

    org, fiches = _make_voorbeeld_equivalent_payload()
    out = etree.fromstring(generate_bow_xml(2022, org, fiches))
    our_count = len(out.findall(".//Fiche28186"))
    assert our_count == voorbeeld_count == 3


def test_voorbeeld_specific_fields_present():
    """Spot-check: dit zijn de minder-vanzelfsprekende velden uit het voorbeeld."""
    org, fiches = _make_voorbeeld_equivalent_payload()
    org = org.model_copy(update={
        "cert_validity_start": date(2021, 8, 1),
        "cert_validity_end": date(2021, 8, 31),
    })
    out = etree.fromstring(generate_bow_xml(2022, org, fiches))
    tags = _all_tags(out)

    for required in [
        "a1027_naamfr1", "a1029_adresfr", "a1030_gemeentefr", "a1031_taalfr",
        "a1032_naamde1", "a1034_adresde", "a1035_gemeentede", "a1036_taalde",
        "f86_2093_begindate2", "f86_2144_enddate2",
        "f86_2061_amount2", "f86_2113_numberofday2", "f86_2115_dailytariff2",
        "f86_2164_beginvaliditycertification", "f86_2171_endvaliditycertification",
    ]:
        assert required in tags, f"Missing tag in output: {required}"
