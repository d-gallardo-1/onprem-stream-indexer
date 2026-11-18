import { useEffect, useState } from 'react';
import { IngestView } from './components/ingest/IngestView';
import { PartitionView } from './components/partition/PartitionView';
import { SearchView } from './components/search/SearchView';
import { TopBar } from './components/TopBar';
import { useFetched } from './hooks/useFetched';
import { useReconnects, useTenantStream } from './hooks/useTenantStream';
import { api, EMPTY_QUERY } from './lib/api';
import type { SearchQuery, ViewId } from './types/lexstream';

/** Application shell (orchestrator): one tenant at a time, one state stream for it. */
export default function App() {
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [view, setView] = useState<ViewId>('search');
  const [query, setQuery] = useState<SearchQuery>(EMPTY_QUERY);
  const { snapshot, status } = useTenantStream(tenantId);
  const connected = status === 'CONNECTED';
  const reconnects = useReconnects(connected, tenantId);
  // Reloaded when the selected tenant's corpus changes, so its counters stay
  // current, and when the stream comes back. A reload that fails keeps the list
  // already on screen: one bad response must not take the whole UI away.
  const directory = useFetched(() => api.directory(), [snapshot?.corpus.rulings, reconnects], {
    keepDataOnError: true,
  });
  const tenants = directory.data?.tenants.map((entry) => entry.tenant) ?? [];
  const offline = status === 'DISCONNECTED';

  useEffect(() => {
    if (tenantId === null && tenants.length > 0) setTenantId(tenants[0].tenant_id);
  }, [tenantId, tenants]);

  const changeTenant = (next: string) => {
    // Filters name authorities of one tenant; they do not carry over to another.
    setQuery(EMPTY_QUERY);
    setTenantId(next);
  };

  return (
    <div className="min-h-screen">
      <TopBar tenants={tenants} tenantId={tenantId} onTenantChange={changeTenant}
        streamStatus={status} view={view} onViewChange={setView} />

      <main className="mx-auto max-w-[1600px] space-y-4 px-4 py-4">
        {directory.error && !directory.data && (
          <p role="alert" className="panel p-4 text-sm text-red-400">
            Cannot load the tenant list: {directory.error}. Check that the API is running on port
            8002 and reload.
          </p>
        )}

        {!snapshot && !directory.error && (
          <p className="panel p-4 text-sm text-slate-300" role="status">
            {offline
              ? 'Cannot reach the backend. Retrying every few seconds; check that the API is running on port 8002.'
              : 'Waiting for the first snapshot of this tenant…'}
          </p>
        )}

        {snapshot && !connected && (
          <p role="alert" className="rounded-md border border-warn/50 bg-warn/10 px-3 py-2 text-sm text-warn">
            {offline
              ? 'Live connection lost. The data below is the last snapshot received and may be out of date; controls are disabled until the stream is back.'
              : 'Reconnecting to the live stream. The data below may be a few seconds old.'}
          </p>
        )}

        {snapshot && directory.data && (
          // A disabled fieldset disables every form control inside it. The key
          // is the tenant: switching tenant discards every view's local state.
          <fieldset key={snapshot.tenant.tenant_id} disabled={offline}
            className="m-0 min-w-0 border-0 p-0">
            {view === 'search' && (
              <SearchView snapshot={snapshot} outcomes={directory.data.outcomes}
                matters={directory.data.matters} query={query} onQueryChange={setQuery}
                reconnects={reconnects} />
            )}
            {view === 'ingest' && (
              <IngestView snapshot={snapshot} portals={directory.data.source_portals} />
            )}
            {view === 'partition' && (
              <PartitionView tenant={snapshot.tenant} directory={directory.data} query={query}
                offline={offline} />
            )}
          </fieldset>
        )}
      </main>

      <footer className="mx-auto max-w-[1600px] px-4 pb-6 text-xs text-slate-400">
        Reference demo. Every ruling, authority, statute, portal, person and tenant is invented.
        The tenant selector is not a login, and nothing here is legal advice.
      </footer>
    </div>
  );
}
