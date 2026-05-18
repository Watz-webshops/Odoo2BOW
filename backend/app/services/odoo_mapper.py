"""
Mapping helpers: Odoo records → lokale rijen.

Survey-antwoorden leveren alleen nog de RRN's:
  - 'rrn kind' / 'rijksregisternummer kind'        → child.rrn
  - 'rrn ouder' / 'rijksregisternummer ouder'      → parent.rrn

Voor- en achternaam van het kind komen uit de Odoo Properties op de
event.registration ('registration_properties'). Gematcht op het property-label
(case-insensitive, partial match):
  - 'voornaam kind' / 'kind voornaam'              → child.first_name
  - 'achternaam kind' / 'kind achternaam'          → child.last_name
"""
from __future__ import annotations

# Survey-vragen — alleen nog RRN's
QUESTION_PATTERNS = {
    "child_rrn": ["rrn kind", "rijksregisternummer kind", "rijksregister kind"],
    "parent_rrn": ["rrn ouder", "rijksregisternummer ouder", "rijksregister ouder"],
}

REQUIRED_QUESTION_KEYS = ["child_rrn", "parent_rrn"]

# Property-labels op event.registration — kindvoornaam/achternaam
PROPERTY_PATTERNS = {
    "child_first_name": ["voornaam kind", "kind voornaam", "first name child"],
    "child_last_name": ["achternaam kind", "kind achternaam", "last name child", "naam kind"],
}


def classify_question(title: str) -> str | None:
    """
    Geeft de canonieke key terug (child_rrn / parent_rrn) of None
    als de title niet matcht.
    """
    if not title:
        return None
    t = title.lower().strip()
    for key, patterns in QUESTION_PATTERNS.items():
        for pat in patterns:
            if pat in t:
                return key
    return None


def classify_property(label: str) -> str | None:
    """Geeft de canonieke key terug (child_first_name / child_last_name) of None."""
    if not label:
        return None
    t = label.lower().strip()
    # child_first_name eerst zodat "voornaam kind" niet als child_last_name matcht op "naam kind"
    ordered = [
        ("child_first_name", PROPERTY_PATTERNS["child_first_name"]),
        ("child_last_name", PROPERTY_PATTERNS["child_last_name"]),
    ]
    for key, patterns in ordered:
        for pat in patterns:
            if pat in t:
                return key
    return None


def _normalize_rrn(value: str) -> str:
    """Strip alles behalve cijfers, max 11 chars."""
    digits = "".join(c for c in value if c.isdigit())
    return digits[:11]


def _truncate(value: str, max_len: int) -> str:
    """Veilig knippen om DB-truncation errors te vermijden."""
    return value.strip()[:max_len]


def parse_answers(
    answers: list[dict],
    question_titles: dict[int, str],
    answer_values: dict[int, str],
) -> dict[str, str | None]:
    """
    Returnt dict met child_rrn, parent_rrn.
    Normaliseert RRN's (alleen cijfers, max 11).
    """
    result: dict[str, str | None] = {k: None for k in REQUIRED_QUESTION_KEYS}
    for ans in answers:
        question_id = ans.get("question_id")
        if isinstance(question_id, list | tuple):
            question_id = question_id[0]
        title = question_titles.get(question_id, "")
        key = classify_question(title)
        if not key:
            continue

        # Waarde kan in value_text_box (free text) of value_answer_id (multi-choice)
        value: str | None = None
        text = ans.get("value_text_box")
        if text:
            value = str(text).strip()
        else:
            ansid = ans.get("value_answer_id")
            if isinstance(ansid, list | tuple):
                ansid = ansid[0]
            if ansid:
                value = answer_values.get(ansid)

        if not value:
            continue

        normalized = _normalize_rrn(value)
        if len(normalized) == 11:
            result[key] = normalized
        # Anders: ongeldige RRN → blijft None, fiche wordt later overgeslagen

    return result


def parse_properties(properties) -> dict[str, str | None]:
    """
    Parse Odoo Properties-veld (registration_properties) naar
    child_first_name / child_last_name. Odoo levert dit als list[dict],
    elk dict met o.a. 'string' (label) en 'value' (waarde).
    """
    result: dict[str, str | None] = {"child_first_name": None, "child_last_name": None}
    if not properties or not isinstance(properties, list):
        return result

    for prop in properties:
        if not isinstance(prop, dict):
            continue
        label = prop.get("string") or ""
        key = classify_property(label)
        if not key:
            continue
        value = prop.get("value")
        if value is None or value == "" or value is False:
            continue
        result[key] = _truncate(str(value), 100)

    return result


def detect_questions(question_titles: list[str]) -> dict[str, list[str]]:
    """Voor 'Test verbinding': welke conventionele titels zijn aanwezig/missing."""
    found: dict[str, list[str]] = {k: [] for k in REQUIRED_QUESTION_KEYS}
    for title in question_titles:
        key = classify_question(title)
        if key:
            found[key].append(title)
    missing = [k for k, v in found.items() if not v]
    return {
        "found": [t for tlist in found.values() for t in tlist],
        "missing": missing,
    }


def normalize_kbo(vat: str | None) -> str:
    """Odoo res.company.vat = 'BE0123456789' → '0123456789'."""
    if not vat:
        return ""
    return vat.replace("BE", "").replace(".", "").replace(" ", "").strip()
