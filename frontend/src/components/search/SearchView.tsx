import { useEffect } from 'react';
import { useFetched } from '../../hooks/useFetched';
import { useSearchStream } from '../../hooks/useSearchStream';
import { api } from '../../lib/api';
import type { LabelledCode, Outcome, SearchQuery, TenantSnapshot } from '../../types/lexstream';
import { AnalyticsPanel } from './AnalyticsPanel';
import { EstimatePanel } from './EstimatePanel';
import { FilterBar } from './FilterBar';
import { ResultList } from './ResultList';

export const SEARCH_DEBOUNCE_MS = 250;

interface Props {
  snapshot: TenantSnapshot;
  outcomes: Outcome[];
  matters: LabelledCode[];
  query: SearchQuery;
  onQueryChange: (query: SearchQuery) => void;
}

/**
 * Live Search & Outcome Analytics (orchestrator). The list is filled either by
 * an ordinary request, or progressively over SSE when the stream button is
 * pressed. Both run inside the partition of the selected tenant.
 */
export function SearchView({ snapshot, outcomes, matters, query, onQueryChange }: Props) {
  const tenantId = snapshot.tenant.tenant_id;
  const corpusRulings = snapshot.corpus.rulings;
  const { state: stream, start, cancel } = useSearchStream();
  const fetched = useFetched(
    (signal) => api.searchSnapshot(tenantId, query, signal),
    [tenantId, query, corpusRulings],
    SEARCH_DEBOUNCE_MS,
  );

  // A streamed list belongs to the filters it was started with.
  useEffect(() => cancel, [cancel, tenantId, query]);

  const streamed = stream.status !== 'idle';
  const analytics = streamed ? stream.summary?.analytics : fetched.data?.analytics;
  const hits = streamed
    ? stream.hits.map(({ hit, arrivedMs }) => ({ hit, arrivedMs }))
    : (fetched.data?.results ?? []).map((hit) => ({ hit }));

  let status = fetched.data ? `${fetched.data.total} ruling(s)` : 'Searching…';
  if (stream.status === 'streaming') {
    status = `Streaming: ${stream.hits.length} of ${stream.expected ?? '…'} received`;
  } else if (stream.status === 'done' && stream.summary) {
    const last = stream.hits[stream.hits.length - 1]?.arrivedMs ?? 0;
    status = `Stream complete: ${stream.summary.sent} of ${stream.summary.total} ruling(s) in ${last} ms`;
    if (stream.summary.truncated) status += ' (capped)';
  } else if (stream.status === 'error') {
    status = 'The search stream was interrupted.';
  }

  return (
    <div className="space-y-4">
      <FilterBar query={query} authorities={snapshot.authorities} outcomes={outcomes}
        streaming={stream.status === 'streaming'} onChange={onQueryChange}
        onStream={() => start(api.searchStreamUrl(tenantId, query))} />

      <div className="grid gap-4 xl:grid-cols-5">
        <section className="panel space-y-3 p-4 xl:col-span-3" aria-label="Search results">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="panel-title">Rulings of {snapshot.tenant.name}</h2>
            <p role="status" className="font-mono text-xs text-slate-300">{status}</p>
          </div>
          {stream.status === 'error' && (
            <p role="alert" className="text-sm text-critical">
              The stream closed before its summary arrived. Press the button to run it again.
            </p>
          )}
          {!streamed && fetched.error && (
            <p role="alert" className="text-sm text-critical">{fetched.error}</p>
          )}
          {(streamed || fetched.data) && (
            <ResultList hits={hits}
              empty={stream.status === 'streaming'
                ? 'Waiting for the first ruling…'
                : 'No ruling of this tenant matches. Every word must match; try fewer words or clear a filter.'} />
          )}
        </section>

        <div className="space-y-4 xl:col-span-2">
          {analytics ? (
            <AnalyticsPanel analytics={analytics} />
          ) : (
            <p className="panel p-4 text-sm text-slate-400">
              {streamed ? 'Analytics arrive with the final event of the stream.' : 'Computing analytics…'}
            </p>
          )}
          <EstimatePanel tenantId={tenantId} authorities={snapshot.authorities} outcomes={outcomes}
            matters={matters.filter((matter) => snapshot.matters.includes(matter.code))}
            corpusRulings={corpusRulings} />
        </div>
      </div>
    </div>
  );
}
