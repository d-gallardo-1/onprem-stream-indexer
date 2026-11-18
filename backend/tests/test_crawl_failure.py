"""A crawl that fails must not block the tenant, and the state stream over HTTP."""

from __future__ import annotations

import asyncio

from app.models import CrawlState, SourcePortal
from app.partition import TenantPartition

from .conftest import API, IND, LAW, sse_events, start_crawl, wait_for_crawl

PORTAL = SourcePortal.MERIDIAN_DOCKET_GAZETTE


def break_indexing(monkeypatch) -> None:
    def explode(_self):
        raise RuntimeError("index is corrupt")

    monkeypatch.setattr(TenantPartition, "index_crawled", explode)


def test_a_crawl_that_raises_is_marked_failed_and_published(engine, monkeypatch):
    break_indexing(monkeypatch)
    engine.start_crawl(LAW, PORTAL, 2)
    queue = engine.subscribe(LAW)

    asyncio.run(engine.run_crawl(LAW, stage_delay=0))  # must not raise

    snapshot = engine.snapshot(LAW)
    assert snapshot.crawl.state == CrawlState.FAILED
    assert snapshot.crawl.finished_at is not None
    assert snapshot.events[0].kind == "CRAWL_FAILED"
    assert "RuntimeError" in snapshot.events[0].message
    assert snapshot.corpus.rulings == 10  # nothing half-indexed
    last = None
    while not queue.empty():
        last = queue.get_nowait()
    assert last.crawl.state == CrawlState.FAILED  # clients were told


def test_a_failed_crawl_does_not_block_the_next_one(client, engine, monkeypatch):
    break_indexing(monkeypatch)
    engine.start_crawl(LAW, PORTAL, 1)
    asyncio.run(engine.run_crawl(LAW, stage_delay=0))
    monkeypatch.undo()

    accepted = start_crawl(client, LAW)

    assert accepted.status_code == 202 and accepted.json()["run_id"] == "RUN-LAW-0002"
    assert wait_for_crawl(client, LAW)["corpus"]["crawled_rulings"] == 3


def test_a_failure_in_one_tenant_leaves_the_other_untouched(engine, monkeypatch):
    break_indexing(monkeypatch)
    engine.start_crawl(LAW, PORTAL, 1)

    asyncio.run(engine.run_crawl(LAW, stage_delay=0))

    assert engine.snapshot(IND).crawl is None and engine.snapshot(IND).events == []


def test_state_stream_over_http_sends_the_snapshot_with_sse_headers(client):
    url = f"{API}/ingest/stream"
    response = client.get(url, params={"tenant_id": IND, "max_events": 1})
    events = sse_events(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    assert response.text.splitlines()[0] == "retry: 3000"
    assert [name for name, _ in events] == ["snapshot"]
    assert events[0][1]["tenant"]["tenant_id"] == IND and events[0][1]["corpus"]["rulings"] == 10
    for bad in (0, 10_001):
        assert client.get(url, params={"tenant_id": IND, "max_events": bad}).status_code == 422
