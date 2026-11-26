/** One labelled bar: what it is, and how many loans. */
export interface Bar {
  key: string | number;
  label: string;
  detail?: string;
  value: number;
}

/**
 * Horizontal bars ranked by value, each with its value at the tip, so every
 * number is readable without hovering.
 *
 *     <BarList bars={[{ key: 1, label: 'Dune', value: 4 }]} unit="loans" />
 */
export function BarList({ bars, unit }: { bars: Bar[]; unit: string }) {
  const max = Math.max(1, ...bars.map((bar) => bar.value));
  return (
    <ol className="bar-list">
      {bars.map((bar) => (
        <li key={bar.key}>
          <span className="bar-label">
            {bar.label}
            {bar.detail && <span className="bar-detail"> · {bar.detail}</span>}
          </span>
          <span className="bar-track">
            {/* Scaled against the track less room for the value, so the longest
                bar is not squeezed by its own label. */}
            <span
              className="bar-fill"
              style={{ width: `calc((100% - 3.5em) * ${bar.value / max})` }}
            />
            <span className="bar-value">
              {bar.value} <span className="visually-hidden">{unit}</span>
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}
