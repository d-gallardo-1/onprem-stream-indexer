"""State stream: Server-Sent Events with full snapshots of one tenant's partition."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from .engine import LexStreamEngine
from .models import TenantSnapshot

#: Milliseconds the browser waits before reconnecting after a dropped stream.
RETRY_MS = 3000

#: Sent as a named event (not an SSE comment) so the browser can observe it and
#: detect a silently dead connection, for example behind a proxy that keeps the
#: client side open after the backend has gone away.
HEARTBEAT_FRAME = "event: heartbeat\ndata: {}\n\n"


def format_sse(event: str, snapshot: TenantSnapshot) -> str:
    return f"id: {snapshot.sequence}\nevent: {event}\ndata: {snapshot.model_dump_json()}\n\n"


async def event_stream(
    engine: LexStreamEngine,
    tenant_id: str,
    *,
    max_events: int | None = None,
    heartbeat_seconds: float = 5.0,
) -> AsyncIterator[str]:
    """Yield SSE frames for one client of ``tenant_id``.

    Order: reconnection hint, an immediate ``snapshot`` event with the current
    state, then one ``update`` event per published state. When nothing is
    published for ``heartbeat_seconds`` a ``heartbeat`` event is sent instead, so
    a client always receives something within that interval.
    """
    queue = engine.subscribe(tenant_id)
    try:
        yield f"retry: {RETRY_MS}\n\n"
        yield format_sse("snapshot", engine.snapshot(tenant_id))
        sent = 1
        while max_events is None or sent < max_events:
            try:
                snapshot = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
            except asyncio.TimeoutError:
                yield HEARTBEAT_FRAME
                continue
            yield format_sse("update", snapshot)
            sent += 1
    finally:
        engine.unsubscribe(tenant_id, queue)
