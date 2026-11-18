import { CheckCircle2, ClipboardCheck, Handshake, XCircle, type LucideIcon } from 'lucide-react';
import { OUTCOME_LABEL } from '../../lib/format';
import type { Outcome } from '../../types/lexstream';

export const OUTCOME_META: Record<Outcome, { icon: LucideIcon; classes: string; tone: 'nominal' | 'critical' | 'warn' | 'link' }> = {
  UPHELD: { icon: CheckCircle2, classes: 'border-nominal/50 bg-nominal/10 text-nominal', tone: 'nominal' },
  DISMISSED: { icon: XCircle, classes: 'border-critical/50 bg-critical/10 text-critical', tone: 'critical' },
  SETTLED_WITH_COSTS: { icon: Handshake, classes: 'border-warn/50 bg-warn/10 text-warn', tone: 'warn' },
  COMPLIANCE_ORDER: { icon: ClipboardCheck, classes: 'border-link/50 bg-link/10 text-link', tone: 'link' },
};

/** Colour + icon + text label, so an outcome never depends on colour alone. */
export function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  const { icon: Icon, classes } = OUTCOME_META[outcome];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-[11px] font-semibold ${classes}`}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5" />
      {OUTCOME_LABEL[outcome]}
    </span>
  );
}
