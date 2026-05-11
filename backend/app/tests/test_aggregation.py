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


def _participation(
    event_id, start, end, days, amount, parent_rrn, child_rrn,
    status="confirmed", half_days=None,
):
    return ParticipationSchema(
        event_id=event_id,
        event_name="Kamp",
        start_date=start,
        end_date=end,
        days=days,
        amount_paid=amount,
        status=status,
        half_days=half_days,
        parent=ParentSchema(
            rrn=parent_rrn,
            first_name="Jan",
            last_name="Peeters",
            address=AddressSchema(street="Straat 1", zip="3000", city="Leuven", country_code=150),
        ),
        child=ChildSchema(rrn=child_rrn, first_name="Emma", last_name="Peeters"),
    )


BIRTH_DATES = {"85010112345": "01-01-1985", "15012154321": "21-01-2015"}


def test_two_close_participations_aggregated_in_one_period():
    # Gap = 11 weken minus 30 dagen — kleiner dan 31 dagen ↔ blijft één cluster.
    p1 = _participation("e1", date(2025, 4, 7), date(2025, 4, 11), 5, 150.0, "85010112345", "15012154321")
    p2 = _participation("e2", date(2025, 5, 5), date(2025, 5, 9), 5, 175.0, "85010112345", "15012154321")
    result = aggregate(_make_request([p1, p2]), BIRTH_DATES)

    assert len(result.fiches) == 1
    fiche = result.fiches[0]
    assert fiche.total_amount_cents == 32500
    assert fiche.period2 is None
    assert fiche.period1.start == date(2025, 4, 7)
    assert fiche.period1.end == date(2025, 5, 9)


def test_distant_participations_split_in_two_periods():
    # Gap > 31 dagen → twee aparte perioden.
    p1 = _participation("e1", date(2025, 4, 7), date(2025, 4, 11), 5, 150.0, "85010112345", "15012154321")
    p2 = _participation("e2", date(2025, 7, 1), date(2025, 7, 5), 5, 175.0, "85010112345", "15012154321")
    result = aggregate(_make_request([p1, p2]), BIRTH_DATES)

    assert len(result.fiches) == 1
    fiche = result.fiches[0]
    assert fiche.period2 is not None
    assert fiche.period1.start == date(2025, 4, 7)
    assert fiche.period1.end == date(2025, 4, 11)
    assert fiche.period2.start == date(2025, 7, 1)
    assert fiche.period2.end == date(2025, 7, 5)
    assert fiche.period1.amount_cents == 15000
    assert fiche.period2.amount_cents == 17500


def test_three_clusters_warning_and_clamp_to_two():
    p1 = _participation("e1", date(2025, 1, 1), date(2025, 1, 5), 5, 100.0, "85010112345", "15012154321")
    p2 = _participation("e2", date(2025, 5, 1), date(2025, 5, 5), 5, 100.0, "85010112345", "15012154321")
    p3 = _participation("e3", date(2025, 10, 1), date(2025, 10, 5), 5, 100.0, "85010112345", "15012154321")
    result = aggregate(_make_request([p1, p2, p3]), BIRTH_DATES)

    types = [w["type"] for w in result.warnings]
    assert "too_many_periods" in types
    fiche = result.fiches[0]
    assert fiche.period2 is not None
    # Periode 2 = p2 + p3 samengevoegd
    assert fiche.period2.start == date(2025, 5, 1)
    assert fiche.period2.end == date(2025, 10, 5)


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


# ── Halve-dag teller ─────────────────────────────────────────────────────────
def test_half_days_used_when_provided():
    # half_days=1 (= 1 halve dag) — XML moet 1 dag tonen (ceil(1/2) = 1).
    p = _participation("e1", date(2025, 7, 1), date(2025, 7, 1), 1, 50.0, "85010112345", "15012154321",
                       half_days=1)
    result = aggregate(_make_request([p]), BIRTH_DATES)
    assert result.fiches[0].period1.half_days == 1
    assert result.fiches[0].period1.xml_days == 1


def test_full_day_via_half_days_field():
    # half_days=2 (= 1 volle dag)
    p = _participation("e1", date(2025, 7, 1), date(2025, 7, 1), 1, 100.0, "85010112345", "15012154321",
                       half_days=2)
    result = aggregate(_make_request([p]), BIRTH_DATES)
    assert result.fiches[0].period1.xml_days == 1


def test_half_days_falls_back_to_days_times_two():
    # Zonder half_days → fallback days*2 = 5*2 = 10 half_days → 5 xml dagen.
    p = _participation("e1", date(2025, 7, 1), date(2025, 7, 5), 5, 100.0, "85010112345", "15012154321",
                       half_days=None)
    result = aggregate(_make_request([p]), BIRTH_DATES)
    assert result.fiches[0].period1.half_days == 10
    assert result.fiches[0].period1.xml_days == 5


def test_half_days_sum_across_two_periods():
    # Periode 1: 5 halve dagen, Periode 2: 6 halve dagen.
    p1 = _participation("e1", date(2025, 4, 1), date(2025, 4, 5), 5, 100.0, "85010112345", "15012154321",
                        half_days=5)
    p2 = _participation("e2", date(2025, 9, 1), date(2025, 9, 6), 6, 100.0, "85010112345", "15012154321",
                        half_days=6)
    result = aggregate(_make_request([p1, p2]), BIRTH_DATES)
    fiche = result.fiches[0]
    assert fiche.period1.half_days == 5
    assert fiche.period2.half_days == 6
    # XML dagen: ceil(5/2)=3 + ceil(6/2)=3 = 6
    assert fiche.total_days == 6
