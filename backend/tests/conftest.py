"""Shared fixtures. Stream and crawl delays are zero so tests are fast and ordered."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine import LexStreamEngine
from app.main import create_app

API = "/api/v1"
LAW = "TNT-LAW-01"  # docket IDs start with SYN-LAW-
IND = "TNT-IND-02"  # docket IDs start with SYN-IND-
PORTAL = "MERIDIAN_DOCKET_GAZETTE"
NO_DELAY = Settings(stream_delay=0.0, crawl_stage_delay=0.0, max_stream_events=100)


class Clock:
    """A clock that moves one second on every reading, so timestamps are ordered."""

    def __init__(self) -> None:
        self.now = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture()
def engine() -> LexStreamEngine:
    return LexStreamEngine(clock=Clock())


@pytest.fixture()
def client(engine: LexStreamEngine):
    with TestClient(create_app(engine, settings=NO_DELAY)) as test_client:
        yield test_client


def sse_events(body: str) -> list[tuple[str, dict]]:
    """Decode an SSE response body into ``(event name, data)`` pairs."""
    events = []
    for frame in body.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in frame.strip().splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def dockets(payload: dict) -> list[str]:
    return [hit["ruling"]["docket_id"] for hit in payload["results"]]


def start_crawl(client: TestClient, tenant_id: str = LAW, portal: str = PORTAL, **extra):
    body = {"tenant_id": tenant_id, "source_portal": portal, **extra}
    return client.post(f"{API}/ingest/simulate-crawl", json=body)


def wait_for_crawl(client: TestClient, tenant_id: str = LAW) -> dict:
    """Poll the tenant state until its crawl is completed; fail after two seconds."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        state = client.get(f"{API}/ingest/state", params={"tenant_id": tenant_id}).json()
        if state["crawl"] and state["crawl"]["state"] == "COMPLETED":
            return state
        time.sleep(0.01)
    raise AssertionError("the simulated crawl did not complete")
