"""Descriptive statistics of a set of rulings, recomputed for every query."""

from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Iterable

from ..models import Outcome, Ruling
from .models import (
    Analytics,
    AuthorityTrend,
    ClauseCount,
    Exposure,
    OutcomeShare,
    YearPoint,
)

TOP_CLAUSES = 5
#: Outcomes counted by the trend: the claim or the enforcement measure stood.
STANDING = frozenset({Outcome.UPHELD, Outcome.COMPLIANCE_ORDER})
_TENTH = Decimal("0.1")
_PENNY = Decimal("0.01")


def to_percent(rate: Fraction) -> float:
    """An exact fraction as a percentage with one decimal, rounded half up."""
    exact = Decimal(rate.numerator * 100) / Decimal(rate.denominator)
    return float(exact.quantize(_TENTH, rounding=ROUND_HALF_UP))


def percent(part: int, total: int) -> float:
    return to_percent(Fraction(part, total)) if total else 0.0


def median_gbp(amounts: list[int]) -> Decimal:
    """Median of whole-pound amounts, computed without floating point."""
    if not amounts:
        return Decimal("0.00")
    ordered = sorted(amounts)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return Decimal(ordered[middle]).quantize(_PENNY)
    return (Decimal(ordered[middle - 1] + ordered[middle]) / 2).quantize(_PENNY)


def _direction(points: list[YearPoint]) -> str:
    if len(points) < 2:
        return "SINGLE_YEAR"
    first, last = points[0].percent, points[-1].percent
    if last > first:
        return "RISING"
    return "FALLING" if last < first else "STEADY"


def _trend(authority: str, rulings: list[Ruling]) -> AuthorityTrend:
    points = []
    for year in sorted({ruling.decision_date.year for ruling in rulings}):
        of_year = [ruling for ruling in rulings if ruling.decision_date.year == year]
        standing = sum(1 for ruling in of_year if ruling.outcome in STANDING)
        points.append(YearPoint(year=year, rulings=len(of_year), upheld_or_ordered=standing,
                                percent=percent(standing, len(of_year))))
    standing = sum(point.upheld_or_ordered for point in points)
    return AuthorityTrend(
        authority=authority,
        rulings=len(rulings),
        upheld_or_ordered=standing,
        percent=percent(standing, len(rulings)),
        direction=_direction(points),
        by_year=points,
    )


def summarise(rulings: Iterable[Ruling]) -> Analytics:
    rulings = list(rulings)
    outcomes = Counter(ruling.outcome for ruling in rulings)
    amounts = [ruling.financial_exposure_gbp for ruling in rulings]
    clauses = Counter(article for ruling in rulings for article in ruling.cited_articles)
    ranked = sorted(clauses.items(), key=lambda item: (-item[1], item[0]))[:TOP_CLAUSES]
    by_authority: dict[str, list[Ruling]] = {}
    for ruling in rulings:
        by_authority.setdefault(ruling.authority, []).append(ruling)
    trends = [_trend(name, members) for name, members in by_authority.items()]
    return Analytics(
        rulings=len(rulings),
        outcome_distribution=[
            OutcomeShare(outcome=outcome, count=outcomes[outcome],
                         percent=percent(outcomes[outcome], len(rulings)))
            for outcome in Outcome
        ],
        exposure=Exposure(total_gbp=sum(amounts), median_gbp=median_gbp(amounts),
                          highest_gbp=max(amounts, default=0)),
        top_clauses=[ClauseCount(article=article, count=count) for article, count in ranked],
        authority_trend=sorted(trends, key=lambda trend: (-trend.rulings, trend.authority)),
    )
