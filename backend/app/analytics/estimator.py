"""Transparent outcome estimate: a smoothed empirical rate with every step exposed.

It answers "among this tenant's rulings, how often did a matter like this, before
this authority, end with the chosen outcome?". It is exact rational arithmetic
over counts: no training step, no hidden state, the same answer on every call.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Callable, Iterable

from ..data.tenants import MATTER_LABELS
from ..models import Matter, Outcome, Ruling
from .models import Estimate, EstimateFactor
from .summary import to_percent

#: Notional rulings each smoothing step adds at the rate of the step before it.
PRIOR_STRENGTH = 4
LOW_SAMPLE = 3
MODERATE_SAMPLE = 8


def _confidence(sample_size: int) -> str:
    if sample_size < LOW_SAMPLE:
        return "LOW"
    return "MODERATE" if sample_size < MODERATE_SAMPLE else "HIGHER"


def _smoothed(matching: int, total: int, prior: Fraction) -> Fraction:
    return (matching + PRIOR_STRENGTH * prior) / (total + PRIOR_STRENGTH)


def estimate(rulings: Iterable[Ruling], *, target: Outcome, authority: str | None,
             matter: Matter | None) -> Estimate:
    rulings = list(rulings)

    def count(test: Callable[[Ruling], bool]) -> tuple[int, int]:
        subset = [ruling for ruling in rulings if test(ruling)]
        return sum(1 for ruling in subset if ruling.outcome == target), len(subset)

    hits, total = count(lambda ruling: True)
    # With no rulings at all, every one of the four outcomes is equally likely.
    base = Fraction(hits, total) if total else Fraction(1, len(Outcome))
    factors = [EstimateFactor(label="All rulings of this tenant", matching=hits, rulings=total,
                              percent=to_percent(base))]

    def step(label: str, test: Callable[[Ruling], bool], prior: Fraction) -> Fraction:
        matching, size = count(test)
        rate = _smoothed(matching, size, prior)
        factors.append(EstimateFactor(label=label, matching=matching, rulings=size,
                                      percent=to_percent(rate)))
        return rate

    by_authority = by_matter = base
    if authority:
        by_authority = step(f"Authority: {authority}", lambda r: r.authority == authority, base)
    if matter:
        by_matter = step(f"Matter: {MATTER_LABELS[matter]}", lambda r: r.matter == matter, base)

    def both(ruling: Ruling) -> bool:
        return (not authority or ruling.authority == authority) and (
            not matter or ruling.matter == matter)

    final = step("Rulings matching both choices", both, (by_authority + by_matter) / 2)
    sample_size = factors[-1].rulings
    return Estimate(
        target_outcome=target,
        authority=authority or None,
        matter=matter,
        sample_size=sample_size,
        confidence=_confidence(sample_size),
        estimated_percent=to_percent(final),
        factors=factors,
    )
