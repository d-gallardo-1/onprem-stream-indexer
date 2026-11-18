"""Simulated crawl: acceptance, stages, refusals, reset and the state stream."""

from __future__ import annotations

import asyncio
import socket

import pytest

from app import partition as partition_module
from app.models import SourcePortal
from app.sse import event_stream

from .conftest import API, IND, LAW, PORTAL, start_crawl, wait_for_crawl

STAGES = ["CONNECTING_PORTAL", "PARSING_DOCKETS", "EXTRACTING_METADATA"]


def test_crawl_is_accepted_with_a_run_id_and_the_stream_to_watch(client):
    response = start_crawl(client, LAW)

    assert response.status_code == 202
    assert response.json() == {
        "run_id": "RUN-LAW-0001",
        "tenant_id": LAW,
        "source_portal": PORTAL,
        "state": "RUNNING",
        "planned_rulings": 3,
        "stream_url": "/api/v1/ingest/stream?tenant_id=TNT-LAW-01",
    }


def test_stages_arrive_in_order_and_each_new_ruling_is_indexed(client):
    start_crawl(client, LAW, rulings=2)
    state = wait_for_crawl(client, LAW)
    stages = state["crawl"]["stages"]

    assert [stage["stage"] for stage in stages] == [*STAGES, "INDEXED_NEW_RULING",
                                                     "INDEXED_NEW_RULING"]
    assert [stage["docket_id"] for stage in stages[3:]] == ["SYN-LAW-CRAWL-0001",
                                                           "SYN-LAW-CRAWL-0002"]
    assert [stage["at"] for stage in stages] == sorted(stage["at"] for stage in stages)
    assert state["corpus"] == {**state["corpus"], "rulings": 12, "crawled_rulings": 2}
    assert [ruling["docket_id"] for ruling in state["recent"]] == ["SYN-LAW-CRAWL-0002",
                                                                  "SYN-LAW-CRAWL-0001"]
    found = client.get(f"{API}/search/snapshot",
                       params={"tenant_id": LAW, "q": "SYN-LAW-CRAWL-0002"}).json()
    assert found["total"] == 1 and found["results"][0]["ruling"]["source"] == "SIMULATED_CRAWL"


def test_second_crawl_for_a_tenant_with_one_running_is_a_409(client, engine):
    engine.start_crawl(LAW, SourcePortal.MERIDIAN_DOCKET_GAZETTE, 3)  # registered, not played

    refused = start_crawl(client, LAW)

    assert refused.status_code == 409
    assert "RUN-LAW-0001 is still running" in refused.json()["detail"]
    assert start_crawl(client, IND).status_code == 202  # the other tenant is not blocked


def test_a_finished_crawl_allows_the_next_one(client):
    start_crawl(client, LAW)
    wait_for_crawl(client, LAW)

    assert start_crawl(client, LAW).json()["run_id"] == "RUN-LAW-0002"
    assert wait_for_crawl(client, LAW)["corpus"]["crawled_rulings"] == 6


@pytest.mark.parametrize(
    "body",
    [
        {"tenant_id": LAW, "source_portal": "https://example.org/dockets"},
        {"tenant_id": LAW, "source_portal": "REAL_COURT_PORTAL"},
        {"tenant_id": LAW, "source_portal": ""},
        {"tenant_id": LAW},
        {"tenant_id": LAW, "source_portal": PORTAL, "rulings": 6},
        {"tenant_id": LAW, "source_portal": PORTAL, "rulings": 0},
        {"tenant_id": LAW, "source_portal": PORTAL, "url": "https://example.org"},
        {"tenant_id": "law", "source_portal": PORTAL},
    ],
)
def test_invalid_crawl_request_is_rejected_and_starts_nothing(client, engine, body):
    assert client.post(f"{API}/ingest/simulate-crawl", json=body).status_code == 422
    assert engine.snapshot(LAW).crawl is None


def test_crawl_for_an_unknown_tenant_is_a_404(client):
    assert start_crawl(client, "TNT-XXX-09").status_code == 404


def test_a_crawl_opens_no_network_connection(client, monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("the simulated crawl tried to open a socket")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)

    start_crawl(client, IND, "ARVENMARK_CONFORMITY_LEDGER")

    assert wait_for_crawl(client, IND)["corpus"]["crawled_rulings"] == 3


def test_crawled_rulings_are_capped_per_tenant(client, monkeypatch):
    monkeypatch.setattr(partition_module, "MAX_CRAWLED", 4)
    start_crawl(client, LAW)
    wait_for_crawl(client, LAW)

    refused = start_crawl(client, LAW)

    assert refused.status_code == 409 and "limit 4" in refused.json()["detail"]


def test_reset_restores_the_default_corpus_and_notifies_clients(client, engine):
    start_crawl(client, LAW)
    wait_for_crawl(client, LAW)
    law_queue, ind_queue = engine.subscribe(LAW), engine.subscribe(IND)
    before = engine.snapshot(LAW).sequence

    assert client.post(f"{API}/ingest/reset").json() == {"status": "reset"}

    for queue, tenant_id in ((law_queue, LAW), (ind_queue, IND)):
        snapshot = queue.get_nowait()
        assert snapshot.tenant.tenant_id == tenant_id
        assert snapshot.corpus.rulings == 10 and snapshot.corpus.crawled_rulings == 0
        assert snapshot.crawl is None and snapshot.events[0].kind == "RESET"
        assert queue.empty()
    assert engine.snapshot(LAW).sequence == before + 1  # sequences keep increasing
    assert start_crawl(client, LAW).json()["run_id"] == "RUN-LAW-0001"


def test_reset_stops_a_running_crawl_from_touching_the_new_corpus(engine):
    async def scenario():
        engine.start_crawl(LAW, SourcePortal.MERIDIAN_DOCKET_GAZETTE, 3)
        crawl = asyncio.create_task(engine.run_crawl(LAW, stage_delay=0.01))
        await asyncio.sleep(0)
        engine.reset()
        await crawl

    asyncio.run(scenario())

    assert engine.snapshot(LAW).corpus.rulings == 10 and engine.snapshot(LAW).crawl is None


def test_state_stream_delivers_one_full_snapshot_per_stage(engine):
    async def scenario():
        frames = []
        stream = event_stream(engine, LAW, max_events=7, heartbeat_seconds=0.05)
        async for frame in stream:
            frames.append(frame)
            if len(frames) == 2:  # retry hint + initial snapshot delivered
                engine.start_crawl(LAW, SourcePortal.HALDEN_TRIBUNAL_REGISTER, 2)
                await engine.run_crawl(LAW, stage_delay=0)
        return frames

    frames = asyncio.run(scenario())
    events = [frame for frame in frames if frame.startswith("id:")]

    assert frames[0] == "retry: 3000\n\n"
    assert [frame.splitlines()[1] for frame in events] == ["event: snapshot"] + ["event: update"] * 6
    assert '"state":"COMPLETED"' in events[-1] and '"rulings":12' in events[-1]
    assert engine.subscriber_count() == 0


def test_state_stream_heartbeats_and_slow_clients_keep_the_latest(engine):
    async def heartbeat():
        stream = event_stream(engine, IND, heartbeat_seconds=0.02)
        frames = [await anext(stream) for _ in range(3)]
        await stream.aclose()
        return frames[2]

    assert asyncio.run(heartbeat()) == "event: heartbeat\ndata: {}\n\n"
    queue = engine.subscribe(IND)
    for _ in range(50):
        engine.publish(IND)
    assert queue.full()
    last = None
    while not queue.empty():
        last = queue.get_nowait()
    assert last.sequence == 50
