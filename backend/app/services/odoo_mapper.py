"""
Mapping helpers: Odoo records → lokale rijen.

Conventie voor vraag-titels (case-insensitive, partial match):
  - 'rrn kind' / 'rijksregisternummer kind'        → child.rrn
  - 'voornaam kind' / 'kind voornaam'              → child.first_name
  - 'achternaam kind' / 'kind achternaam'          → child.last_name
  - 'rrn ouder' / 'rijksregisternummer ouder'      → parent.rrn
"""
from __future__ import annotations

# Canonieke titels (lowercase) — alle moeten als substring matchen
QUESTION_PATTERNS = {
    "child_rrn": ["rrn kind", "rijksregisternummer kind", "rijksregister kind"],
    "child_first_name": ["voornaam kind", "kind voornaam", "first name child"],
    "child_last_name": ["achternaam kind", "kind achternaam", "last name child", "naam kind"],
    "parent_rrn": ["rrn ouder", "rijksregisternummer ouder", "rijksregister ouder"],
}

REQUIRED_QUESTION_KEYS = ["child_rrn", "child_first_name", "child_last_name", "parent_rrn"]


def classify_question(title: str) -> str | None:
    """
    Geeft de canonieke key terug (child_rrn, child_first_name, etc.) of None
    als de title niet matcht.
    """
    if not title:
        return None
    t = title.lower().strip()
    # Specifieke matches eerst (langste eerst om "naam kind" niet child_last te laten matchen voor "voornaam kind")
    ordered = [
        ("child_rrn", QUESTION_PATTERNS["child_rrn"]),
        ("parent_rrn", QUESTION_PATTERNS["parent_rrn"]),
        ("child_first_name", QUESTION_PATTERNS["child_first_name"]),
        ("child_last_name", QUESTION_PATTERNS["child_last_name"]),
    ]
    for key, patterns in ordered:
        for pat in patterns:
            if pat in t:
                return key
    return None


def parse_answers(
    answers: list[dict],
    question_titles: dict[int, str],
    answer_values: dict[int, str],
) -> dict[str, str | None]:
    """
    Returnt dict met child_rrn, child_first_name, child_last_name, parent_rrn.

    answers: list van event.registration.answer records met velden:
      registration_id, question_id, value_text_box, value_answer_id
    question_titles: mapping question_id → title (voor classify_question)
    answer_values: mapping answer_id → name (voor multiple-choice)
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

        if value:
            result[key] = value

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
