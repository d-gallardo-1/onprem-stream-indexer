"""Tenant partitioning: no endpoint, stream or export returns the other tenant's records.

This is data partitioning, not access control: the caller names the tenant.
"""

from __future__ import annotations

import inspect
import io
import json

import pytest
from openpyxl import load_workbook

from app import engine as engine_module
from app.tenancy import TenantStore, UnknownTenant

from .conftest import API, IND, LAW, dockets, sse_events, start_crawl, wait_for_crawl

OTHER = {LAW: ("SYN-IND-", "NorthSea", "Inspectorate", "ISC reg", "MCR r."),
         IND: ("SYN-LAW-", "Vanguard", "Halden", "COC art", "LRS s.")}
TENANT_GETS = ("/search/snapshot", "/search/stream", "/export/analytics-xlsx",
               "/analytics/estimate", "/ingest/state", "/ingest/stream")


def assert_only(tenant_id: str, text: str) -> None:
    for foreign in OTHER[tenant_id]:
        assert foreign not in text, f"{foreign!r} leaked into a {tenant_id} response"


@pytest.mark.parametrize("tenant_id", [LAW, IND])
def test_snapshot_search_returns_only_the_named_tenant(client, tenant_id):
    payload = client.get(f"{API}/search/snapshot", params={"tenant_id": tenant_id}).json()

    assert payload["total"] == 10
    assert {hit["ruling"]["tenant_id"] for hit in payload["results"]} == {tenant_id}
    assert_only(tenant_id, json.dumps(payload))


@pytest.mark.parametrize("tenant_id", [LAW, IND])
def test_search_stream_returns_only_the_named_tenant(client, tenant_id):
    body = client.get(f"{API}/search/stream", params={"tenant_id": tenant_id}).text
    events = sse_events(body)

    assert len(events) == 11 and events[-1][1]["tenant_id"] == tenant_id
    assert {data["hit"]["ruling"]["tenant_id"] for _, data in events[:-1]} == {tenant_id}
    assert_only(tenant_id, body)


@pytest.mark.parametrize("tenant_id", [LAW, IND])
def test_export_holds_only_the_named_tenant(client, tenant_id):
    response = client.get(f"{API}/export/analytics-xlsx", params={"tenant_id": tenant_id})
    workbook = load_workbook(io.BytesIO(response.content))
    cells = [str(cell) for sheet in workbook for row in sheet.iter_rows(values_only=True)
             for cell in row if cell is not None]

    assert tenant_id in workbook["Results"]["A1"].value
    assert_only(tenant_id, "\n".join(cells))


@pytest.mark.parametrize("tenant_id", [LAW, IND])
def test_state_and_estimate_mention_only_the_named_tenant(client, tenant_id):
    params = {"tenant_id": tenant_id}
    state = client.get(f"{API}/ingest/state", params=params).text
    estimate = client.get(f"{API}/analytics/estimate", params=params).json()

    assert_only(tenant_id, state)
    assert estimate["factors"][0]["rulings"] == 10


def test_a_term_of_the_other_tenant_finds_nothing(client):
    def total(tenant_id: str, q: str) -> int:
        params = {"tenant_id": tenant_id, "q": q}
        return client.get(f"{API}/search/snapshot", params=params).json()["total"]

    assert total(IND, "crane") == 2 and total(LAW, "crane") == 0
    assert total(LAW, "redundancy") == 1 and total(IND, "redundancy") == 0
    assert total(LAW, "SYN-IND-2024-0001") == 0


def test_another_tenants_authority_filter_matches_nothing(client):
    params = {"tenant_id": LAW, "authority": "Kestrel Industrial Safety Inspectorate"}

    assert client.get(f"{API}/search/snapshot", params=params).json()["total"] == 0


@pytest.mark.parametrize("path", TENANT_GETS)
def test_unknown_tenant_is_a_404_on_every_tenant_route(client, path):
    response = client.get(f"{API}{path}", params={"tenant_id": "TNT-XXX-09"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown tenant."}


def test_a_crawl_only_changes_the_tenant_it_was_started_for(client, engine):
    assert start_crawl(client, LAW).status_code == 202
    wait_for_crawl(client, LAW)

    law = client.get(f"{API}/search/snapshot", params={"tenant_id": LAW}).json()
    ind = client.get(f"{API}/search/snapshot", params={"tenant_id": IND}).json()
    assert law["total"] == 13 and ind["total"] == 10
    assert all(docket.startswith("SYN-LAW-") for docket in dockets(law))
    assert engine.snapshot(IND).crawl is None and engine.snapshot(IND).events == []


def test_state_stream_subscriber_receives_only_its_own_tenant(client, engine):
    law_queue, ind_queue = engine.subscribe(LAW), engine.subscribe(IND)

    start_crawl(client, IND, "KESTREL_ENFORCEMENT_BULLETIN")
    wait_for_crawl(client, IND)

    assert law_queue.empty()
    received = []
    while not ind_queue.empty():
        received.append(ind_queue.get_nowait())
    assert received and {snapshot.tenant.tenant_id for snapshot in received} == {IND}


def test_directory_lists_counters_but_no_ruling(client):
    text = client.get(f"{API}/tenants").text

    assert "TNT-LAW-01" in text and "TNT-IND-02" in text
    assert "SYN-" not in text


def test_the_store_is_the_only_holder_of_partitions(engine):
    """Scoping lives in one layer: the engine reaches tenant data only through it."""
    source = inspect.getsource(engine_module)

    assert "_partitions" not in source
    assert source.count("self._store.partition(") == 1  # the single entry point
    with pytest.raises(UnknownTenant):
        engine.partition("TNT-XXX-09")
    assert [name for name in vars(TenantStore) if "partition" in name] == ["partition"]
