"""Builds the default corpus and the rulings a simulated crawl "finds".

A crawl never fetches anything: its rulings come from the deterministic
generator below, so the same crawl number always yields the same ruling.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from ..models import Outcome, Ruling, RulingSource
from . import rulings_industrial, rulings_law
from .tenants import INDUSTRIAL, LAW, TenantProfile

_ROWS = {LAW.tenant.tenant_id: rulings_law.ROWS, INDUSTRIAL.tenant.tenant_id: rulings_industrial.ROWS}

_PARTY_STEMS = ("Corvane", "Lumestra", "Pellwick", "Dravos", "Yarrowby", "Quenthar", "Osmere",
                "Vantry", "Kilnwarth", "Sablewood", "Zephran", "Ulverith")
_PARTY_SUFFIXES = ("Holdings", "Logistics", "Works", "Systems", "Marine", "Engineering")
_TOPICS = {
    "LAW": ("a disputed price adjustment clause", "late payment of milestone invoices",
            "a withdrawn shift allowance", "termination of a distribution agreement",
            "an unconsulted change of working hours"),
    "IND": ("an unguarded transfer conveyor", "a missing lifting equipment register",
            "an isolation valve left unlocked", "a bypassed safety interlock",
            "untested emergency lighting on a jetty"),
}
_CRAWL_FIRST_DAY = date(2026, 1, 12)


def default_rulings(profile: TenantProfile) -> list[Ruling]:
    rulings = []
    for sequence, title, authority, matter, decided, outcome, exposure, articles, officer, text \
            in _ROWS[profile.tenant.tenant_id]:
        rulings.append(Ruling(
            docket_id=f"SYN-{profile.code}-{decided[:4]}-{sequence:04d}",
            tenant_id=profile.tenant.tenant_id,
            title=title,
            authority=authority,
            matter=matter,
            decision_date=date.fromisoformat(decided),
            outcome=outcome,
            financial_exposure_gbp=exposure,
            cited_articles=list(articles),
            judge_or_inspector=officer,
            summary_excerpt=text,
        ))
    return rulings


def crawled_ruling(profile: TenantProfile, number: int) -> Ruling:
    """Ruling number ``number`` (1-based) of this tenant's simulated crawls."""
    rng = random.Random(f"crawl:{profile.tenant.tenant_id}:{number}")
    matter = rng.choice(list(profile.authorities))
    authority = rng.choice(profile.authorities[matter])
    first, second = rng.sample(_PARTY_STEMS, 2)
    topic = rng.choice(_TOPICS[profile.code])
    outcome = rng.choice(list(Outcome))
    statute = profile.statutes[matter].split("(")[1].rstrip(")")
    unit = "art." if profile.code == "LAW" else "reg."
    articles = sorted({f"{statute} {unit} {rng.randint(3, 90)}" for _ in range(rng.randint(1, 3))})
    return Ruling(
        docket_id=f"SYN-{profile.code}-CRAWL-{number:04d}",
        tenant_id=profile.tenant.tenant_id,
        title=f"{first} {rng.choice(_PARTY_SUFFIXES)} v {second} {rng.choice(_PARTY_SUFFIXES)}",
        authority=authority,
        matter=matter,
        decision_date=_CRAWL_FIRST_DAY + timedelta(days=7 * number + rng.randrange(5)),
        outcome=outcome,
        financial_exposure_gbp=rng.randrange(20, 400) * 500,
        cited_articles=articles,
        judge_or_inspector=rng.choice(profile.officers),
        summary_excerpt=(
            f"Synthetic ruling added by a simulated crawl. The matter concerned {topic}; "
            f"the outcome recorded is {outcome.value.replace('_', ' ').lower()}."
        ),
        source=RulingSource.SIMULATED_CRAWL,
    )
