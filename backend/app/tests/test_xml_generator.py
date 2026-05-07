from datetime import date

from lxml import etree

from app.schemas.export import AddressSchema, ContactSchema, OrganizationPayload
from app.services.aggregation import AddressData, Fiche28186Data
from app.services.xml_generator import generate_bow_xml

CHILD_ADDR = AddressData(street="Kindstraat 1", zip="3000", city="Leuven", country_code=150)
PARENT_ADDR = AddressData(street="Ouderlaan 5", zip="3000", city="Leuven", country_code=150)


def _org():
    return OrganizationPayload(
        kbo="0886886638",
        name="Sportkamp Leuven VZW",
        address=AddressSchema(street="Kampstraat 12", zip="3000", city="Leuven", country_code=150),
        language_code=1,
        contact=ContactSchema(name="Administratie", email="admin@sportkamp.be", phone="+32 16 12 34 56"),
    )


def _fiche(seq_offset: int = 0) -> Fiche28186Data:
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
        total_amount_cents=32500 + seq_offset,
        total_days=10,
        period_start=date(2025, 4, 7),
        period_end=date(2025, 7, 5),
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


def test_totaalcontrole_is_2x_totalamount():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    total = int(root.findtext(".//f86_2064_totalamount"))
    ctrl = int(root.findtext(".//f86_2059_totaalcontrole"))
    assert ctrl == 2 * total


def test_date_format_dd_mm_yyyy():
    root = _parse(generate_bow_xml(2025, _org(), [_fiche()]))
    assert root.findtext(".//f86_2055_begindate1") == "07-04-2025"
    assert root.findtext(".//f86_2056_enddate1") == "05-07-2025"


def test_r8_controletotaal_is_sum_of_fiche_ctrls():
    f1, f2 = _fiche(), _fiche(10000)
    root = _parse(generate_bow_xml(2025, _org(), [f1, f2]))
    expected = 2 * f1.total_amount_cents + 2 * f2.total_amount_cents
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
