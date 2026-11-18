import { useState } from 'react';
import { useFetched } from '../../hooks/useFetched';
import { api } from '../../lib/api';
import { OUTCOME_LABEL, percentText } from '../../lib/format';
import type { Estimate, EstimateInput, LabelledCode, Outcome } from '../../types/lexstream';
import { Bar } from '../shared/Bar';

interface Props {
  tenantId: string;
  authorities: string[];
  /** Matters this tenant follows. */
  matters: LabelledCode[];
  outcomes: Outcome[];
  /** Number of rulings in the partition; the estimate is recomputed when it changes. */
  corpusRulings: number;
  /** Times the state stream came back; the estimate is asked again on each return. */
  reconnects: number;
}

const FIELD = 'rounded-md border border-edge bg-obsidian px-2 py-1.5 text-sm text-slate-100';
const CONFIDENCE: Record<Estimate['confidence'], string> = {
  LOW: 'Low: fewer than 3 matching rulings',
  MODERATE: 'Moderate: fewer than 8 matching rulings',
  HIGHER: 'Higher: 8 or more matching rulings',
};

/** Illustrative estimate with every step of the calculation on screen. */
export function EstimatePanel({ tenantId, authorities, matters, outcomes, corpusRulings, reconnects }: Props) {
  const [input, setInput] = useState<EstimateInput>({ authority: '', matter: '', outcome: 'UPHELD' });
  const { data, error } = useFetched(
    (signal) => api.estimate(tenantId, input, signal),
    [tenantId, input, corpusRulings, reconnects],
  );
  const set = (field: keyof EstimateInput) => (value: string) =>
    setInput((current) => ({ ...current, [field]: value }));

  return (
    <section className="panel space-y-3 p-4" aria-label="Illustrative outcome estimator">
      <h2 className="panel-title">Illustrative outcome estimator</h2>
      <p className="rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
        Illustrative only. A smoothed rate over an invented corpus; it is not legal advice and
        describes no real court or regulator.
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Estimate authority
          <select className={FIELD} value={input.authority}
            onChange={(event) => set('authority')(event.target.value)}>
            <option value="">Any authority</option>
            {authorities.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Estimate matter
          <select className={FIELD} value={input.matter}
            onChange={(event) => set('matter')(event.target.value)}>
            <option value="">Any matter</option>
            {matters.map((matter) => (
              <option key={matter.code} value={matter.code}>{matter.label}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Estimate outcome
          <select className={FIELD} value={input.outcome}
            onChange={(event) => set('outcome')(event.target.value)}>
            {outcomes.map((outcome) => (
              <option key={outcome} value={outcome}>{OUTCOME_LABEL[outcome]}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p role="alert" className="text-sm text-critical">{error}</p>}
      {!data && !error && <p className="text-sm text-slate-400">Computing…</p>}
      {data && (
        <div>
          <p className="text-xs text-slate-400">
            Estimated share ending "{OUTCOME_LABEL[data.target_outcome]}"
          </p>
          <p className="font-mono text-3xl font-semibold text-slate-100" data-testid="estimate">
            {percentText(data.estimated_percent)}
          </p>
          <p className="text-xs text-slate-400">
            Sample: {data.sample_size} matching ruling(s). Confidence: {CONFIDENCE[data.confidence]}.
          </p>
          <ol className="mt-2 space-y-2" aria-label="Steps of the estimate">
            {data.factors.map((factor) => (
              <li key={factor.label} className="text-sm">
                <div className="flex justify-between gap-2">
                  <span className="text-slate-200">{factor.label}</span>
                  <span className="font-mono text-slate-100">{percentText(factor.percent)}</span>
                </div>
                <Bar value={factor.percent / 100} label={`${factor.label}: ${percentText(factor.percent)}`} />
                <p className="text-xs text-slate-400">
                  {factor.matching} of {factor.rulings} ruling(s) ended this way
                </p>
              </li>
            ))}
          </ol>
          <p className="mt-2 text-xs text-slate-400">{data.method}</p>
        </div>
      )}
    </section>
  );
}
