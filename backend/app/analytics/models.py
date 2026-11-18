"""Response shapes of the analytics."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from ..models import Matter, Outcome

DISCLAIMER = (
    "Illustrative statistics over an invented corpus. They describe no real court or "
    "regulator and are not legal advice."
)


class OutcomeShare(BaseModel):
    outcome: Outcome
    count: int
    percent: float


class Exposure(BaseModel):
    """Whole pounds. The median of an even count can end in .50, so it is a decimal."""

    total_gbp: int
    median_gbp: Decimal
    highest_gbp: int


class ClauseCount(BaseModel):
    article: str
    count: int


class YearPoint(BaseModel):
    year: int
    rulings: int
    upheld_or_ordered: int
    percent: float


class AuthorityTrend(BaseModel):
    authority: str
    rulings: int
    upheld_or_ordered: int
    percent: float
    #: RISING, FALLING or STEADY between the first and last year; SINGLE_YEAR otherwise.
    direction: str
    by_year: list[YearPoint]


class Analytics(BaseModel):
    disclaimer: str = DISCLAIMER
    rulings: int
    outcome_distribution: list[OutcomeShare]
    exposure: Exposure
    top_clauses: list[ClauseCount]
    authority_trend: list[AuthorityTrend]


class EstimateFactor(BaseModel):
    """One step of the estimate: how many rulings matched and what rate that gives."""

    label: str
    matching: int
    rulings: int
    percent: float


class Estimate(BaseModel):
    disclaimer: str = DISCLAIMER
    method: str = (
        "Smoothed empirical rate. The tenant-wide rate smooths the rate of the chosen "
        "authority and of the chosen matter; their average smooths the rate of rulings "
        "that match both. Each step adds four notional rulings at the rate before it."
    )
    target_outcome: Outcome
    authority: str | None
    matter: Matter | None
    #: Rulings that match both the authority and the matter.
    sample_size: int
    confidence: str
    estimated_percent: float
    factors: list[EstimateFactor]
