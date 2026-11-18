import { Play, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import { useAction } from '../../hooks/useAction';
import { api } from '../../lib/api';
import { codeLabel, formatTime, gbp } from '../../lib/format';
import type { TenantSnapshot } from '../../types/lexstream';
import { OutcomeBadge } from '../shared/OutcomeBadge';
import { StageTimeline } from './StageTimeline';

interface Props {
  snapshot: TenantSnapshot;
  /** The fixed list of fictional portals the backend accepts. */
  portals: string[];
}

const FIELD = 'rounded-md border border-edge bg-obsidian px-2 py-1.5 text-sm text-slate-100';

function Counter({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-3">
      <p className="panel-title">{label}</p>
      <p className="mt-1 font-mono text-2xl font-semibold text-slate-100">{value}</p>
    </div>
  );
}

/**
 * Ingestion Simulator (orchestrator). The buttons only send commands; every
 * change on screen arrives through the tenant's state stream.
 */
export function IngestView({ snapshot, portals }: Props) {
  const { tenant, corpus, crawl } = snapshot;
  const [portal, setPortal] = useState(portals[0] ?? '');
  const [rulings, setRulings] = useState(3);
  const { pending, error, run } = useAction();
  const running = crawl?.state === 'RUNNING';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Counter label="Rulings indexed" value={String(corpus.rulings)} />
        <Counter label="Added by crawls" value={String(corpus.crawled_rulings)} />
        <Counter label="Index terms" value={String(corpus.index_terms)} />
        <Counter label="Total exposure" value={gbp(corpus.total_exposure_gbp)} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="panel space-y-3 p-4" aria-label="Simulated crawl">
          <h2 className="panel-title">Simulated crawl for {tenant.tenant_id}</h2>
          <p className="text-xs text-slate-400">
            Nothing is fetched: the portal is a label from a fixed list and the new rulings are
            generated locally. A production worker would drive a headless browser instead.
          </p>
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Source portal
            <select className={FIELD} value={portal} onChange={(event) => setPortal(event.target.value)}>
              {portals.map((name) => (
                <option key={name} value={name}>{codeLabel(name)}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            New rulings to index
            <select className={FIELD} value={rulings}
              onChange={(event) => setRulings(Number(event.target.value))}>
              {[1, 2, 3, 4, 5].map((count) => (
                <option key={count} value={count}>{count}</option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn" disabled={running || pending.has('crawl') || !portal}
              onClick={() => run('crawl', () => api.startCrawl(tenant.tenant_id, portal, rulings))}>
              <Play aria-hidden="true" className="h-4 w-4" />
              {running ? 'Crawl running…' : 'Run simulated crawl'}
            </button>
            <button type="button" className="btn" disabled={pending.has('reset')}
              onClick={() => run('reset', api.reset)}>
              <RotateCcw aria-hidden="true" className="h-4 w-4" />
              Reset corpus
            </button>
          </div>
          <p className="text-xs text-slate-400">Reset restores the default corpus of every tenant.</p>
          {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
        </section>

        <div className="space-y-4 xl:col-span-2">
          <StageTimeline crawl={crawl} />

          <section className="panel p-4" aria-label="Rulings added by crawls">
            <h2 className="panel-title">Newest rulings added to this tenant's index</h2>
            {snapshot.recent.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400">None yet: the index holds the default corpus.</p>
            ) : (
              <ul className="mt-3 divide-y divide-edge">
                {snapshot.recent.map((ruling) => (
                  <li key={ruling.docket_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
                    <span className="tag text-xs">{ruling.docket_id}</span>
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-100">{ruling.title}</span>
                    <span className="text-xs text-slate-400">{ruling.authority}</span>
                    <OutcomeBadge outcome={ruling.outcome} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel p-4" aria-label="Activity log">
            <h2 className="panel-title">Activity log</h2>
            {snapshot.events.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400">No activity since start-up.</p>
            ) : (
              <ol className="mt-3 space-y-1.5">
                {snapshot.events.map((event, position) => (
                  <li key={`${event.at}-${position}`} className="flex gap-3 text-sm">
                    <time className="shrink-0 font-mono text-xs leading-5 text-slate-400" dateTime={event.at}>
                      {formatTime(event.at)}
                    </time>
                    <span className="w-36 shrink-0 font-mono text-xs leading-5 text-link">{event.kind}</span>
                    <span className="min-w-0 break-words text-slate-200">{event.message}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
