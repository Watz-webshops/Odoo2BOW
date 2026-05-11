from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.schemas.export import AddressSchema, BelcotaxRequest, ParticipationSchema
from app.services.day_classifier import half_days_to_xml_days


@dataclass
class AddressData:
    street: str
    zip: str
    city: str
    country_code: int


@dataclass
class PeriodData:
    """Eén opvangperiode binnen een fiche (periode 1 of 2)."""
    start: date
    end: date
    amount_cents: int
    half_days: int      # raw teller (1 halve dag = 1, 1 volle dag = 2)

    @property
    def xml_days(self) -> int:
        return half_days_to_xml_days(self.half_days)

    @property
    def daily_tariff_cents(self) -> int:
        d = self.xml_days
        return round(self.amount_cents / d) if d else 0


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
    period1: PeriodData
    period2: PeriodData | None = None

    # Backward-compat properties — bestaande code (xml-generator, summaries) blijft werken.
    @property
    def total_amount_cents(self) -> int:
        p2 = self.period2.amount_cents if self.period2 else 0
        return self.period1.amount_cents + p2

    @property
    def total_days(self) -> int:
        p2 = self.period2.xml_days if self.period2 else 0
        return self.period1.xml_days + p2

    @property
    def period_start(self) -> date:
        return self.period1.start

    @property
    def period_end(self) -> date:
        if self.period2:
            return self.period2.end
        return self.period1.end


@dataclass
class AggregationResult:
    fiches: list[Fiche28186Data]
    skipped_count: int
    warnings: list[dict] = field(default_factory=list)


_HIGH_DAILY_RATE_CENTS = 5_000  # €50/dag
_MAX_AMOUNT_CENTS = 1_000_000   # €10.000/kind
_MAX_PERIOD_DAYS = 365
_CLUSTER_GAP_DAYS = 31           # gap waarboven we een nieuwe periode openen


def _to_address(addr: AddressSchema) -> AddressData:
    return AddressData(street=addr.street, zip=addr.zip, city=addr.city, country_code=addr.country_code)


def _half_days(p: ParticipationSchema) -> int:
    """Halve-dag teller voor één participation. Fallback: days*2 als half_days niet expliciet gezet is."""
    if p.half_days is not None:
        return p.half_days
    return p.days * 2


def _cluster_periods(items: list[ParticipationSchema]) -> list[list[ParticipationSchema]]:
    """Splits chronologisch in clusters wanneer er een gap > _CLUSTER_GAP_DAYS is."""
    if not items:
        return []
    items_sorted = sorted(items, key=lambda i: i.start_date)
    clusters: list[list[ParticipationSchema]] = [[items_sorted[0]]]
    cluster_end = items_sorted[0].end_date
    for it in items_sorted[1:]:
        gap = (it.start_date - cluster_end).days
        if gap > _CLUSTER_GAP_DAYS:
            clusters.append([it])
        else:
            clusters[-1].append(it)
        if it.end_date > cluster_end:
            cluster_end = it.end_date
    return clusters


def _cluster_to_period(items: list[ParticipationSchema]) -> PeriodData:
    return PeriodData(
        start=min(i.start_date for i in items),
        end=max(i.end_date for i in items),
        amount_cents=round(sum(i.amount_paid for i in items) * 100),
        half_days=sum(_half_days(i) for i in items),
    )


def aggregate(request: BelcotaxRequest, birth_dates: dict[str, str]) -> AggregationResult:
    """
    Groepeert bevestigde deelnames per (kbo, income_year, parent_rrn, child_rrn).
    Splitst per fiche in maximaal 2 perioden bij een gap > 31 dagen.
    Halve-dag teller via ParticipationSchema.half_days (of fallback days*2).
    birth_dates: mapping rrn → DD-MM-YYYY (pre-computed door RRN validator).
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
        clusters = _cluster_periods(items)

        # Cluster naar periode-data
        periods = [_cluster_to_period(c) for c in clusters]

        # Warning bij 3+ clusters — clamp naar 2 (eerste 2 perioden behouden, rest in periode 2 toevoegen).
        if len(periods) > 2:
            warnings.append({
                "type": "too_many_periods",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"{len(periods)} losse opvangperiodes — XML kan er maximaal 2 bevatten",
            })
            # Voeg derde+ samen met periode 2 (alles wat na cluster 1 komt)
            merged_tail = [i for cluster in clusters[1:] for i in cluster]
            periods = [periods[0], _cluster_to_period(merged_tail)]

        period1 = periods[0]
        period2 = periods[1] if len(periods) > 1 else None

        total_cents = period1.amount_cents + (period2.amount_cents if period2 else 0)
        total_xml_days = period1.xml_days + (period2.xml_days if period2 else 0)

        if total_xml_days > 0 and total_cents // total_xml_days > _HIGH_DAILY_RATE_CENTS:
            warnings.append({
                "type": "high_daily_rate",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"Dagtarief €{total_cents / total_xml_days / 100:.2f} overschrijdt €50,00",
            })

        if total_cents > _MAX_AMOUNT_CENTS:
            warnings.append({
                "type": "high_total_amount",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"Totaalbedrag €{total_cents / 100:.2f} overschrijdt €10.000,00",
            })

        span_start = period1.start
        span_end = period2.end if period2 else period1.end
        if (span_end - span_start).days > _MAX_PERIOD_DAYS:
            warnings.append({
                "type": "long_period",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": f"Periode van {(span_end - span_start).days} dagen overschrijdt 365 dagen",
            })

        # Warning bij participations zonder half_days en zonder days — niet voorkomen door schema,
        # maar voor de zekerheid markeren we 0-day fiches.
        if total_xml_days == 0:
            warnings.append({
                "type": "zero_hours",
                "parent_rrn": parent_rrn,
                "child_rrn": child_rrn,
                "message": "Geen opvangdagen geteld (uren < 1u of half_days = 0)",
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
            period1=period1,
            period2=period2,
        ))

    return AggregationResult(fiches=fiches, skipped_count=skipped, warnings=warnings)
