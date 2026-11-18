"""Progressive search over SSE: one ruling per event, then the analytics summary."""

from __future__ import annotations

import asyncio
import time

from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.index.filters import SearchFilters
from app.main import create_app
from app.search_service import result_stream

from .conftest import API, IND, LAW, dockets, sse_events

STREAM = f"{API}/search/stream"


def test_stream_sends_each_match_in_ranked_order_then_one_summary(client):
    params = {"tenant_id": LAW, "q": "costs"}
    expected = dockets(client.get(f"{API}/search/snapshot", params=params).json())

    response = client.get(STREAM, params=params)
    events = sse_events(response.text)

    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    assert [name for name, _ in events] == ["result"] * len(expected) + ["analytics_summary"]
    assert [data["hit"]["ruling"]["docket_id"] for _, data in events[:-1]] == expected
    assert [data["position"] for _, data in events[:-1]] == list(range(1, len(expected) + 1))
    assert all(data["total"] == len(expected) for _, data in events[:-1])


def test_summary_matches_the_snapshot_analytics(client):
    params = {"tenant_id": IND, "outcome": "COMPLIANCE_ORDER"}
    snapshot = client.get(f"{API}/search/snapshot", params=params).json()

    summary = sse_events(client.get(STREAM, params=params).text)[-1][1]

    assert summary["analytics"] == snapshot["analytics"]
    assert (summary["total"], summary["sent"], summary["truncated"]) == (4, 4, False)
    assert summary["tenant_id"] == IND and summary["elapsed_ms"] >= 0


def test_a_search_without_matches_still_ends_with_a_summary(client):
    events = sse_events(client.get(STREAM, params={"tenant_id": LAW, "q": "zeppelin"}).text)

    assert [name for name, _ in events] == ["analytics_summary"]
    assert events[0][1]["total"] == 0 and events[0][1]["analytics"]["rulings"] == 0


def test_event_ids_increase_so_a_client_can_tell_the_order(client):
    body = client.get(STREAM, params={"tenant_id": LAW}).text
    ids = [int(line[4:]) for line in body.splitlines() if line.startswith("id: ")]

    assert ids == list(range(1, 12))


def test_number_of_streamed_documents_is_capped(engine):
    settings = Settings(stream_delay=0.0, crawl_stage_delay=0.0, max_stream_events=3)
    with TestClient(create_app(engine, settings=settings)) as capped:
        events = sse_events(capped.get(STREAM, params={"tenant_id": LAW}).text)

    assert [name for name, _ in events] == ["result"] * 3 + ["analytics_summary"]
    summary = events[-1][1]
    assert (summary["total"], summary["sent"], summary["truncated"]) == (10, 3, True)
    assert summary["analytics"]["rulings"] == 10  # analytics still cover every match


def test_documents_are_spaced_by_the_configured_delay(engine):
    hits = engine.partition(LAW).search("", SearchFilters())[:3]

    async def collect():
        started = time.perf_counter()
        frames = [frame async for frame in result_stream(hits, LAW, delay=0.03, max_events=10)]
        return frames, time.perf_counter() - started

    frames, seconds = asyncio.run(collect())
    elapsed = [data["elapsed_ms"] for name, data in sse_events("".join(frames)) if name == "result"]

    # Three pauses of 30 ms. The bounds leave room for coarse timers (about 15 ms on
    # Windows) that may fire early; they still fail if the delay is not applied at all.
    assert seconds >= 0.06 and elapsed == sorted(elapsed) and elapsed[-1] >= 50


def test_delay_comes_from_the_environment_and_is_clamped(monkeypatch):
    for name in ("LEXSTREAM_STREAM_DELAY_MS", "LEXSTREAM_CRAWL_STAGE_DELAY_MS",
                 "LEXSTREAM_MAX_STREAM_EVENTS"):
        monkeypatch.delenv(name, raising=False)  # the developer's shell must not decide
    assert load_settings().stream_delay == 0.12
    monkeypatch.setenv("LEXSTREAM_STREAM_DELAY_MS", "0")
    monkeypatch.setenv("LEXSTREAM_CRAWL_STAGE_DELAY_MS", "nan")
    monkeypatch.setenv("LEXSTREAM_MAX_STREAM_EVENTS", "999999")

    settings = load_settings()

    assert settings.stream_delay == 0.0
    assert settings.crawl_stage_delay == 0.7
    assert settings.max_stream_events == 500
