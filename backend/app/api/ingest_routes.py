"""Ingestion simulator: start a crawl, watch its stages, reset the corpus."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..config import API_PREFIX, Settings
from ..engine import LexStreamEngine
from ..models import TenantSnapshot
from ..partition import CrawlRefused
from ..sse import event_stream
from .schemas import CrawlAccepted, CrawlRequest, ResetResponse, TenantId
from .search_routes import SSE_HEADERS


def build_ingest_router(engine: LexStreamEngine, settings: Settings,
                        tasks: set[asyncio.Task[None]]) -> APIRouter:
    """The set holds the running crawls, so they stay alive and can be cancelled."""
    router = APIRouter(prefix="/ingest", tags=["ingest"])

    @router.post("/simulate-crawl", response_model=CrawlAccepted, status_code=202)
    async def simulate_crawl(request: CrawlRequest) -> CrawlAccepted:
        """Start a simulated crawl. Its stages arrive on ``GET /ingest/stream``.

        A browser ``EventSource`` can only issue GET, so the run is started here
        and observed there. No network request is made at any point.
        """
        try:
            run = engine.start_crawl(request.tenant_id, request.source_portal, request.rulings)
        except CrawlRefused as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        task = asyncio.create_task(
            engine.run_crawl(request.tenant_id, stage_delay=settings.crawl_stage_delay))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return CrawlAccepted(
            run_id=run.run_id,
            tenant_id=run.tenant_id,
            source_portal=run.source_portal,
            state=run.state,
            planned_rulings=run.planned_rulings,
            stream_url=f"{API_PREFIX}/ingest/stream?tenant_id={run.tenant_id}",
        )

    @router.post("/reset", response_model=ResetResponse)
    async def reset() -> ResetResponse:
        """Restore the default corpus of every tenant and notify connected clients."""
        for task in list(tasks):
            task.cancel()
        engine.reset()
        return ResetResponse(status="reset")

    @router.get("/state", response_model=TenantSnapshot)
    async def state(tenant_id: TenantId) -> TenantSnapshot:
        return engine.snapshot(tenant_id)

    @router.get("/stream")
    async def stream(
        tenant_id: TenantId,
        max_events: Annotated[int | None, Query(ge=1, le=10_000)] = None,
    ) -> StreamingResponse:
        """Server-Sent Events with full snapshots: crawl stages, new rulings, resets."""
        engine.partition(tenant_id)  # a 404 before the stream starts, not after
        return StreamingResponse(
            event_stream(engine, tenant_id, max_events=max_events),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    return router
