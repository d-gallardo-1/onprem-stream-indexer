"""One tenant's partition: its rulings, its index, its crawl run and its activity log.

A partition holds no reference to any other tenant. It is reached only through
``TenantStore.partition`` (see ``tenancy.py``).
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Callable

from .data.corpus import crawled_ruling, default_rulings
from .data.tenants import TenantProfile
from .index.filters import SearchFilters
from .index.inverted import SearchHit, TenantIndex
from .models import (
    ActivityEvent,
    CorpusStats,
    CrawlRun,
    CrawlStage,
    CrawlState,
    Ruling,
    RulingSource,
    SourcePortal,
    StageEvent,
    TenantSnapshot,
)

RECENT_SIZE = 6
EVENT_LOG_SIZE = 12
#: Rulings simulated crawls may add to one tenant, so memory stays bounded.
MAX_CRAWLED = 60


class CrawlRefused(RuntimeError):
    """A crawl cannot start for this tenant right now. The message says why."""


class TenantPartition:
    def __init__(self, profile: TenantProfile, clock: Callable[[], datetime]) -> None:
        self.profile = profile
        self.index = TenantIndex()
        self.crawl: CrawlRun | None = None
        self._clock = clock
        self._crawled = 0
        self._runs = 0
        self._recent: deque[Ruling] = deque(maxlen=RECENT_SIZE)
        self._events: deque[ActivityEvent] = deque(maxlen=EVENT_LOG_SIZE)
        for ruling in default_rulings(profile):
            self.index.add(ruling)

    @property
    def tenant_id(self) -> str:
        return self.profile.tenant.tenant_id

    def rulings(self) -> list[Ruling]:
        return self.index.rulings()

    def search(self, query: str, filters: SearchFilters) -> list[SearchHit]:
        return self.index.search(query, filters)

    def log(self, kind: str, message: str) -> None:
        self._events.appendleft(ActivityEvent(at=self._clock(), kind=kind, message=message))

    # ---- simulated crawl ------------------------------------------------------

    def begin_crawl(self, portal: SourcePortal, planned_rulings: int) -> CrawlRun:
        if self.crawl is not None and self.crawl.state == CrawlState.RUNNING:
            raise CrawlRefused(f"Crawl {self.crawl.run_id} is still running for this tenant.")
        if self._crawled + planned_rulings > MAX_CRAWLED:
            raise CrawlRefused(
                f"This tenant already holds {self._crawled} crawled rulings (limit "
                f"{MAX_CRAWLED}). Reset the demo to start again."
            )
        self._runs += 1
        self.crawl = CrawlRun(
            run_id=f"RUN-{self.profile.code}-{self._runs:04d}",
            tenant_id=self.tenant_id,
            source_portal=portal,
            state=CrawlState.RUNNING,
            started_at=self._clock(),
            planned_rulings=planned_rulings,
        )
        self.record_stage(CrawlStage.CONNECTING_PORTAL,
                          f"Opening a simulated session with {portal.value}; no network is used.")
        self.log("CRAWL_STARTED", f"{self.crawl.run_id} started on {portal.value}")
        return self.crawl

    def record_stage(self, stage: CrawlStage, detail: str, docket_id: str | None = None) -> None:
        assert self.crawl is not None
        event = StageEvent(stage=stage, at=self._clock(), detail=detail, docket_id=docket_id)
        self.crawl = self.crawl.model_copy(update={"stages": [*self.crawl.stages, event]})

    def index_crawled(self) -> Ruling:
        """Add the next synthetic ruling of this tenant's crawl sequence to the index."""
        self._crawled += 1
        ruling = crawled_ruling(self.profile, self._crawled)
        self.index.add(ruling)
        self._recent.appendleft(ruling)
        self.record_stage(CrawlStage.INDEXED_NEW_RULING, ruling.title, ruling.docket_id)
        return ruling

    def finish_crawl(self) -> None:
        assert self.crawl is not None
        self.crawl = self.crawl.model_copy(
            update={"state": CrawlState.COMPLETED, "finished_at": self._clock()})
        self.log("CRAWL_COMPLETED",
                 f"{self.crawl.run_id} indexed {self.crawl.planned_rulings} new ruling(s)")

    # ---- snapshot -------------------------------------------------------------

    def snapshot(self, sequence: int) -> TenantSnapshot:
        rulings = self.rulings()
        crawled = sum(1 for r in rulings if r.source == RulingSource.SIMULATED_CRAWL)
        return TenantSnapshot(
            sequence=sequence,
            generated_at=self._clock(),
            tenant=self.profile.tenant,
            corpus=CorpusStats(
                rulings=len(rulings),
                default_rulings=len(rulings) - crawled,
                crawled_rulings=crawled,
                total_exposure_gbp=sum(r.financial_exposure_gbp for r in rulings),
                index_terms=self.index.term_count,
            ),
            authorities=sorted({ruling.authority for ruling in rulings}),
            matters=list(self.profile.authorities),
            crawl=self.crawl,
            recent=list(self._recent),
            events=list(self._events),
        )
