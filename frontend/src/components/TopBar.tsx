import {
  Building2,
  DatabaseZap,
  Layers,
  Scale,
  Search,
  Wifi,
  WifiOff,
  type LucideIcon,
} from 'lucide-react';
import type { StreamStatus, Tenant, ViewId } from '../types/lexstream';

const TABS: { id: ViewId; label: string; icon: LucideIcon }[] = [
  { id: 'search', label: 'Live Search & Outcome Analytics', icon: Search },
  { id: 'ingest', label: 'Ingestion Simulator', icon: DatabaseZap },
  { id: 'partition', label: 'Tenant Partitioning & Export', icon: Layers },
];

const STREAM: Record<StreamStatus, { label: string; classes: string; icon: LucideIcon }> = {
  CONNECTED: { label: 'Stream live', classes: 'border-nominal/50 text-nominal', icon: Wifi },
  RECONNECTING: { label: 'Reconnecting', classes: 'border-warn/50 text-warn', icon: Wifi },
  DISCONNECTED: { label: 'Disconnected', classes: 'border-critical/50 text-critical', icon: WifiOff },
};

interface Props {
  tenants: Tenant[];
  tenantId: string | null;
  onTenantChange: (tenantId: string) => void;
  streamStatus: StreamStatus;
  view: ViewId;
  onViewChange: (view: ViewId) => void;
}

export function TopBar({ tenants, tenantId, onTenantChange, streamStatus, view, onViewChange }: Props) {
  const stream = STREAM[streamStatus];
  const StreamIcon = stream.icon;

  return (
    <header className="border-b border-edge bg-panel">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <div className="flex items-center gap-2">
          <Scale aria-hidden="true" className="h-5 w-5 text-link" />
          <div>
            <h1 className="text-base font-semibold leading-tight text-slate-100">LexStream On-Prem</h1>
            <p className="text-[11px] leading-tight text-slate-400">
              Multi-Tenant Regulatory &amp; Case-Law Intelligence Engine
            </p>
          </div>
        </div>
        <span className="rounded border border-warn/50 bg-warn/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-warn">
          Synthetic demo data
        </span>

        {/* On a narrow screen the selector takes its own full row and may shrink:
            the longest tenant name is wider than a phone, and without min-w-0 the
            select would push the page sideways. */}
        <label className="flex w-full min-w-0 items-center gap-2 text-sm text-slate-300 sm:ml-auto sm:w-auto sm:max-w-md">
          <Building2 aria-hidden="true" className="h-4 w-4 text-slate-400" />
          <span>Tenant</span>
          <select
            className="min-w-0 flex-1 truncate rounded-md border border-edge bg-obsidian px-2 py-1.5 text-sm text-slate-100"
            value={tenantId ?? ''}
            disabled={tenants.length === 0}
            onChange={(event) => onTenantChange(event.target.value)}
          >
            {tenants.map((tenant) => (
              <option key={tenant.tenant_id} value={tenant.tenant_id}>
                {tenant.tenant_id} · {tenant.name}
              </option>
            ))}
          </select>
        </label>
        <span
          role="status"
          className={`inline-flex items-center gap-1.5 rounded border bg-obsidian px-2 py-1 font-mono text-[11px] font-semibold ${stream.classes}`}
        >
          <StreamIcon aria-hidden="true" className="h-3.5 w-3.5" />
          {stream.label}
        </span>
      </div>

      <nav aria-label="Views" className="mx-auto flex max-w-[1600px] gap-1 overflow-x-auto px-4 pb-2">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = id === view;
          return (
            <button
              key={id}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => onViewChange(id)}
              className={`flex shrink-0 items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                active
                  ? 'border-link/60 bg-link/10 text-link'
                  : 'border-transparent text-slate-300 hover:bg-obsidian hover:text-slate-100'
              }`}
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
              {label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
