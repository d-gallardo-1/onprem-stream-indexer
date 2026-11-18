"""Full-text search inside one partition: matching, ranking, filters and input caps."""

from __future__ import annotations

import pytest

from app.index.snippets import best_snippet
from app.index.tokenizer import tokenize

from .conftest import API, LAW, dockets

SNAPSHOT = f"{API}/search/snapshot"


def search(client, **params) -> dict:
    return client.get(SNAPSHOT, params={"tenant_id": LAW, **params}).json()


def test_tokenizer_drops_case_accents_punctuation_and_stop_words():
    assert tokenize("The Société's claim, art. 12!") == ["societe", "s", "claim", "art", "12"]


def test_empty_query_lists_the_whole_partition_newest_first(client):
    payload = search(client)

    assert payload["total"] == 10
    dates = [hit["ruling"]["decision_date"] for hit in payload["results"]]
    assert dates == sorted(dates, reverse=True)


def test_every_query_word_must_match(client):
    assert dockets(search(client, q="liquidated damages")) == [
        "SYN-LAW-2025-0004", "SYN-LAW-2024-0001"]
    assert search(client, q="liquidated zeppelin")["total"] == 0


def test_last_word_matches_as_a_prefix(client):
    assert dockets(search(client, q="redund")) == ["SYN-LAW-2024-0007"]
    assert search(client, q="re")["total"] == 0  # too short for a prefix


def test_docket_judge_and_cited_article_are_searchable(client):
    assert dockets(search(client, q="SYN-LAW-2024-0002")) == ["SYN-LAW-2024-0002"]
    assert search(client, q="Venthame")["total"] == 3
    assert search(client, q="LRS 58")["total"] == 2


def test_authority_and_outcome_filters_combine_with_the_text(client):
    board = search(client, authority="Halden Labour Review Board")
    upheld = search(client, authority="Halden Labour Review Board", outcome="UPHELD")
    both = search(client, q="dismissal", authority="Halden Labour Review Board", outcome="UPHELD")

    assert board["total"] == 4 and upheld["total"] == 2
    assert dockets(both) == ["SYN-LAW-2025-0009"]
    assert search(client, authority="No Such Authority")["total"] == 0


def test_hit_reports_matched_terms_score_and_a_snippet(client):
    hit = search(client, q="warranty fit")["results"][0]

    assert hit["matched_terms"] == ["fitness", "warranty"]
    assert "warranty of fitness" in hit["snippet"]
    assert hit["score"] > 0
    assert best_snippet("First one. Second one.", {"absent"}) == "First one."


@pytest.mark.parametrize(
    "params",
    [
        {"q": "x" * 121},
        {"authority": "x" * 81},
        {"outcome": "ACQUITTED"},
        {"tenant_id": "tnt-law-01"},
        {"tenant_id": "TNT-LAW-01; DROP"},
    ],
)
def test_overlong_or_malformed_input_is_rejected(client, params):
    assert client.get(SNAPSHOT, params={"tenant_id": LAW, **params}).status_code == 422


def test_tenant_is_a_required_parameter(client):
    for path in ("/search/snapshot", "/search/stream", "/export/analytics-xlsx",
                 "/analytics/estimate", "/ingest/state", "/ingest/stream"):
        assert client.get(f"{API}{path}").status_code == 422


def test_health_directory_and_schema(client):
    assert client.get(f"{API}/health").json() == {"status": "ok", "version": "0.1.0"}
    directory = client.get(f"{API}/tenants").json()
    assert [entry["tenant"]["tenant_id"] for entry in directory["tenants"]] == [
        "TNT-LAW-01", "TNT-IND-02"]
    assert directory["tenants"][0]["tenant"]["name"] == "Vanguard Corporate Litigation LLP"
    assert directory["tenants"][1]["tenant"]["name"] == "NorthSea Infrastructure Compliance"
    assert all(entry["corpus"]["rulings"] == 10 for entry in directory["tenants"])
    assert len(directory["outcomes"]) == 4 and len(directory["source_portals"]) == 4
    assert client.get(f"{API}/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 404  # would load assets from a CDN
