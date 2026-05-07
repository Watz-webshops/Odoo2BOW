import pytest
from datetime import date
from app.services.rrn_validator import validate_rrn


# Bekende geldige RRN's (gesynthetiseerd voor tests)
# Pre-2000: 850101-123-45  → yy=85, mm=01, dd=01, seq=123, check=97-(850101123%97)
def _make_rrn(yy: int, mm: int, dd: int, seq: int, post2000: bool = False) -> str:
    base = f"{yy:02d}{mm:02d}{dd:02d}{seq:03d}"
    n = int(("2" if post2000 else "") + base)
    check = 97 - (n % 97)
    return base + f"{check:02d}"


VALID_PRE2000 = _make_rrn(85, 1, 1, 123, post2000=False)
VALID_POST2000 = _make_rrn(15, 1, 21, 54, post2000=True)


def test_valid_pre2000():
    result = validate_rrn(VALID_PRE2000)
    assert result.is_valid
    assert result.birth_date == date(1985, 1, 1)
    assert result.formatted == "01-01-1985"


def test_valid_post2000():
    result = validate_rrn(VALID_POST2000)
    assert result.is_valid
    assert result.birth_date == date(2015, 1, 21)
    assert result.formatted == "21-01-2015"


def test_wrong_length():
    result = validate_rrn("123")
    assert not result.is_valid
    assert "11 cijfers" in result.error


def test_non_digits():
    result = validate_rrn("abcdefghijk")
    assert not result.is_valid


def test_invalid_checksum():
    bad = VALID_PRE2000[:-2] + "00"
    result = validate_rrn(bad)
    assert not result.is_valid
    assert "controlegetal" in result.error


def test_strips_separators():
    formatted = f"{VALID_PRE2000[:6]}-{VALID_PRE2000[6:9]}-{VALID_PRE2000[9:]}"
    result = validate_rrn(formatted)
    assert result.is_valid
