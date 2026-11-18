import { Radio, Search, X } from 'lucide-react';
import { EMPTY_QUERY, MAX_QUERY_CHARS } from '../../lib/api';
import { OUTCOME_LABEL } from '../../lib/format';
import type { Outcome, SearchQuery } from '../../types/lexstream';

interface Props {
  query: SearchQuery;
  /** Authorities present in the selected tenant's partition. */
  authorities: string[];
  outcomes: Outcome[];
  streaming: boolean;
  onChange: (query: SearchQuery) => void;
  onStream: () => void;
}

const FIELD = 'rounded-md border border-edge bg-obsidian px-2 py-1.5 text-sm text-slate-100';

export function FilterBar({ query, authorities, outcomes, streaming, onChange, onStream }: Props) {
  const set = (field: keyof SearchQuery) => (value: string) => onChange({ ...query, [field]: value });
  const filtered = Object.values(query).some((value) => value !== '');

  return (
    <form className="panel space-y-3 p-4" role="search" onSubmit={(event) => event.preventDefault()}>
      <label className="flex items-center gap-2 rounded-md border border-edge bg-obsidian px-3 py-2 focus-within:border-link">
        <Search aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-400" />
        <span className="sr-only">Search this tenant's rulings</span>
        <input
          type="search"
          className="w-full bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-400"
          placeholder="Search titles, summaries, authorities, cited articles or dockets"
          maxLength={MAX_QUERY_CHARS}
          value={query.q}
          onChange={(event) => set('q')(event.target.value)}
        />
      </label>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-xs text-slate-400">
          Authority
          <select className={FIELD} value={query.authority}
            onChange={(event) => set('authority')(event.target.value)}>
            <option value="">Any authority</option>
            {authorities.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </label>
        <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs text-slate-400">
          Outcome
          <select className={FIELD} value={query.outcome}
            onChange={(event) => set('outcome')(event.target.value)}>
            <option value="">Any outcome</option>
            {outcomes.map((outcome) => (
              <option key={outcome} value={outcome}>{OUTCOME_LABEL[outcome]}</option>
            ))}
          </select>
        </label>
        <button type="button" className="btn" disabled={!filtered} onClick={() => onChange(EMPTY_QUERY)}>
          <X aria-hidden="true" className="h-4 w-4" />
          Clear
        </button>
        <button type="button" disabled={streaming} onClick={onStream}
          className="btn border-link/60 bg-link/10 text-link hover:border-link hover:bg-link/20">
          <Radio aria-hidden="true" className={`h-4 w-4 ${streaming ? 'motion-safe:animate-pulse' : ''}`} />
          {streaming ? 'Streaming…' : 'Stream Search via SSE'}
        </button>
      </div>
    </form>
  );
}
