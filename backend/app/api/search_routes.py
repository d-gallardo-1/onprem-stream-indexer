"""Health, tenant directory, search (snapshot and progressive) and the estimator."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from .. import __version__, search_service
from ..analytics.estimator import estimate
from ..analytics.models import Estimate
from ..config import Settings
from ..data.tenants import MATTER_LABELS
from ..engine import LexStreamEngine
from ..models import Outcome, SourcePortal
from .schemas import (
    EstimateParams,
    HealthResponse,
    LabelledCode,
    SearchParams,
    SearchSnapshot,
    TenantEntry,
    TenantsResponse,
)

SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


def build_search_router(engine: LexStreamEngine, settings: Settings) -> APIRouter:
    router = APIRouter(tags=["search"])

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @router.get("/tenants", response_model=TenantsResponse)
    async def tenants() -> TenantsResponse:
        """Tenant directory with corpus counters. It holds no ruling."""
        return TenantsResponse(
            tenants=[
                TenantEntry(tenant=tenant, corpus=engine.snapshot(tenant.tenant_id).corpus)
                for tenant in engine.tenants
            ],
            outcomes=list(Outcome),
            matters=[LabelledCode(code=matter.value, label=label)
                     for matter, label in MATTER_LABELS.items()],
            source_portals=list(SourcePortal),
        )

    @router.get("/search/snapshot", response_model=SearchSnapshot)
    async def search_snapshot(params: Annotated[SearchParams, Depends()]) -> SearchSnapshot:
        return search_service.snapshot(engine, params)

    @router.get("/search/stream")
    async def search_stream(params: Annotated[SearchParams, Depends()]) -> StreamingResponse:
        """Server-Sent Events: one ``result`` per ruling, then ``analytics_summary``."""
        # Resolved before the response starts: an unknown tenant must be a 404,
        # not a stream that fails after its headers were sent.
        hits = search_service.find(engine, params)
        return StreamingResponse(
            search_service.result_stream(hits, params.tenant_id, delay=settings.stream_delay,
                                         max_events=settings.max_stream_events),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @router.get("/analytics/estimate", response_model=Estimate)
    async def analytics_estimate(params: Annotated[EstimateParams, Depends()]) -> Estimate:
        return estimate(
            engine.partition(params.tenant_id).rulings(),
            target=params.outcome,
            authority=params.authority,
            matter=params.matter,
        )

    return router
