// Shapes of the backend API. They mirror backend/app/models.py and api/schemas.py.

export type StreamStatus = 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';
export type ViewId = 'search' | 'ingest' | 'partition';
export type Outcome = 'UPHELD' | 'DISMISSED' | 'SETTLED_WITH_COSTS' | 'COMPLIANCE_ORDER';
export type CrawlStage =
  | 'CONNECTING_PORTAL'
  | 'PARSING_DOCKETS'
  | 'EXTRACTING_METADATA'
  | 'INDEXED_NEW_RULING';

export interface Tenant {
  tenant_id: string;
  name: string;
  focus: string;
}

export interface CorpusStats {
  rulings: number;
  default_rulings: number;
  crawled_rulings: number;
  total_exposure_gbp: number;
  index_terms: number;
}

export interface LabelledCode {
  code: string;
  label: string;
}

export interface Directory {
  tenants: { tenant: Tenant; corpus: CorpusStats }[];
  outcomes: Outcome[];
  matters: LabelledCode[];
  source_portals: string[];
}

export interface Ruling {
  docket_id: string;
  tenant_id: string;
  title: string;
  authority: string;
  matter: string;
  decision_date: string;
  outcome: Outcome;
  financial_exposure_gbp: number;
  cited_articles: string[];
  judge_or_inspector: string;
  summary_excerpt: string;
  source: 'DEFAULT_CORPUS' | 'SIMULATED_CRAWL';
}

export interface SearchHit {
  ruling: Ruling;
  score: number;
  matched_terms: string[];
  snippet: string;
}

export interface AuthorityTrend {
  authority: string;
  rulings: number;
  upheld_or_ordered: number;
  percent: number;
  direction: 'RISING' | 'FALLING' | 'STEADY' | 'SINGLE_YEAR';
  by_year: { year: number; rulings: number; upheld_or_ordered: number; percent: number }[];
}

export interface Analytics {
  disclaimer: string;
  rulings: number;
  outcome_distribution: { outcome: Outcome; count: number; percent: number }[];
  /** `median_gbp` is an exact decimal sent as text, for example "111750.00". */
  exposure: { total_gbp: number; median_gbp: string; highest_gbp: number };
  top_clauses: { article: string; count: number }[];
  authority_trend: AuthorityTrend[];
}

/** Text query plus filters; an empty string means "no filter". */
export interface SearchQuery {
  q: string;
  authority: string;
  outcome: string;
}

export interface SearchSnapshot {
  tenant_id: string;
  query: string;
  total: number;
  results: SearchHit[];
  analytics: Analytics;
}

export interface StreamedResult {
  position: number;
  total: number;
  elapsed_ms: number;
  hit: SearchHit;
}

export interface StreamSummary {
  tenant_id: string;
  total: number;
  sent: number;
  truncated: boolean;
  elapsed_ms: number;
  analytics: Analytics;
}

export interface EstimateInput {
  authority: string;
  matter: string;
  outcome: Outcome;
}

export interface Estimate {
  disclaimer: string;
  method: string;
  target_outcome: Outcome;
  sample_size: number;
  confidence: 'LOW' | 'MODERATE' | 'HIGHER';
  estimated_percent: number;
  factors: { label: string; matching: number; rulings: number; percent: number }[];
}

export interface StageEvent {
  stage: CrawlStage;
  at: string;
  detail: string;
  docket_id: string | null;
}

export interface CrawlRun {
  run_id: string;
  tenant_id: string;
  source_portal: string;
  state: 'RUNNING' | 'COMPLETED';
  started_at: string;
  finished_at: string | null;
  planned_rulings: number;
  stages: StageEvent[];
}

export interface TenantSnapshot {
  sequence: number;
  generated_at: string;
  tenant: Tenant;
  corpus: CorpusStats;
  authorities: string[];
  matters: string[];
  crawl: CrawlRun | null;
  recent: Ruling[];
  events: { at: string; kind: string; message: string }[];
}
