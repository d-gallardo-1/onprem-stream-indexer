import { ArrowDown } from 'lucide-react';
import type { Directory } from '../../types/lexstream';

function Layer({ title, detail, accent = false }: { title: string; detail: string; accent?: boolean }) {
  return (
    <div className={`rounded-md border p-3 text-center ${accent ? 'border-link/60 bg-link/10' : 'border-edge bg-obsidian'}`}>
      <p className={`text-sm font-semibold ${accent ? 'text-link' : 'text-slate-100'}`}>{title}</p>
      <p className="mt-0.5 text-xs text-slate-400">{detail}</p>
    </div>
  );
}

const Arrow = () => (
  <ArrowDown aria-hidden="true" className="mx-auto h-4 w-4 text-slate-400" />
);

interface Props {
  directory: Directory;
  activeTenantId: string;
}

/** The path of a request, from the browser down to one tenant's partition. */
export function ArchitectureDiagram({ directory, activeTenantId }: Props) {
  return (
    <div className="space-y-2" role="group" aria-label="Request path">
      <Layer title="Browser" detail="React SPA; every tenant request carries tenant_id" />
      <Arrow />
      <Layer title="Nginx (unprivileged)" detail="static bundle and /api proxy, buffering off for SSE" />
      <Arrow />
      <Layer title="FastAPI routes" detail="search, search stream, estimate, ingest, export" />
      <Arrow />
      <Layer accent title="TenantStore.partition(tenant_id)"
        detail="the one scoping layer; an unknown tenant is a 404" />
      <Arrow />
      <ul className="grid gap-2 sm:grid-cols-2">
        {directory.tenants.map(({ tenant, corpus }) => {
          const active = tenant.tenant_id === activeTenantId;
          return (
            <li key={tenant.tenant_id} aria-current={active ? 'true' : undefined}
              className={`rounded-md border p-3 ${active ? 'border-nominal/60 bg-nominal/10' : 'border-edge bg-obsidian'}`}>
              <p className="font-mono text-sm font-semibold text-slate-100">{tenant.tenant_id}</p>
              <p className="text-xs text-slate-300">{tenant.name}</p>
              <p className="mt-1 text-xs text-slate-400">
                Own index · {corpus.rulings} rulings ({corpus.crawled_rulings} from crawls) ·{' '}
                {corpus.index_terms} terms
              </p>
              <p className="mt-1 text-xs font-medium text-slate-300">
                {active ? 'Selected: requests on this screen read this partition' : 'Not reachable from the selected tenant'}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
