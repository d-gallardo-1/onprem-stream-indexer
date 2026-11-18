"""Fan-out of snapshots to the stream clients of one tenant at a time.

Subscribers are kept per tenant, so a snapshot can only be delivered to clients
that subscribed to the tenant it describes.
"""

from __future__ import annotations

import asyncio

from ..models import TenantSnapshot

#: Per-subscriber queue bound. Every message is a full snapshot, so dropping the
#: oldest one for a slow client loses nothing: the next snapshot supersedes it.
QUEUE_SIZE = 16

SnapshotQueue = asyncio.Queue[TenantSnapshot]


class Broadcaster:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[SnapshotQueue]] = {}

    def subscriber_count(self, tenant_id: str | None = None) -> int:
        if tenant_id is not None:
            return len(self._subscribers.get(tenant_id, ()))
        return sum(len(queues) for queues in self._subscribers.values())

    def subscribe(self, tenant_id: str) -> SnapshotQueue:
        queue: SnapshotQueue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subscribers.setdefault(tenant_id, set()).add(queue)
        return queue

    def unsubscribe(self, tenant_id: str, queue: SnapshotQueue) -> None:
        queues = self._subscribers.get(tenant_id)
        if queues is None:
            return
        queues.discard(queue)
        if not queues:
            del self._subscribers[tenant_id]

    def publish(self, snapshot: TenantSnapshot) -> None:
        for queue in self._subscribers.get(snapshot.tenant.tenant_id, ()):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(snapshot)
