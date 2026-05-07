from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.schemas.export import AddressSchema, BelcotaxRequest, ParticipationSchema


@dataclass
class AddressData:
    street: str
    zip: str
    city: str
    country_code: int


@dataclass
class Fiche28186Data:
    parent_rrn: str
    parent_last_name: str
    parent_first_name: str
    parent_address: AddressData
    child_rrn: str
    child_last_name: str
    child_first_name: str
    child_birth_date_formatted: str  # DD-MM-YYYY, derived from RRN
    child_address: AddressData        # fallback naar parent_address indien kind geen adres heeft
    total_amount_cents: int
    total_days: int
    period_start: date
    period_end: date


@dataclass
class AggregationResult:
    fiches: list[Fiche28186Data]
    skipped_count: int
    warnings: list[dict]


_HIGH_DAILY_RATE_CENTS = 5_000  # €50/dag
_MAX_AMOUNT_CENTS = 1_000_000   # €10.000/kind
_MAX_PERIOD_DAYS = 365


def _to_address(addr: AddressSchema) -> AddressData:
    return AddressData(street=addr.street, zip=addr.zip, city=addr.city, country_code=addr.country_code)


def aggregate(request: BelcotaxRequest, birth_dates: dict[str, str]) -> AggregationResult:
    """
    Groups confirmed participations by (kbo, income_year, parent_rrn, child_rrn).
    birth_dates: mapping of rrn → DD-MM-YYYY (pre-computed by export_service after RRN validation).
    """
    AggKey = tuple[str, int, str, str]
    groups: dict[AggKey, list[ParticipationSchema]] = defaultdict(list)
    skipped = 0

    for p in request.participations:
        if p.status != "confirmed":
            skipped += 1
            continue
        key: AggKey = (request.organization.kbo, request.income_year, p.parent.rrn, p.child.rrn)
        groups[key].append(p)

    fiches: list[Fiche28186Data] = []
    warnings: list[dict] = []

    for (kbo, year, parent_rrn, child_rrn), items in groups.items():
        first = items[0]
        total_cents = round(sum(i.amount_paid for i in items) * 100)
        total_days = sum(i.days for i in items)
        period_start = min(i.start_date for i in items)
        period_end = max(i.end_date for i in items)

        if total_days > 0 and total_cents // total_days > _HIGH_DAILY_RATE_CENTS:
            warnings.append({
                "type": "high_daily_rate",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"Dagtarief €{total_cents / total_days / 100:.2f} overschrijdt €50,00",
            })

        if total_cents > _MAX_AMOUNT_CENTS:
            warnings.append({
                "type": "high_total_amount",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"Totaalbedrag €{total_cents / 100:.2f} overschrijdt €10.000,00",
            })

        if (period_end - period_start).days > _MAX_PERIOD_DAYS:
            warnings.append({
                "type": "long_period",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"Periode van {(period_end - period_start).days} dagen overschrijdt 365 dagen",
            })

        child_addr = (
            _to_address(first.child.address)
            if first.child.address
            else _to_address(first.parent.address)
        )
        fiches.append(Fiche28186Data(
            parent_rrn=parent_rrn,
            parent_last_name=first.parent.last_name,
            parent_first_name=first.parent.first_name,
            parent_address=_to_address(first.parent.address),
            child_rrn=child_rrn,
            child_last_name=first.child.last_name,
            child_first_name=first.child.first_name,
            child_birth_date_formatted=birth_dates.get(child_rrn, ""),
            child_address=child_addr,
            total_amount_cents=total_cents,
            total_days=total_days,
            period_start=period_start,
            period_end=period_end,
        ))

    return AggregationResult(fiches=fiches, skipped_count=skipped, warnings=warnings)
