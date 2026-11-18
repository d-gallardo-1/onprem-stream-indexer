"""A crawl that fails must not block the tenant, and the state stream over HTTP."""

from __future__ import annotations

import asyncio
import logging

from app.models import CrawlState, RulingSource, SourcePortal
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


def test_a_failed_crawl_leaves_a_traceback_in_the_server_log(engine, monkeypatch, caplog):
    break_indexing(monkeypatch)
    engine.start_crawl(LAW, PORTAL, 1)

    with caplog.at_level(logging.ERROR, logger="app.engine"):
        asyncio.run(engine.run_crawl(LAW, stage_delay=0))

    record = caplog.records[-1]
    assert "RUN-LAW-0001" in record.getMessage() and LAW in record.getMessage()
    assert record.exc_info is not None and record.exc_info[0] is RuntimeError


def test_a_failure_midway_keeps_the_rulings_already_indexed(engine, monkeypatch):
    original = TenantPartition.index_crawled
    calls = {"count": 0}

    def fail_on_second(self):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("second ruling is malformed")
        return original(self)

    monkeypatch.setattr(TenantPartition, "index_crawled", fail_on_second)
    engine.start_crawl(LAW, PORTAL, 3)

    asyncio.run(engine.run_crawl(LAW, stage_delay=0))

    snapshot = engine.snapshot(LAW)
    assert snapshot.crawl.state == CrawlState.FAILED
    assert snapshot.corpus.crawled_rulings == 1  # a valid ruling is not thrown away
    assert [r.source for r in snapshot.recent] == [RulingSource.SIMULATED_CRAWL]


def test_an_error_after_completion_does_not_relabel_the_run_as_failed(engine, monkeypatch):
    engine.start_crawl(LAW, PORTAL, 1)
    publish = engine.publish

    def fail_once_completed(tenant_id):
        if engine.partition(tenant_id).crawl.state == CrawlState.COMPLETED:
            raise RuntimeError("a subscriber queue broke")
        publish(tenant_id)

    monkeypatch.setattr(engine, "publish", fail_once_completed)

    asyncio.run(engine.run_crawl(LAW, stage_delay=0))

    assert engine.snapshot(LAW).crawl.state == CrawlState.COMPLETED
