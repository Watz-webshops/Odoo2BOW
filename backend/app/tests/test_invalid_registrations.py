from datetime import datetime

from app.services.export_from_local import invalid_reasons_for_row

VALID_PARENT_RRN = "85010112345"
VALID_CHILD_RRN = "15012154321"
VALID_BEGIN = datetime(2026, 7, 1)
VALID_END = datetime(2026, 7, 5)


def test_valid_row_has_no_reasons():
    assert invalid_reasons_for_row(
        VALID_PARENT_RRN, VALID_CHILD_RRN, VALID_BEGIN, VALID_END,
    ) == []


def test_missing_parent_rrn():
    reasons = invalid_reasons_for_row(None, VALID_CHILD_RRN, VALID_BEGIN, VALID_END)
    assert reasons == ["RRN ouder ontbreekt"]


def test_empty_parent_rrn_treated_as_missing():
    reasons = invalid_reasons_for_row("", VALID_CHILD_RRN, VALID_BEGIN, VALID_END)
    assert reasons == ["RRN ouder ontbreekt"]


def test_invalid_child_rrn_wrong_length():
    reasons = invalid_reasons_for_row(VALID_PARENT_RRN, "123", VALID_BEGIN, VALID_END)
    assert reasons == ["RRN kind ongeldig"]


def test_invalid_child_rrn_wrong_checksum():
    reasons = invalid_reasons_for_row(
        VALID_PARENT_RRN, "15012154399", VALID_BEGIN, VALID_END,
    )
    assert reasons == ["RRN kind ongeldig"]


def test_missing_event_begin_date():
    reasons = invalid_reasons_for_row(
        VALID_PARENT_RRN, VALID_CHILD_RRN, None, VALID_END,
    )
    assert reasons == ["Begin- of einddatum event ontbreekt"]


def test_missing_event_end_date():
    reasons = invalid_reasons_for_row(
        VALID_PARENT_RRN, VALID_CHILD_RRN, VALID_BEGIN, None,
    )
    assert reasons == ["Begin- of einddatum event ontbreekt"]


def test_all_reasons_combined():
    reasons = invalid_reasons_for_row(None, None, None, None)
    assert reasons == [
        "RRN ouder ontbreekt",
        "RRN kind ontbreekt",
        "Begin- of einddatum event ontbreekt",
    ]


def test_invalid_parent_rrn_and_missing_child_rrn():
    reasons = invalid_reasons_for_row("00000000000", None, VALID_BEGIN, VALID_END)
    assert reasons == ["RRN ouder ongeldig", "RRN kind ontbreekt"]
