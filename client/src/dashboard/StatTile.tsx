const COMPACT = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });

/**
 * One headline number with its label, compacted from 1,000 up (12.9K).
 *
 *     <StatTile label="On loan" value={42} />
 */
export function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  /** Marks a number someone should act on; the label says why, not the colour. */
  tone?: 'attention';
}) {
  return (
    <div className={tone === 'attention' && value > 0 ? 'stat-tile attention' : 'stat-tile'}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value < 1000 ? value : COMPACT.format(value)}</span>
    </div>
  );
}
