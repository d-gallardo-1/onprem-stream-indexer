import { CheckCircle2, FilePlus2, FileSearch, Loader, PlugZap, ScanText, XCircle, type LucideIcon } from 'lucide-react';
import { codeLabel, formatTime, STAGE_LABEL } from '../../lib/format';
import type { CrawlRun, CrawlStage } from '../../types/lexstream';

const STAGE_ICON: Record<CrawlStage, LucideIcon> = {
  CONNECTING_PORTAL: PlugZap,
  PARSING_DOCKETS: FileSearch,
  EXTRACTING_METADATA: ScanText,
  INDEXED_NEW_RULING: FilePlus2,
};

const STATE: Record<CrawlRun['state'], { label: string; icon: LucideIcon; classes: string }> = {
  RUNNING: { label: 'Running', icon: Loader, classes: 'border-warn/50 bg-warn/10 text-warn' },
  COMPLETED: { label: 'Completed', icon: CheckCircle2, classes: 'border-nominal/50 bg-nominal/10 text-nominal' },
  // A run that stopped on an error; it no longer blocks the next crawl.
  FAILED: { label: 'Failed', icon: XCircle, classes: 'border-critical/50 bg-critical/10 text-critical' },
};

/** Stages of the tenant's latest crawl, in the order the state stream delivered them. */
export function StageTimeline({ crawl }: { crawl: CrawlRun | null }) {
  if (!crawl) {
    return (
      <section className="panel p-4" aria-label="Crawl stages">
        <h2 className="panel-title">Crawl stages</h2>
        <p className="mt-3 text-sm text-slate-400">
          No crawl has run for this tenant yet. Start one to watch its stages arrive.
        </p>
      </section>
    );
  }
  const running = crawl.state === 'RUNNING';
  const state = STATE[crawl.state];
  const StateIcon = state.icon;

  return (
    <section className="panel p-4" aria-label="Crawl stages">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="panel-title">
          Crawl stages · {crawl.run_id} · {codeLabel(crawl.source_portal)}
        </h2>
        <span role="status"
          className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-[11px] font-semibold ${state.classes}`}>
          <StateIcon aria-hidden="true" className={`h-3.5 w-3.5 ${running ? 'motion-safe:animate-spin' : ''}`} />
          {state.label}
        </span>
      </div>
      <ol className="mt-3 space-y-2">
        {crawl.stages.map((stage, position) => {
          const Icon = STAGE_ICON[stage.stage];
          return (
            <li key={`${stage.at}-${position}`} className="flex gap-3 text-sm">
              <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-link" />
              <div className="min-w-0 flex-1">
                <p className="text-slate-100">
                  {STAGE_LABEL[stage.stage]}
                  {stage.docket_id && <span className="tag ml-2 text-xs">{stage.docket_id}</span>}
                </p>
                <p className="break-words text-xs text-slate-400">{stage.detail}</p>
              </div>
              <time className="shrink-0 font-mono text-xs text-slate-400" dateTime={stage.at}>
                {formatTime(stage.at)}
              </time>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
