"""BOW kinderopvang halve-dag classificatie.

Regel:
- 1–4u per dag = halve opvangdag (0.5)
- 5–11u per dag = volle opvangdag (1.0)
- <1u of >11u = geclampt (skip resp. 1.0)

We werken in halve-dag eenheden (int) zodat optellingen exact blijven:
  1 halve dag = 1, 1 volle dag = 2.
Eindwaarde voor f86_2110_numberofday1 = ceil(total_half_days / 2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Literal


Classification = Literal["skip", "half", "full"]


@dataclass
class DayClassification:
    total_hours: float
    days_in_range: int            # aantal kalenderdagen tussen start en eind (incl.)
    avg_hours_per_day: float
    classification: Classification
    half_days: int                # totaal in halve-dag eenheden (= 1 of 2 per dag × days_in_range)


def classify_event(date_begin: datetime | None, date_end: datetime | None) -> DayClassification | None:
    """Classificeer een Odoo event op basis van begin- en eindtijd.

    Returns None als de input onbruikbaar is (ontbrekende velden, end < begin).
    """
    if not date_begin or not date_end or date_end < date_begin:
        return None
    total_seconds = (date_end - date_begin).total_seconds()
    total_hours = total_seconds / 3600.0
    days_in_range = (date_end.date() - date_begin.date()).days + 1
    if days_in_range <= 0:
        return None
    avg = total_hours / days_in_range

    if avg < 1.0:
        return DayClassification(total_hours, days_in_range, avg, "skip", 0)
    if avg <= 4.0:
        return DayClassification(total_hours, days_in_range, avg, "half", days_in_range)
    return DayClassification(total_hours, days_in_range, avg, "full", days_in_range * 2)


def half_days_to_xml_days(half_days: int) -> int:
    """Convert halve-dag eenheden naar geheel-dag aantal voor f86_2110_numberofday.

    Afronding naar boven (ceil) — 1 halve dag telt nog steeds als 1 dag in de XML.
    """
    return ceil(half_days / 2)
