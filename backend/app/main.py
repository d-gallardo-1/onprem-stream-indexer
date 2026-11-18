"""FastAPI application (orchestrator): wires the engine and the routers.

Run with a single worker so the in-memory partitions are shared by every client::

    uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 1
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .api.export_routes import build_export_router
from .api.ingest_routes import build_ingest_router
from .api.search_routes import build_search_router
from .config import API_PREFIX, Settings, load_settings
from .engine import LexStreamEngine
from .tenancy import UnknownTenant


def create_app(engine: LexStreamEngine | None = None, *,
               settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    engine = engine or LexStreamEngine()
    crawl_tasks: set[asyncio.Task[None]] = set()

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            for task in list(crawl_tasks):
                task.cancel()
            await asyncio.gather(*crawl_tasks, return_exceptions=True)

    app = FastAPI(
        title="LexStream On-Prem API",
        version=__version__,
        description=(
            "Reference demo. Every ruling, authority, statute, portal, person and tenant is "
            "invented. The outcome estimate is illustrative and is not legal advice."
        ),
        lifespan=lifespan,
        # The interactive docs page loads its assets from a public CDN, which
        # would break the offline, on-premises promise. The schema stays available.
        docs_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json",
        redoc_url=None,
    )
    app.state.engine = engine

    @app.exception_handler(UnknownTenant)
    async def unknown_tenant(_: Request, __: UnknownTenant) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Unknown tenant."})

    # Every route is static: there is no path parameter that could shadow one.
    app.include_router(build_search_router(engine, settings), prefix=API_PREFIX)
    app.include_router(build_ingest_router(engine, settings, crawl_tasks), prefix=API_PREFIX)
    app.include_router(build_export_router(engine), prefix=API_PREFIX)
    return app


app = create_app()
