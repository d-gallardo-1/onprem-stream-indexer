"""Runs one search inside one tenant's partition: snapshot form and progressive form."""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

from .analytics.summary import summarise
from .api.schemas import (
    SearchHitOut,
    SearchParams,
    SearchSnapshot,
    StreamedResult,
    StreamSummary,
)
from .engine import LexStreamEngine
from .index.inverted import SearchHit

#: Most rulings a snapshot search or an export returns.
MAX_RESULTS = 200


def find(engine: LexStreamEngine, params: SearchParams) -> list[SearchHit]:
    """Every matching ruling of the tenant named in the request, best first."""
    return engine.partition(params.tenant_id).search(params.query, params.filters)


def _hit(hit: SearchHit) -> SearchHitOut:
    return SearchHitOut(ruling=hit.ruling, score=hit.score,
                        matched_terms=list(hit.matched_terms), snippet=hit.snippet)


def snapshot(engine: LexStreamEngine, params: SearchParams) -> SearchSnapshot:
    hits = find(engine, params)
    return SearchSnapshot(
        tenant_id=params.tenant_id,
        query=params.query,
        authority=params.filters.authority,
        outcome=params.filters.outcome,
        total=len(hits),
        results=[_hit(hit) for hit in hits[:MAX_RESULTS]],
        # Analytics always cover every match, not only the rows returned.
        analytics=summarise(hit.ruling for hit in hits),
    )


def _frame(event: str, sequence: int, payload: str) -> str:
    return f"id: {sequence}\nevent: {event}\ndata: {payload}\n\n"


async def result_stream(hits: list[SearchHit], tenant_id: str, *, delay: float,
                        max_events: int) -> AsyncIterator[str]:
    """Yield one ``result`` event per ruling, then a final ``analytics_summary``.

    The matches were resolved before the stream started, so every event belongs
    to the same tenant and the same moment of the index.
    """
    started = time.perf_counter()

    def elapsed_ms() -> int:
        return int((time.perf_counter() - started) * 1000)

    sending = hits[:max_events]
    for position, hit in enumerate(sending, start=1):
        if delay:
            await asyncio.sleep(delay)
        event = StreamedResult(position=position, total=len(hits), elapsed_ms=elapsed_ms(),
                               hit=_hit(hit))
        yield _frame("result", position, event.model_dump_json())
    summary = StreamSummary(
        tenant_id=tenant_id,
        total=len(hits),
        sent=len(sending),
        truncated=len(hits) > len(sending),
        elapsed_ms=elapsed_ms(),
        analytics=summarise(hit.ruling for hit in hits),
    )
    yield _frame("analytics_summary", len(sending) + 1, summary.model_dump_json())
