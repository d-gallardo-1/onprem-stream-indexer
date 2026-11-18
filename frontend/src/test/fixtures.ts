import type {
  Analytics,
  CrawlRun,
  Directory,
  Estimate,
  Ruling,
  SearchHit,
  SearchSnapshot,
  StreamSummary,
  Tenant,
  TenantSnapshot,
} from '../types/lexstream';

export const LAW: Tenant = {
  tenant_id: 'TNT-LAW-01',
  name: 'Vanguard Corporate Litigation LLP',
  focus: 'Commercial and labour rulings',
};
export const IND: Tenant = {
  tenant_id: 'TNT-IND-02',
  name: 'NorthSea Infrastructure Compliance',
  focus: 'Industrial safety and machinery enforcement',
};

const corpus = (rulings = 10) => ({
  rulings,
  default_rulings: 10,
  crawled_rulings: rulings - 10,
  total_exposure_gbp: 1_938_300,
  index_terms: 188,
});

export const DIRECTORY: Directory = {
  tenants: [
    { tenant: LAW, corpus: corpus() },
    { tenant: IND, corpus: corpus() },
  ],
  outcomes: ['UPHELD', 'DISMISSED', 'SETTLED_WITH_COSTS', 'COMPLIANCE_ORDER'],
  matters: [
    { code: 'COMMERCIAL', label: 'Commercial' },
    { code: 'LABOUR', label: 'Labour' },
    { code: 'INDUSTRIAL_SAFETY', label: 'Industrial safety' },
    { code: 'MACHINERY', label: 'Machinery' },
  ],
  source_portals: ['MERIDIAN_DOCKET_GAZETTE', 'HALDEN_TRIBUNAL_REGISTER'],
};

export function makeRuling(changes: Partial<Ruling> = {}): Ruling {
  return {
    docket_id: 'SYN-LAW-2024-0001',
    tenant_id: LAW.tenant_id,
    title: 'Corvane Freight v Lumestra Packaging',
    authority: 'Meridian Commercial Disputes Bench',
    matter: 'COMMERCIAL',
    decision_date: '2024-03-12',
    outcome: 'UPHELD',
    financial_exposure_gbp: 412_000,
    cited_articles: ['COC art. 14', 'COC art. 31'],
    judge_or_inspector: 'Judge Orla Venthame',
    summary_excerpt: 'Late delivery triggered the liquidated damages clause.',
    source: 'DEFAULT_CORPUS',
    ...changes,
  };
}

export function makeHit(changes: Partial<Ruling> = {}): SearchHit {
  return {
    ruling: makeRuling(changes),
    score: 2.5,
    matched_terms: ['damages', 'liquidated'],
    snippet: 'Late delivery triggered the liquidated damages clause.',
  };
}

export function makeAnalytics(rulings = 2): Analytics {
  return {
    disclaimer: 'Illustrative statistics over an invented corpus.',
    rulings,
    outcome_distribution: [
      { outcome: 'UPHELD', count: 1, percent: 50 },
      { outcome: 'DISMISSED', count: 1, percent: 50 },
      { outcome: 'SETTLED_WITH_COSTS', count: 0, percent: 0 },
      { outcome: 'COMPLIANCE_ORDER', count: 0, percent: 0 },
    ],
    exposure: { total_gbp: 507_500, median_gbp: '253750.50', highest_gbp: 412_000 },
    top_clauses: [
      { article: 'COC art. 14', count: 2 },
      { article: 'COC art. 31', count: 1 },
    ],
    authority_trend: [
      {
        authority: 'Meridian Commercial Disputes Bench',
        rulings: 2,
        upheld_or_ordered: 1,
        percent: 50,
        direction: 'FALLING',
        by_year: [
          { year: 2024, rulings: 1, upheld_or_ordered: 1, percent: 100 },
          { year: 2025, rulings: 1, upheld_or_ordered: 0, percent: 0 },
        ],
      },
    ],
  };
}

export function makeSearch(changes: Partial<SearchSnapshot> = {}): SearchSnapshot {
  return {
    tenant_id: LAW.tenant_id,
    query: '',
    total: 1,
    results: [makeHit()],
    analytics: makeAnalytics(),
    ...changes,
  };
}

export function makeSummary(total = 2): StreamSummary {
  return {
    tenant_id: LAW.tenant_id,
    total,
    sent: total,
    truncated: false,
    elapsed_ms: 240,
    analytics: makeAnalytics(total),
  };
}

export function makeEstimate(percent = 47.5): Estimate {
  return {
    disclaimer: 'Illustrative statistics over an invented corpus.',
    method: 'Smoothed empirical rate.',
    target_outcome: 'UPHELD',
    sample_size: 4,
    confidence: 'MODERATE',
    estimated_percent: percent,
    factors: [
      { label: 'All rulings of this tenant', matching: 4, rulings: 10, percent: 40 },
      { label: 'Rulings matching both choices', matching: 2, rulings: 4, percent },
    ],
  };
}

export function makeCrawl(changes: Partial<CrawlRun> = {}): CrawlRun {
  return {
    run_id: 'RUN-LAW-0001',
    tenant_id: LAW.tenant_id,
    source_portal: 'MERIDIAN_DOCKET_GAZETTE',
    state: 'RUNNING',
    started_at: '2026-01-05T09:00:00Z',
    finished_at: null,
    planned_rulings: 3,
    stages: [
      { stage: 'CONNECTING_PORTAL', at: '2026-01-05T09:00:00Z', detail: 'Opening a simulated session.', docket_id: null },
      { stage: 'PARSING_DOCKETS', at: '2026-01-05T09:00:01Z', detail: 'Listing new dockets: 3 found.', docket_id: null },
    ],
    ...changes,
  };
}

export function makeSnapshot(tenant: Tenant = LAW, rulings = 10): TenantSnapshot {
  const law = tenant.tenant_id === LAW.tenant_id;
  return {
    sequence: 1,
    generated_at: '2026-01-05T09:00:00Z',
    tenant,
    corpus: corpus(rulings),
    authorities: law
      ? ['Halden Labour Review Board', 'Meridian Commercial Disputes Bench']
      : ['Kestrel Industrial Safety Inspectorate'],
    matters: law ? ['COMMERCIAL', 'LABOUR'] : ['INDUSTRIAL_SAFETY', 'MACHINERY'],
    crawl: null,
    recent: [],
    events: [],
  };
}
