"""The default corpus and the crawl sequence: synthetic, even and reproducible."""

from __future__ import annotations

import re

from app.data.corpus import crawled_ruling, default_rulings
from app.data.tenants import TENANT_PROFILES
from app.models import Outcome, RulingSource

DEFAULT = {p.tenant.tenant_id: default_rulings(p) for p in TENANT_PROFILES}
EVERY = [ruling for rulings in DEFAULT.values() for ruling in rulings]
#: Words that would make an invented record look like a decision of a real body.
REAL_WORLD = ("Employment Appeal Tribunal", "Health & Safety Executive", "Health and Safety",
              "Technology & Construction Court", "UK-", "EAT", "HSE", "High Court")


def test_corpus_has_at_least_sixteen_rulings_split_evenly():
    sizes = [len(rulings) for rulings in DEFAULT.values()]

    assert sum(sizes) >= 16
    assert len(set(sizes)) == 1 and len(DEFAULT) == 2


def test_every_docket_has_the_synthetic_prefix_and_is_unique():
    ids = [ruling.docket_id for ruling in EVERY]

    assert len(set(ids)) == len(ids)
    for profile in TENANT_PROFILES:
        for ruling in DEFAULT[profile.tenant.tenant_id]:
            assert re.fullmatch(rf"SYN-{profile.code}-\d{{4}}-\d{{4}}", ruling.docket_id)
            assert ruling.tenant_id == profile.tenant.tenant_id
            assert ruling.docket_id[8:12] == str(ruling.decision_date.year)


def test_no_record_names_a_real_body():
    for ruling in EVERY:
        text = " ".join([ruling.docket_id, ruling.title, ruling.authority,
                         ruling.summary_excerpt, *ruling.cited_articles])
        for word in REAL_WORLD:
            assert word not in text, f"{ruling.docket_id} mentions {word!r}"


def test_authorities_matters_and_officers_come_from_the_tenants_own_lists():
    for profile in TENANT_PROFILES:
        for ruling in DEFAULT[profile.tenant.tenant_id]:
            assert ruling.authority in profile.authorities[ruling.matter]
            assert ruling.judge_or_inspector in profile.officers
            assert ruling.cited_articles and ruling.financial_exposure_gbp > 0
            assert isinstance(ruling.financial_exposure_gbp, int)


def test_all_four_outcomes_appear_in_the_corpus():
    assert {ruling.outcome for ruling in EVERY} == set(Outcome)
    assert all(ruling.source == RulingSource.DEFAULT_CORPUS for ruling in EVERY)


def test_crawl_sequence_is_reproducible_and_stays_inside_the_tenant():
    for profile in TENANT_PROFILES:
        first = crawled_ruling(profile, 1)

        assert first == crawled_ruling(profile, 1)
        assert first != crawled_ruling(profile, 2)
        assert first.docket_id == f"SYN-{profile.code}-CRAWL-0001"
        assert first.tenant_id == profile.tenant.tenant_id
        assert first.source == RulingSource.SIMULATED_CRAWL
        assert first.authority in profile.authorities[first.matter]
        assert "simulated crawl" in first.summary_excerpt
