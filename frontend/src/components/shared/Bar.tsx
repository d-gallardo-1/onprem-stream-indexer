const FILL = {
  link: 'fill-link',
  nominal: 'fill-nominal',
  warn: 'fill-warn',
  critical: 'fill-critical',
} as const;

interface Props {
  /** Share of the bar to fill, from 0 to 1. */
  value: number;
  label: string;
  tone?: keyof typeof FILL;
}

/**
 * A proportional bar drawn as SVG. An inline `style` width would be refused by
 * the Content Security Policy (`style-src 'self'`); SVG attributes are not.
 */
export function Bar({ value, label, tone = 'link' }: Props) {
  const width = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0)) * 100;
  return (
    <svg
      role="img"
      aria-label={label}
      viewBox="0 0 100 6"
      preserveAspectRatio="none"
      className="h-1.5 w-full overflow-hidden rounded-full bg-edge"
    >
      <rect width={width} height="6" className={FILL[tone]} />
    </svg>
  );
}
