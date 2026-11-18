"""Domain models shared by the corpus, the index, the partitions and the API."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class Outcome(str, Enum):
    UPHELD = "UPHELD"
    DISMISSED = "DISMISSED"
    SETTLED_WITH_COSTS = "SETTLED_WITH_COSTS"
    COMPLIANCE_ORDER = "COMPLIANCE_ORDER"


class Matter(str, Enum):
    COMMERCIAL = "COMMERCIAL"
    LABOUR = "LABOUR"
    INDUSTRIAL_SAFETY = "INDUSTRIAL_SAFETY"
    MACHINERY = "MACHINERY"


class RulingSource(str, Enum):
    DEFAULT_CORPUS = "DEFAULT_CORPUS"
    SIMULATED_CRAWL = "SIMULATED_CRAWL"


class CrawlStage(str, Enum):
    CONNECTING_PORTAL = "CONNECTING_PORTAL"
    PARSING_DOCKETS = "PARSING_DOCKETS"
    EXTRACTING_METADATA = "EXTRACTING_METADATA"
    INDEXED_NEW_RULING = "INDEXED_NEW_RULING"


class CrawlState(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SourcePortal(str, Enum):
    """Fictional portal names. A crawl never opens a network connection."""

    MERIDIAN_DOCKET_GAZETTE = "MERIDIAN_DOCKET_GAZETTE"
    HALDEN_TRIBUNAL_REGISTER = "HALDEN_TRIBUNAL_REGISTER"
    KESTREL_ENFORCEMENT_BULLETIN = "KESTREL_ENFORCEMENT_BULLETIN"
    ARVENMARK_CONFORMITY_LEDGER = "ARVENMARK_CONFORMITY_LEDGER"


class Tenant(BaseModel):
    tenant_id: str
    name: str
    focus: str


class Ruling(BaseModel):
    docket_id: str
    tenant_id: str
    title: str
    authority: str
    matter: Matter
    decision_date: date
    outcome: Outcome
    #: Whole pounds. Money stays an integer everywhere; it is never a float.
    financial_exposure_gbp: int
    cited_articles: list[str]
    judge_or_inspector: str
    summary_excerpt: str
    source: RulingSource = RulingSource.DEFAULT_CORPUS


class StageEvent(BaseModel):
    stage: CrawlStage
    at: datetime
    detail: str
    docket_id: str | None = None


class CrawlRun(BaseModel):
    run_id: str
    tenant_id: str
    source_portal: SourcePortal
    state: CrawlState
    started_at: datetime
    finished_at: datetime | None = None
    planned_rulings: int
    stages: list[StageEvent] = []


class CorpusStats(BaseModel):
    rulings: int
    default_rulings: int
    crawled_rulings: int
    total_exposure_gbp: int
    index_terms: int


class ActivityEvent(BaseModel):
    at: datetime
    kind: str
    message: str


class TenantSnapshot(BaseModel):
    """Live state of one tenant's partition. It never holds another tenant's data."""

    sequence: int
    generated_at: datetime
    tenant: Tenant
    corpus: CorpusStats
    authorities: list[str]
    matters: list[Matter]
    crawl: CrawlRun | None
    recent: list[Ruling]
    events: list[ActivityEvent]
