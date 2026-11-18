import type { CrawlStage, Outcome } from '../types/lexstream';

export const OUTCOME_LABEL: Record<Outcome, string> = {
  UPHELD: 'Upheld',
  DISMISSED: 'Dismissed',
  SETTLED_WITH_COSTS: 'Settled with costs',
  COMPLIANCE_ORDER: 'Compliance order',
};

export const STAGE_LABEL: Record<CrawlStage, string> = {
  CONNECTING_PORTAL: 'Connecting to portal',
  PARSING_DOCKETS: 'Parsing dockets',
  EXTRACTING_METADATA: 'Extracting metadata',
  INDEXED_NEW_RULING: 'Indexed new ruling',
};

/** `INDUSTRIAL_SAFETY` becomes `Industrial safety`. */
export function codeLabel(code: string): string {
  const text = code.replace(/_/g, ' ').toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Pounds for display. The backend sends whole pounds as integers and the median
 * as exact decimal text; pence are shown only when they are not zero.
 */
export function gbp(amount: number | string): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) return '£–';
  const pence = Number.isInteger(value) ? 0 : 2;
  return `£${value.toLocaleString('en-GB', { minimumFractionDigits: pence, maximumFractionDigits: pence })}`;
}

export function percentText(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatTime(iso: string | null): string {
  const date = new Date(iso ?? '');
  if (Number.isNaN(date.getTime())) return '--:--:--';
  return date.toLocaleTimeString('en-GB', { hour12: false });
}
