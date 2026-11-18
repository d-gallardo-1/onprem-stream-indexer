"""Analytics arithmetic against the filtered corpus, and the deterministic estimator."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from statistics import median

import pytest

from app.analytics.estimator import PRIOR_STRENGTH, estimate
from app.analytics.summary import median_gbp, percent, summarise, to_percent
from app.data.corpus import default_rulings
from app.data.tenants import INDUSTRIAL, LAW as LAW_PROFILE
from app.models import Matter, Outcome

from .conftest import API, IND, LAW

LAW_RULINGS = default_rulings(LAW_PROFILE)
IND_RULINGS = default_rulings(INDUSTRIAL)
BOARD = "Halden Labour Review Board"


def analytics(client, **params) -> tuple[dict, list[dict]]:
    payload = client.get(f"{API}/search/snapshot", params=params).json()
    return payload["analytics"], [hit["ruling"] for hit in payload["results"]]


@pytest.mark.parametrize(
    "params",
    [
        {"tenant_id": LAW},
        {"tenant_id": LAW, "authority": BOARD},
        {"tenant_id": LAW, "q": "costs", "outcome": "SETTLED_WITH_COSTS"},
        {"tenant_id": IND, "q": "order"},
        {"tenant_id": IND, "q": "nothing-matches-this"},
    ],
)
def test_figures_match_the_filtered_rulings(client, params):
    result, rulings = analytics(client, **params)
    amounts = [ruling["financial_exposure_gbp"] for ruling in rulings]

    assert result["rulings"] == len(rulings)
    assert result["exposure"]["total_gbp"] == sum(amounts)
    assert Decimal(result["exposure"]["median_gbp"]) == (
        Decimal(str(median(amounts))) if amounts else Decimal("0.00"))
    assert result["exposure"]["highest_gbp"] == max(amounts, default=0)
    assert sum(share["count"] for share in result["outcome_distribution"]) == len(rulings)
    for share in result["outcome_distribution"]:
        matching = sum(1 for ruling in rulings if ruling["outcome"] == share["outcome"])
        assert share["count"] == matching
        assert share["percent"] == (round(matching * 1000 / len(rulings)) / 10 if rulings else 0)


def test_distribution_lists_all_four_outcomes_and_sums_to_one_hundred():
    shares = summarise(LAW_RULINGS).outcome_distribution

    assert [share.outcome for share in shares] == list(Outcome)
    assert [share.count for share in shares] == [4, 3, 3, 0]
    assert sum(share.percent for share in shares) == 100.0


def test_money_is_exact_and_never_a_float():
    result = summarise(LAW_RULINGS)

    assert result.exposure.total_gbp == 1_938_300 and isinstance(result.exposure.total_gbp, int)
    assert result.exposure.median_gbp == Decimal("111750.00")
    assert median_gbp([1, 2]) == Decimal("1.50") and median_gbp([7]) == Decimal("7.00")
    assert median_gbp([10**15 + 1, 10**15 + 2]) == Decimal("1000000000000001.50")


def test_percent_rounds_half_up_from_an_exact_fraction():
    assert percent(1, 3) == 33.3 and percent(2, 3) == 66.7
    assert percent(1, 8) == 12.5 and to_percent(Fraction(1, 16)) == 6.3  # 6.25 rounds up
    assert percent(0, 0) == 0.0


def test_top_clauses_are_ranked_by_citations_then_name():
    clauses = [(c.article, c.count) for c in summarise(LAW_RULINGS).top_clauses]

    assert clauses == [("COC art. 31", 4), ("COC art. 14", 3), ("LRS s. 22", 3),
                       ("COC art. 52", 2), ("COC art. 77", 2)]


def test_authority_trend_counts_each_year_and_names_the_direction():
    trends = {trend.authority: trend for trend in summarise(IND_RULINGS).authority_trend}
    inspectorate = trends["Kestrel Industrial Safety Inspectorate"]

    assert [(p.year, p.rulings, p.upheld_or_ordered) for p in inspectorate.by_year] == [
        (2024, 2, 2), (2025, 2, 1)]
    assert (inspectorate.percent, inspectorate.direction) == (75.0, "FALLING")
    assert trends["Harbour Works Enforcement Tribunal"].direction == "RISING"
    assert sum(trend.rulings for trend in trends.values()) == len(IND_RULINGS)
    assert summarise(IND_RULINGS[:1]).authority_trend[0].direction == "SINGLE_YEAR"


def test_estimate_follows_its_published_formula():
    result = estimate(LAW_RULINGS, target=Outcome.UPHELD, authority=BOARD, matter=Matter.LABOUR)
    base = Fraction(4, 10)
    by_authority = (2 + PRIOR_STRENGTH * base) / (4 + PRIOR_STRENGTH)
    by_matter = (2 + PRIOR_STRENGTH * base) / (4 + PRIOR_STRENGTH)
    expected = (2 + PRIOR_STRENGTH * (by_authority + by_matter) / 2) / (4 + PRIOR_STRENGTH)

    assert result.estimated_percent == to_percent(expected) == 47.5
    assert [(f.matching, f.rulings) for f in result.factors] == [(4, 10), (2, 4), (2, 4), (2, 4)]
    assert result.sample_size == 4 and result.confidence == "MODERATE"


def test_estimate_is_deterministic_and_pulled_towards_the_base_rate():
    def run(**choice):
        return estimate(IND_RULINGS, target=Outcome.COMPLIANCE_ORDER, **choice)

    chosen = {"authority": "Kestrel Industrial Safety Inspectorate",
              "matter": Matter.INDUSTRIAL_SAFETY}
    assert run(**chosen) == run(**chosen)
    # Raw rate is 3 of 4 (75 %); the tenant-wide rate is 40 %. The estimate sits between.
    assert 40.0 < run(**chosen).estimated_percent < 75.0
    assert run(authority=None, matter=None).estimated_percent == 40.0


def test_estimate_without_any_ruling_is_even_and_flagged_low():
    result = estimate([], target=Outcome.DISMISSED, authority="Anything", matter=Matter.LABOUR)

    assert result.estimated_percent == 25.0
    assert result.sample_size == 0 and result.confidence == "LOW"


def test_estimate_endpoint_carries_the_disclaimer_and_validates_input(client):
    url = f"{API}/analytics/estimate"
    result = client.get(url, params={"tenant_id": LAW, "matter": "LABOUR"}).json()

    assert "not legal advice" in result["disclaimer"]
    assert result["target_outcome"] == "UPHELD" and result["sample_size"] == 4
    assert client.get(url, params={"tenant_id": LAW, "matter": "MARITIME"}).status_code == 422
    assert "not legal advice" in client.get(
        f"{API}/search/snapshot", params={"tenant_id": LAW}).json()["analytics"]["disclaimer"]
