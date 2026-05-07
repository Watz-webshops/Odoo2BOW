"""
Optionele XSD validatie tegen de officiële Belcotax-on-web XSD.

Het bestand `Belcotax-2025.xsd` wordt verwacht in `backend/app/schemas/`.
Zonder XSD-bestand wordt validatie automatisch overgeslagen.
"""
from pathlib import Path

from lxml import etree

# Mogelijke zoekpaden voor de XSD (in volgorde van prioriteit)
_SEARCH_PATHS = [
    Path(__file__).parent.parent / "schemas" / "Belcotax-2025.xsd",
    Path(__file__).parent / "schemas" / "Belcotax-2025.xsd",
]
_schema_cache: etree.XMLSchema | None = None
_schema_resolved_path: Path | None = None


def _get_schema() -> etree.XMLSchema | None:
    global _schema_cache, _schema_resolved_path
    if _schema_cache is not None:
        return _schema_cache
    for path in _SEARCH_PATHS:
        if path.is_file():
            with path.open("rb") as fh:
                doc = etree.parse(fh)
            _schema_cache = etree.XMLSchema(doc)
            _schema_resolved_path = path
            return _schema_cache
    return None


def get_schema_path() -> Path | None:
    """Geeft het pad terug van de geladen XSD, of None indien niet geladen."""
    _get_schema()
    return _schema_resolved_path


def validate_xml(xml_bytes: bytes) -> tuple[bool, list[str]]:
    """
    Returns (is_valid, errors). is_valid is True wanneer:
      - de XSD niet beschikbaar is (validatie overgeslagen), of
      - de XML strikt voldoet aan de XSD.
    """
    schema = _get_schema()
    if schema is None:
        return True, []  # geen XSD aanwezig — skip
    try:
        doc = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        return False, [f"XML parse error: {e}"]
    if schema.validate(doc):
        return True, []
    return False, [str(e) for e in schema.error_log]
