"""
Belgian national registry number (RRN / rijksregisternummer) validation.

Format: YYMMDD-SSS-CC
- YY: year of birth (2 digits)
- MM: month of birth
- DD: day of birth
- SSS: sequence number (odd = male, even = female)
- CC: check digit = 97 - (number % 97)
  For born >= 2000: the 9-digit number is prefixed with '2' before mod 97.
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class RRNInfo:
    is_valid: bool
    error: str | None
    birth_date: date | None = None
    formatted: str | None = None  # DD-MM-YYYY


def validate_rrn(rrn: str) -> RRNInfo:
    digits = rrn.replace(".", "").replace("-", "").replace(" ", "")

    if not digits.isdigit():
        return RRNInfo(is_valid=False, error=f"RRN bevat niet-cijfer tekens: {rrn!r}")
    if len(digits) != 11:
        return RRNInfo(is_valid=False, error=f"RRN moet 11 cijfers hebben, kreeg {len(digits)}: {rrn!r}")

    first9 = int(digits[:9])
    checksum = int(digits[9:11])

    post2000 = 97 - (int("2" + digits[:9]) % 97) == checksum
    pre2000 = 97 - (first9 % 97) == checksum

    if not post2000 and not pre2000:
        return RRNInfo(is_valid=False, error=f"Ongeldig controlegetal voor RRN: {rrn!r}")

    yy = int(digits[0:2])
    mm = int(digits[2:4])
    dd = int(digits[4:6])

    # Month can be > 20 or > 40 for certain BIS numbers — normalize
    if mm > 40:
        mm -= 40
    elif mm > 20:
        mm -= 20

    century = 2000 if post2000 else 1900
    full_year = century + yy

    try:
        birth_date = date(full_year, mm, dd)
    except ValueError:
        return RRNInfo(is_valid=False, error=f"Ongeldig geboortedatum in RRN: {rrn!r}")

    formatted = birth_date.strftime("%d-%m-%Y")
    return RRNInfo(is_valid=True, error=None, birth_date=birth_date, formatted=formatted)
