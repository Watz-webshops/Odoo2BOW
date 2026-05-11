from datetime import date

from lxml import etree

from app.schemas.export import (
    AddressSchema,
    ContactSchema,
    MultilingualNameSchema,
    OrganizationPayload,
)
from app.services.aggregation import AddressData, Fiche28186Data, PeriodData
from app.services.xml_generator import generate_bow_xml

CHILD_ADDR = AddressData(street="Kindstraat 1", zip="3000", city="Leuven", country_code=150)
PARENT_ADDR = AddressData(street="Ouderlaan 5", zip="3000", city="Leuven", country_code=150)


def _org(**overrides) -> OrganizationPayload:
    base = dict(
        kbo="0886886638",
        name="Sportkamp Leuven VZW",
        address=AddressSchema(street="Kampstraat 12", zip="3000", city="Leuven", country_code=150),
        language_code=1,
        contact=ContactSchema(name="Administratie", email="admin@sportkamp.be", phone="+32 16 12 34 56"),
    )
    base.update(overrides)
    return OrganizationPayload(**base)


def _period(amount_cents: int = 32500, half_days: int = 20, start=date(2025, 4, 7), end=date(2025, 7, 5)) -> PeriodData:
    # half_days=20 => 10 volle dagen
    return PeriodData(start=start, end=end, amount_cents=amount_cents, half_days=half_days)


def _fiche(seq_offset: int = 0, *, period2: PeriodData | None = None) -> Fiche28186Data:
    return Fiche28186Data(
        parent_rrn="85010112345",
        parent_last_name="Peeters",
        parent_first_name="Jan",
        parent_address=PARENT_ADDR,
        child_rrn="15012154321",
        child_last_name="Peeters",
        child_first_name="Emma",
        child_birth_date_formatted="21-01-2015",
        child_address=CHILD_ADDR,
        period1=_period(amount_cents=32500 + seq_offset),
        period2=period2,
    )


def _parse(xml_bytes: bytes) -> etree._Element:
    return etree.fromstring(xml_bytes)


def test_root_element_is_verzendingen():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.tag == "Verzendingen"


def test_bestandtype_is_belcotax():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//v0010_bestandtype") == "BELCOTAX"


def test_income_year_in_verzending():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//v0002_inkomstenjaar") == "2025"


def test_parent_rrn_in_f2011():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f2011_nationaalnr") == "85010112345"


def test_parent_name_fields():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f2013_naam") == "Peeters"
    assert root.findtext(".//f2114_voornamen") == "Jan"


def test_child_rrn_in_f86_2153():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2153_nnchild") == "15012154321"


def test_child_birthdate_in_f86_2163():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2163_childbirthdate") == "21-01-2015"


def test_amount_in_cents_f86_2060():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2060_amount1") == "32500"


def test_totalamount_equals_amount1_single_period():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2064_totalamount") == root.findtext(".//f86_2060_amount1")


def test_totaalcontrole_is_2x_totalamount_single_period():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    total = int(root.findtext(".//f86_2064_totalamount"))
    ctrl = int(root.findtext(".//f86_2059_totaalcontrole"))
    # Bij 1 periode: amount1 + 0 + totalamount = 2 × totalamount
    assert ctrl == 2 * total


def test_date_format_dd_mm_yyyy():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2055_begindate1") == "07-04-2025"
    assert root.findtext(".//f86_2056_enddate1") == "05-07-2025"


def test_r8_controletotaal_is_sum_of_fiche_ctrls():
    f1, f2 = _fiche(), _fiche(10000)
    root = _parse(generate_bow_xml(2025, _org(), [f1, f2]))
    # Per fiche: amount1 + amount2(=0) + totalamount = 2 × amount1 (single period)
    expected = 2 * f1.period1.amount_cents + 2 * f2.period1.amount_cents
    assert int(root.findtext(".//r8012_controletotaal")) == expected


