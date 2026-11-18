"""LexStreamEngine (orchestrator): tenant store, simulated crawls and live snapshots.

All state lives in this process. Every method that touches tenant data takes
the tenant ID and resolves it through ``TenantStore.partition`` first.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable

from .models import CrawlRun, CrawlStage, SourcePortal, Tenant, TenantSnapshot
from .partition import TenantPartition
from .streaming.broadcaster import Broadcaster, SnapshotQueue
from .tenancy import TenantStore


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LexStreamEngine:
    def __init__(self, *, clock: Callable[[], datetime] = _utc_now) -> None:
        self._store = TenantStore(clock=clock)
        self._broadcaster = Broadcaster()
        self._sequences = {tenant.tenant_id: 0 for tenant in self._store.tenants}
        #: Changes on reset, so a crawl that was running stops touching the new corpus.
        self._generation = 0

    # ---- tenant scoping -----------------------------------------------------

    @property
    def tenants(self) -> list[Tenant]:
        return self._store.tenants

    def partition(self, tenant_id: str) -> TenantPartition:
        """The one entry point to tenant data; raises ``UnknownTenant``."""
        return self._store.partition(tenant_id)

    # ---- snapshots and state stream -----------------------------------------

    def snapshot(self, tenant_id: str) -> TenantSnapshot:
        return self.partition(tenant_id).snapshot(self._sequences[tenant_id])

    def publish(self, tenant_id: str) -> None:
        """Send a fresh snapshot to the state-stream clients of one tenant."""
        partition = self.partition(tenant_id)
        self._sequences[tenant_id] += 1
        self._broadcaster.publish(partition.snapshot(self._sequences[tenant_id]))

    def subscribe(self, tenant_id: str) -> SnapshotQueue:
        return self._broadcaster.subscribe(self.partition(tenant_id).tenant_id)

    def unsubscribe(self, tenant_id: str, queue: SnapshotQueue) -> None:
        self._broadcaster.unsubscribe(tenant_id, queue)

    def subscriber_count(self, tenant_id: str | None = None) -> int:
        return self._broadcaster.subscriber_count(tenant_id)

    # ---- simulated crawl ----------------------------------------------------

    def start_crawl(self, tenant_id: str, portal: SourcePortal, rulings: int) -> CrawlRun:
        """Register a run and publish its first stage; raises ``CrawlRefused``."""
        run = self.partition(tenant_id).begin_crawl(portal, rulings)
        self.publish(tenant_id)
        return run

    async def run_crawl(self, tenant_id: str, *, stage_delay: float) -> None:
        """Play the remaining stages of the tenant's running crawl.

        Nothing is fetched: the "found" rulings come from the tenant's own
        deterministic sequence of synthetic rulings.
        """
        partition = self.partition(tenant_id)
        run = partition.crawl
        generation = self._generation
        if run is None:
            return

        async def advance() -> bool:
            await asyncio.sleep(stage_delay)
            return generation == self._generation  # False once the demo was reset

        if not await advance():
            return
        partition.record_stage(CrawlStage.PARSING_DOCKETS,
                               f"Listing new dockets: {run.planned_rulings} found.")
        self.publish(tenant_id)
        if not await advance():
            return
        partition.record_stage(CrawlStage.EXTRACTING_METADATA,
                               "Reading authority, outcome, exposure and cited articles.")
        self.publish(tenant_id)
        for _ in range(run.planned_rulings):
            if not await advance():
                return
            partition.index_crawled()
            self.publish(tenant_id)
        partition.finish_crawl()
        self.publish(tenant_id)

    def reset(self) -> None:
        """Restore the default corpus of every tenant and tell connected clients."""
        self._generation += 1
        self._store.reset()
        for tenant in self._store.tenants:
            self.partition(tenant.tenant_id).log("RESET", "Default corpus restored.")
            self.publish(tenant.tenant_id)
