"""Request parameters and response shapes of the HTTP API."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from ..analytics.models import Analytics
from ..index.filters import SearchFilters
from ..models import CorpusStats, CrawlState, Matter, Outcome, Ruling, SourcePortal, Tenant

TENANT_PATTERN = r"^TNT-[A-Z]{3}-\d{2}$"
MAX_QUERY_CHARS = 120
MAX_AUTHORITY_CHARS = 80
#: The tenant is a required parameter of every tenant-scoped request.
TenantId = Annotated[str, Query(pattern=TENANT_PATTERN)]

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class HealthResponse(BaseModel):
    status: str
    version: str


class LabelledCode(BaseModel):
    code: str
    label: str


class TenantEntry(BaseModel):
    tenant: Tenant
    corpus: CorpusStats


class TenantsResponse(BaseModel):
    tenants: list[TenantEntry]
    outcomes: list[Outcome]
    matters: list[LabelledCode]
    source_portals: list[SourcePortal]


class SearchHitOut(BaseModel):
    ruling: Ruling
    score: float
    matched_terms: list[str]
    snippet: str


class SearchSnapshot(BaseModel):
    tenant_id: str
    query: str
    authority: str | None
    outcome: Outcome | None
    total: int
    results: list[SearchHitOut]
    analytics: Analytics


class StreamedResult(BaseModel):
    position: int
    total: int
    elapsed_ms: int
    hit: SearchHitOut


class StreamSummary(BaseModel):
    tenant_id: str
    total: int
    sent: int
    #: True when the match count exceeded the cap on streamed documents.
    truncated: bool
    elapsed_ms: int
    analytics: Analytics


class CrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(pattern=TENANT_PATTERN)
    #: One of the fictional portals. Never a URL: the backend makes no network request.
    source_portal: SourcePortal
    rulings: int = Field(default=3, ge=1, le=5)


class CrawlAccepted(BaseModel):
    run_id: str
    tenant_id: str
    source_portal: SourcePortal
    state: CrawlState
    planned_rulings: int
    #: Where the stages of this run are delivered (Server-Sent Events).
    stream_url: str


class ResetResponse(BaseModel):
    status: str


class SearchParams:
    """Query-string parameters shared by snapshot search, stream search and the export."""

    def __init__(
        self,
        tenant_id: TenantId,
        q: Annotated[str, Query(max_length=MAX_QUERY_CHARS)] = "",
        authority: Annotated[str | None, Query(max_length=MAX_AUTHORITY_CHARS)] = None,
        outcome: Outcome | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.query = q
        self.filters = SearchFilters(authority=authority or None, outcome=outcome)

    def describe(self) -> str:
        parts = [f"Query: {self.query or '(all rulings)'}"]
        if self.filters.authority:
            parts.append(f"Authority: {self.filters.authority}")
        if self.filters.outcome:
            parts.append(f"Outcome: {self.filters.outcome.value}")
        return " | ".join(parts)


class EstimateParams:
    def __init__(
        self,
        tenant_id: TenantId,
        outcome: Outcome = Outcome.UPHELD,
        authority: Annotated[str | None, Query(max_length=MAX_AUTHORITY_CHARS)] = None,
        matter: Matter | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.outcome = outcome
        self.authority = authority or None
        self.matter = matter