def test_r8_aantalrecords_is_n_plus_2():
    # 1 aangifte-header + 3 fiches + 1 trailer = 5
    root = _parse(generate_bow_xml(2025, _org(), [_fiche(), _fiche(1), _fiche(2)]))
    assert root.findtext(".//r8010_aantalrecords") == "5"


def test_sequence_numbers_increment():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche(), _fiche(1), _fiche(2)]))
    volgnrs = [el.text for el in root.findall(".//f2009_volgnummer")]
    assert volgnrs == ["1", "2", "3"]


def test_opgaven_wrapper_present():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.find(".//Opgaven") is not None
    assert root.find(".//Opgaven/Opgave32586") is not None


def test_certifier_kbo_in_f86_2109():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2109_certifiercbenumber") == "0886886638"


def test_typefiche_is_28186():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f2008_typefiche") == "28186"


# ── Periode 2 ────────────────────────────────────────────────────────────────
def test_period2_written_when_present():
    p2 = _period(amount_cents=50000, half_days=20, start=date(2025, 9, 1), end=date(2025, 12, 20))
    root = _parse(generate_bow_xml(2025, _org(), [_fiche(period2=p2)]))
    assert root.findtext(".//f86_2093_begindate2") == "01-09-2025"
    assert root.findtext(".//f86_2144_enddate2") == "20-12-2025"
    assert root.findtext(".//f86_2061_amount2") == "50000"
    assert root.findtext(".//f86_2113_numberofday2") == "10"
    assert root.findtext(".//f86_2115_dailytariff2") == "5000"


def test_period2_absent_when_not_set():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.find(".//f86_2093_begindate2") is None
    assert root.find(".//f86_2061_amount2") is None
    assert root.find(".//f86_2113_numberofday2") is None


def test_totaalcontrole_with_period2():
    p2 = _period(amount_cents=50000, half_days=20)
    root = _parse(generate_bow_xml(2025, _org(), [_fiche(period2=p2)]))
    # amount1 + amount2 + totalamount = 32500 + 50000 + 82500 = 165000
    assert int(root.findtext(".//f86_2059_totaalcontrole")) == 165000
    assert int(root.findtext(".//f86_2064_totalamount")) == 82500


# ── Meertalige aangever-blokken ──────────────────────────────────────────────
def test_french_block_written_when_present():
    org = _org(name_fr=MultilingualNameSchema(name="SPF Test", street="Rue 1", city="Bruxelles"))
    root = _parse(generate_bow_xml(2025, org, [_fiche()]))
    assert root.findtext(".//a1027_naamfr1") == "SPF Test"
    assert root.findtext(".//a1029_adresfr") == "Rue 1"
    assert root.findtext(".//a1030_gemeentefr") == "Bruxelles"
    assert root.findtext(".//a1031_taalfr") == "2"


def test_german_block_written_when_present():
    org = _org(name_de=MultilingualNameSchema(name="FOD Test", street="Strasse 1", city="Brüssel"))
    root = _parse(generate_bow_xml(2025, org, [_fiche()]))
    assert root.findtext(".//a1032_naamde1") == "FOD Test"
    assert root.findtext(".//a1036_taalde") == "3"


def test_no_multilingual_blocks_by_default():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.find(".//a1027_naamfr1") is None
    assert root.find(".//a1032_naamde1") is None


# ── Certificeringsgeldigheid ─────────────────────────────────────────────────
def test_cert_validity_written_when_present():
    org = _org(cert_validity_start=date(2021, 8, 1), cert_validity_end=date(2021, 8, 31))
    root = _parse(generate_bow_xml(2025, org, [_fiche()]))
    assert root.findtext(".//f86_2164_beginvaliditycertification") == "01-08-2021"
    assert root.findtext(".//f86_2171_endvaliditycertification") == "31-08-2021"


def test_cert_validity_absent_when_not_set():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.find(".//f86_2164_beginvaliditycertification") is None
    assert root.find(".//f86_2171_endvaliditycertification") is None
