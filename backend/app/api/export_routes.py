"""Excel report of the current tenant query."""

from __future__ import annotations

from typing import Annotated

import anyio
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import search_service
from ..analytics.summary import summarise
from ..engine import LexStreamEngine
from ..workbook.exporter import report_bytes
from .schemas import XLSX_MEDIA_TYPE, SearchParams


def build_export_router(engine: LexStreamEngine) -> APIRouter:
    router = APIRouter(prefix="/export", tags=["export"])

    @router.get("/analytics-xlsx")
    async def analytics_xlsx(params: Annotated[SearchParams, Depends()]) -> Response:
        partition = engine.partition(params.tenant_id)
        hits = search_service.find(engine, params)
        analytics = summarise(hit.ruling for hit in hits)
        rulings = [hit.ruling for hit in hits[: search_service.MAX_RESULTS]]
        # Building the workbook is CPU work: keep it off the event loop.
        payload = await anyio.to_thread.run_sync(
            report_bytes, partition.profile.tenant, params.describe(), rulings, analytics
        )
        filename = f"lexstream_report_{params.tenant_id}.xlsx"
        return Response(
            content=payload,
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router
