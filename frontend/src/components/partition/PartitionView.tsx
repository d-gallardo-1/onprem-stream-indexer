import { Download } from 'lucide-react';
import { api } from '../../lib/api';
import { OUTCOME_LABEL } from '../../lib/format';
import type { Directory, Outcome, SearchQuery, Tenant } from '../../types/lexstream';
import { Notice } from '../shared/Notice';
import { ArchitectureDiagram } from './ArchitectureDiagram';

interface Props {
  tenant: Tenant;
  directory: Directory;
  /** The query of the search view; the report covers exactly this query. */
  query: SearchQuery;
}

export const PARTITION_NOTICE =
  'This is data partitioning per tenant, not access control. The demo has no login, so the tenant selector decides which partition a request reads.';

const ROUTES: [string, string][] = [
  ['GET /search/snapshot', 'Results and analytics of one tenant'],
  ['GET /search/stream', 'The same search, one ruling per SSE event, then the summary'],
  ['GET /analytics/estimate', 'Estimator over one tenant\'s rulings'],
  ['POST /ingest/simulate-crawl', 'Adds synthetic rulings to one tenant'],
  ['GET /ingest/stream', 'Live state of one tenant (SSE)'],
  ['GET /export/analytics-xlsx', 'Report of one tenant\'s query'],
];

/** Tenant Partitioning & Export Inspector (orchestrator). */
export function PartitionView({ tenant, directory, query }: Props) {
  const filters = [
    `Text: ${query.q.trim() || 'all rulings'}`,
    `Authority: ${query.authority || 'any'}`,
    `Outcome: ${query.outcome ? OUTCOME_LABEL[query.outcome as Outcome] : 'any'}`,
  ];

  return (
    <div className="space-y-4">
      <Notice>{PARTITION_NOTICE}</Notice>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="panel p-4" aria-label="Architecture">
          <h2 className="panel-title">How a request reaches a partition</h2>
          <div className="mt-3">
            <ArchitectureDiagram directory={directory} activeTenantId={tenant.tenant_id} />
          </div>
        </section>

        <div className="space-y-4">
          <section className="panel p-4" aria-label="Export">
            <h2 className="panel-title">Export the current query of {tenant.tenant_id}</h2>
            <p className="mt-2 text-sm text-slate-300">
              The workbook holds the matching rulings of {tenant.name}, the analytics of that
              query and the trend by authority.
            </p>
            <ul className="mt-2 space-y-0.5 font-mono text-xs text-slate-300">
              {filters.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <a className="btn mt-3" href={api.exportUrl(tenant.tenant_id, query)} download>
              <Download aria-hidden="true" className="h-4 w-4" />
              Download .xlsx report
            </a>
            <p className="mt-2 text-xs text-slate-400">
              Cell text that starts with =, +, - or @ is written as plain text, so a spreadsheet
              program cannot run it as a formula.
            </p>
          </section>

          <section className="panel p-4" aria-label="Scoped routes">
            <h2 className="panel-title">Routes that pass through the scoping layer</h2>
            <table className="mt-3 w-full text-left text-sm">
              <thead className="text-xs text-slate-400">
                <tr>
                  <th scope="col" className="pb-2 font-medium">Route</th>
                  <th scope="col" className="pb-2 font-medium">What it touches</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-edge">
                {ROUTES.map(([route, effect]) => (
                  <tr key={route}>
                    <th scope="row" className="py-1.5 pr-3 font-mono text-xs font-normal text-slate-100">{route}</th>
                    <td className="py-1.5 text-slate-300">{effect}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-slate-400">
              Each of them requires <span className="font-mono">tenant_id</span>. A real deployment
              would take the tenant from a verified identity instead of a parameter.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
