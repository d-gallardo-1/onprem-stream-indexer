import { Minus, TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';
import { gbp, percentText } from '../../lib/format';
import type { Analytics, AuthorityTrend } from '../../types/lexstream';
import { Bar } from '../shared/Bar';
import { OUTCOME_META, OutcomeBadge } from '../shared/OutcomeBadge';

const DIRECTION: Record<AuthorityTrend['direction'], { label: string; icon: LucideIcon; classes: string }> = {
  RISING: { label: 'Rising', icon: TrendingUp, classes: 'text-nominal' },
  FALLING: { label: 'Falling', icon: TrendingDown, classes: 'text-red-400' },
  STEADY: { label: 'Steady', icon: Minus, classes: 'text-slate-300' },
  SINGLE_YEAR: { label: 'One year only', icon: Minus, classes: 'text-slate-400' },
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-edge bg-obsidian p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 font-mono text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

/** Descriptive statistics of the rulings that match the current query. */
export function AnalyticsPanel({ analytics }: { analytics: Analytics }) {
  const mostCited = Math.max(1, ...analytics.top_clauses.map((clause) => clause.count));

  return (
    <section className="panel space-y-4 p-4" aria-label="Outcome analytics">
      <h2 className="panel-title">Outcome analytics · {analytics.rulings} ruling(s) in this query</h2>

      <ul className="space-y-2" aria-label="Outcome distribution">
        {analytics.outcome_distribution.map((share) => (
          <li key={share.outcome}>
            <div className="flex items-center justify-between gap-2">
              <OutcomeBadge outcome={share.outcome} />
              <span className="font-mono text-sm text-slate-100">
                {percentText(share.percent)} <span className="text-slate-400">({share.count})</span>
              </span>
            </div>
            <div className="mt-1">
              <Bar value={share.percent / 100} tone={OUTCOME_META[share.outcome].tone}
                label={`${share.outcome}: ${percentText(share.percent)}`} />
            </div>
          </li>
        ))}
      </ul>

      <div className="grid grid-cols-3 gap-2">
        <Metric label="Total exposure" value={gbp(analytics.exposure.total_gbp)} />
        <Metric label="Median exposure" value={gbp(analytics.exposure.median_gbp)} />
        <Metric label="Highest exposure" value={gbp(analytics.exposure.highest_gbp)} />
      </div>

      <div>
        <h3 className="text-xs font-medium text-slate-400">Most cited clauses</h3>
        {analytics.top_clauses.length === 0 ? (
          <p className="mt-1 text-sm text-slate-400">No citations in this query.</p>
        ) : (
          <ol className="mt-1 space-y-1.5">
            {analytics.top_clauses.map((clause) => (
              <li key={clause.article} className="text-sm">
                <div className="flex justify-between gap-2">
                  <span className="font-mono text-slate-200">{clause.article}</span>
                  <span className="font-mono text-slate-400">{clause.count}</span>
                </div>
                <Bar value={clause.count / mostCited} label={`${clause.article}: ${clause.count} citations`} />
              </li>
            ))}
          </ol>
        )}
      </div>

      <div>
        <h3 className="text-xs font-medium text-slate-400">
          Resolution trend by authority (share upheld or ending in a compliance order)
        </h3>
        <ul className="mt-1 divide-y divide-edge">
          {analytics.authority_trend.map((trend) => {
            const direction = DIRECTION[trend.direction];
            const Icon = direction.icon;
            return (
              <li key={trend.authority} className="py-2 text-sm">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="text-slate-200">{trend.authority}</span>
                  <span className={`inline-flex items-center gap-1 font-mono text-xs ${direction.classes}`}>
                    <Icon aria-hidden="true" className="h-3.5 w-3.5" />
                    {direction.label}
                  </span>
                </div>
                <p className="font-mono text-xs text-slate-400">
                  {trend.by_year
                    .map((point) => `${point.year}: ${percentText(point.percent)} of ${point.rulings}`)
                    .join('  →  ')}
                </p>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
