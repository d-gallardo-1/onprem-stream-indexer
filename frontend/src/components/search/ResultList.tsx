import { codeLabel, gbp } from '../../lib/format';
import { splitHighlight } from '../../lib/highlight';
import type { SearchHit } from '../../types/lexstream';
import { OutcomeBadge } from '../shared/OutcomeBadge';

export interface ListedHit {
  hit: SearchHit;
  /** Set for rulings that arrived over the search stream. */
  arrivedMs?: number;
}

function Hit({ hit, arrivedMs }: ListedHit) {
  const { ruling } = hit;
  return (
    <li className="rounded-md border border-edge p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 text-sm font-medium text-slate-100">{ruling.title}</h3>
        <div className="flex items-center gap-2">
          {arrivedMs !== undefined && (
            <span className="rounded border border-link/50 px-1.5 py-0.5 font-mono text-[11px] text-link">
              +{arrivedMs} ms
            </span>
          )}
          <OutcomeBadge outcome={ruling.outcome} />
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-400">
        <span className="tag text-xs">{ruling.docket_id}</span> · {ruling.authority} ·{' '}
        {codeLabel(ruling.matter)} · {ruling.decision_date} · {ruling.judge_or_inspector}
        {ruling.source === 'SIMULATED_CRAWL' && ' · simulated crawl'}
      </p>
      <p className="mt-2 text-sm text-slate-300">
        {splitHighlight(hit.snippet || ruling.summary_excerpt, hit.matched_terms).map((segment, position) =>
          segment.hit ? (
            <mark key={position} className="rounded bg-link/25 px-0.5 text-slate-100">
              {segment.text}
            </mark>
          ) : (
            <span key={position}>{segment.text}</span>
          ),
        )}
      </p>
      <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-300">
        <span className="font-mono text-slate-100">{gbp(ruling.financial_exposure_gbp)}</span>
        <span className="text-slate-400">exposure</span>
        {ruling.cited_articles.map((article) => (
          <span key={article} className="rounded border border-edge bg-obsidian px-1.5 py-0.5 font-mono">
            {article}
          </span>
        ))}
      </p>
    </li>
  );
}

export function ResultList({ hits, empty }: { hits: ListedHit[]; empty: string }) {
  if (hits.length === 0) return <p className="text-sm text-slate-400">{empty}</p>;
  return (
    <ul className="space-y-2">
      {hits.map((item) => (
        <Hit key={item.hit.ruling.docket_id} {...item} />
      ))}
    </ul>
  );
}
