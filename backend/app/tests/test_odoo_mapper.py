from app.services.odoo_mapper import (
    classify_property,
    classify_question,
    parse_answers,
    parse_properties,
)


# ── classify_property ─────────────────────────────────────────────────────────
def test_classify_property_voornaam_kind():
    assert classify_property("Voornaam kind") == "child_first_name"


def test_classify_property_achternaam_kind():
    assert classify_property("Achternaam kind") == "child_last_name"


def test_classify_property_voornaam_kind_wins_over_naam_kind():
    # "Voornaam kind" bevat "naam kind" (last_name pattern), maar moet first_name worden
    assert classify_property("Voornaam kind") == "child_first_name"


def test_classify_property_case_insensitive():
    assert classify_property("VOORNAAM KIND") == "child_first_name"


def test_classify_property_unknown_label():
    assert classify_property("Iets anders") is None


def test_classify_property_empty():
    assert classify_property("") is None


# ── parse_properties ──────────────────────────────────────────────────────────
def test_parse_properties_extracts_names():
    props = [
        {"name": "k1", "string": "Voornaam kind", "type": "char", "value": "Emma"},
        {"name": "k2", "string": "Achternaam kind", "type": "char", "value": "Peeters"},
    ]
    assert parse_properties(props) == {
        "child_first_name": "Emma",
        "child_last_name": "Peeters",
    }


def test_parse_properties_ignores_unknown_labels():
    props = [
        {"name": "k1", "string": "Iets onbekends", "type": "char", "value": "x"},
        {"name": "k2", "string": "Voornaam kind", "type": "char", "value": "Sam"},
    ]
    assert parse_properties(props) == {
        "child_first_name": "Sam",
        "child_last_name": None,
    }


def test_parse_properties_handles_false_or_missing_value():
    # Odoo levert False voor lege properties
    props = [
        {"name": "k1", "string": "Voornaam kind", "type": "char", "value": False},
        {"name": "k2", "string": "Achternaam kind", "type": "char", "value": ""},
    ]
    assert parse_properties(props) == {
        "child_first_name": None,
        "child_last_name": None,
    }


def test_parse_properties_empty_input():
    assert parse_properties(None) == {"child_first_name": None, "child_last_name": None}
    assert parse_properties(False) == {"child_first_name": None, "child_last_name": None}
    assert parse_properties([]) == {"child_first_name": None, "child_last_name": None}


def test_parse_properties_truncates_long_values():
    props = [{"name": "k1", "string": "Voornaam kind", "type": "char", "value": "A" * 200}]
    assert parse_properties(props)["child_first_name"] == "A" * 100


def test_parse_properties_strips_whitespace():
    props = [{"name": "k1", "string": "Voornaam kind", "type": "char", "value": "  Emma  "}]
    assert parse_properties(props)["child_first_name"] == "Emma"


# ── classify_question (regressie: alleen nog RRN's) ───────────────────────────
def test_classify_question_only_rrn_keys():
    assert classify_question("RRN kind") == "child_rrn"
    assert classify_question("RRN ouder") == "parent_rrn"
    # Naam-vragen worden NIET meer geclassificeerd via survey
    assert classify_question("Voornaam kind") is None
    assert classify_question("Achternaam kind") is None


# ── parse_answers (regressie: returnt alleen rrn keys) ────────────────────────
def test_parse_answers_returns_only_rrn_keys():
    answers = [
        {"question_id": (1, "RRN kind"), "value_text_box": "15.01.21-543.21"},
        {"question_id": (2, "RRN ouder"), "value_text_box": "85.01.01-123.45"},
    ]
    question_titles = {1: "RRN kind", 2: "RRN ouder"}
    result = parse_answers(answers, question_titles, {})
    assert set(result.keys()) == {"child_rrn", "parent_rrn"}
    assert result["child_rrn"] == "15012154321"
    assert result["parent_rrn"] == "85010112345"
