from datetime import date

import pytest

from app.schemas.export import (
    AddressSchema,
    BelcotaxRequest,
    ChildSchema,
    ContactSchema,
    OrganizationPayload,
    ParentSchema,
    ParticipationSchema,
)
from app.services.aggregation import aggregate


def _make_request(participations):
    return BelcotaxRequest(
        income_year=2025,
        organization=OrganizationPayload(
            kbo="0886886638",
            name="Sportkamp Leuven VZW",
            address=AddressSchema(street="Kampstraat 12", zip="3000", city="Leuven", country_code=150),
            language_code=1,
            contact=ContactSchema(name="Admin", email="admin@sportkamp.be", phone="+32 16 12 34 56"),
        ),
        participations=participations,
    )


def _participation(event_id, start, end, days, amount, parent_rrn, child_rrn, status="confirmed"):
    return ParticipationSchema(
        event_id=event_id,
        event_name="Kamp",
        start_date=start,
        end_date=end,
        days=days,
        amount_paid=amount,
        status=status,
        parent=ParentSchema(
            rrn=parent_rrn,
            first_name="Jan",
            last_name="Peeters",
            address=AddressSchema(street="Straat 1", zip="3000", city="Leuven", country_code=150),
        ),
        child=ChildSchema(rrn=child_rrn, first_name="Emma", last_name="Peeters"),
    )


BIRTH_DATES = {"85010112345": "01-01-1985", "15012154321": "21-01-2015"}


def test_two_participations_same_parent_child_aggregated():
    p1 = _participation("e1", date(2025, 4, 7), date(2025, 4, 11), 5, 150.0, "85010112345", "15012154321")
    p2 = _participation("e2", date(2025, 7, 1), date(2025, 7, 5), 5, 175.0, "85010112345", "15012154321")
    result = aggregate(_make_request([p1, p2]), BIRTH_DATES)

    assert len(result.fiches) == 1
    fiche = result.fiches[0]
    assert fiche.total_amount_cents == 32500
    assert fiche.total_days == 10
    assert fiche.period_start == date(2025, 4, 7)
    assert fiche.period_end == date(2025, 7, 5)


def test_cancelled_participation_skipped():
    p1 = _participation("e1", date(2025, 4, 7), date(2025, 4, 11), 5, 150.0, "85010112345", "15012154321")
    p2 = _participation("e2", date(2025, 7, 1), date(2025, 7, 5), 5, 175.0, "85010112345", "15012154321", status="cancelled")
    result = aggregate(_make_request([p1, p2]), BIRTH_DATES)

    assert len(result.fiches) == 1
    assert result.skipped_count == 1
    assert result.fiches[0].total_amount_cents == 15000


def test_different_child_gives_two_fiches():
    p1 = _participation("e1", date(2025, 4, 7), date(2025, 4, 11), 5, 150.0, "85010112345", "15012154321")
    p2 = _participation("e2", date(2025, 7, 1), date(2025, 7, 5), 5, 100.0, "85010112345", "15012199999")
    result = aggregate(_make_request([p1, p2]), {**BIRTH_DATES, "15012199999": "21-01-2015"})

    assert len(result.fiches) == 2


def test_high_daily_rate_warning():
    p = _participation("e1", date(2025, 7, 1), date(2025, 7, 2), 1, 100.0, "85010112345", "15012154321")
    result = aggregate(_make_request([p]), BIRTH_DATES)
    types = [w["type"] for w in result.warnings]
    assert "high_daily_rate" in types


def test_amount_in_cents_correct():
    p = _participation("e1", date(2025, 7, 1), date(2025, 7, 5), 5, 1.23, "85010112345", "15012154321")
    result = aggregate(_make_request([p]), BIRTH_DATES)
    assert result.fiches[0].total_amount_cents == 123
