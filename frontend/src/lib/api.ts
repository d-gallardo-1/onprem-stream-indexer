import type {
  Directory,
  Estimate,
  EstimateInput,
  SearchQuery,
  SearchSnapshot,
} from '../types/lexstream';

// Same-origin API: Nginx (Docker) or the Vite dev server proxies /api to the backend.
export const API_BASE = '/api/v1';

export const EMPTY_QUERY: SearchQuery = { q: '', authority: '', outcome: '' };
export const MAX_QUERY_CHARS = 120;
/** A request that has not answered after this long is given up on. */
export const REQUEST_TIMEOUT_MS = 15_000;

/** Uses the server's own explanation when it sends one, so refusals are readable. */
async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    /* not JSON: fall through */
  }
  return fallback;
}

/**
 * Every request has a time limit. Without one, a backend that accepts the
 * connection and never answers would leave a button on "pending" for good.
 * The caller's own signal (a newer search replacing this one) still cancels.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const label = `${init?.method ?? 'GET'} ${path}`;
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  const cancel = () => controller.abort();
  init?.signal?.addEventListener('abort', cancel);
  if (init?.signal?.aborted) cancel();
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
    if (!response.ok) {
      throw new Error(await errorMessage(response, `${label} failed with HTTP ${response.status}`));
    }
    return (await response.json()) as T;
  } catch (cause) {
    if (timedOut) throw new Error(`${label} timed out after ${REQUEST_TIMEOUT_MS / 1000} s`);
    throw cause;
  } finally {
    clearTimeout(timer);
    init?.signal?.removeEventListener('abort', cancel);
  }
}

/**
 * Query string of a tenant request. The tenant always comes first and is always
 * present; the backend resolves it before doing anything else. Empty filters are omitted.
 */
export function tenantParams(tenantId: string, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams({ tenant_id: tenantId });
  for (const [key, value] of Object.entries(extra)) {
    const text = value.trim();
    if (text) params.set(key, text);
  }
  return `?${params.toString()}`;
}

const searchParams = (tenantId: string, query: SearchQuery) => tenantParams(tenantId, { ...query });

export const api = {
  directory: () => request<Directory>('/tenants'),
  searchSnapshot: (tenantId: string, query: SearchQuery, signal?: AbortSignal) =>
    request<SearchSnapshot>(`/search/snapshot${searchParams(tenantId, query)}`, { signal }),
  estimate: (tenantId: string, input: EstimateInput, signal?: AbortSignal) =>
    request<Estimate>(`/analytics/estimate${tenantParams(tenantId, { ...input })}`, { signal }),
  /** Starts a simulated crawl. Its stages arrive on the tenant's state stream. */
  startCrawl: (tenantId: string, sourcePortal: string, rulings: number) =>
    request<{ run_id: string }>('/ingest/simulate-crawl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tenant_id: tenantId, source_portal: sourcePortal, rulings }),
    }),
  reset: () => request<{ status: string }>('/ingest/reset', { method: 'POST' }),
  searchStreamUrl: (tenantId: string, query: SearchQuery) =>
    `${API_BASE}/search/stream${searchParams(tenantId, query)}`,
  stateStreamUrl: (tenantId: string) => `${API_BASE}/ingest/stream${tenantParams(tenantId)}`,
  exportUrl: (tenantId: string, query: SearchQuery) =>
    `${API_BASE}/export/analytics-xlsx${searchParams(tenantId, query)}`,
};
