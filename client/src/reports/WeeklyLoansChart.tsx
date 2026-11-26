import { useState } from 'react';
import type { WeekCount } from './api';

const WIDTH = 640;
const HEIGHT = 240;
const MARGIN = { top: 12, right: 8, bottom: 28, left: 36 };
const PLOT_WIDTH = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_HEIGHT = HEIGHT - MARGIN.top - MARGIN.bottom;
const MAX_BAR = 24;
const RADIUS = 4;
/** Room each x label needs, so labels are thinned rather than overlapped. */
const LABEL_SPACING = 64;

const weekLabel = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });

/** A clean axis top (1, 2 or 5 × 10ⁿ) at or above `max`, and its tick step. */
function niceScale(max: number): { top: number; step: number } {
  if (max <= 0) return { top: 4, step: 1 };
  const rough = max / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? rough;
  return { top: Math.ceil(max / step) * step, step };
}

/** A column rounded at the top only, so it reads as growing from the baseline. */
function columnPath(x: number, y: number, width: number, height: number): string {
  const r = Math.min(RADIUS, width / 2, height);
  const bottom = y + height;
  return [
    `M${x},${bottom}`,
    `V${y + r}`,
    `Q${x},${y} ${x + r},${y}`,
    `H${x + width - r}`,
    `Q${x + width},${y} ${x + width},${y + r}`,
    `V${bottom}`,
    'Z',
  ].join(' ');
}

/**
 * Loans checked out per week as columns, with a tooltip on hover and focus.
 * The same numbers are in the table view below it.
 *
 *     <WeeklyLoansChart weeks={report.loans_per_week} />
 */
export function WeeklyLoansChart({ weeks }: { weeks: WeekCount[] }) {
  const [active, setActive] = useState<number | null>(null);
  const { top, step } = niceScale(Math.max(...weeks.map((w) => w.loans)));
  const band = PLOT_WIDTH / weeks.length;
  const barWidth = Math.min(MAX_BAR, band * 0.6);
  const labelEvery = Math.max(1, Math.ceil(LABEL_SPACING / band));
  const y = (value: number) => MARGIN.top + PLOT_HEIGHT - (value / top) * PLOT_HEIGHT;
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);
  const shown = active === null ? null : weeks[active];

  return (
    <div className="chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Loans per week, ${weeks.length} weeks`}
      >
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              className="chart-grid"
              x1={MARGIN.left}
              x2={WIDTH - MARGIN.right}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text
              className="chart-tick"
              x={MARGIN.left - 6}
              y={y(tick)}
              dy="0.32em"
              textAnchor="end"
            >
              {tick}
            </text>
          </g>
        ))}
        {weeks.map((week, index) => {
          const bandX = MARGIN.left + index * band;
          const height = (week.loans / top) * PLOT_HEIGHT;
          return (
            <g
              key={week.week_start}
              tabIndex={0}
              className={active === index ? 'chart-column active' : 'chart-column'}
              aria-label={`Week of ${weekLabel(week.week_start)}: ${week.loans} loans`}
              onPointerEnter={() => setActive(index)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(index)}
              onBlur={() => setActive(null)}
            >
              {/* The whole band is the hit target, not just the painted column. */}
              <rect
                className="chart-hit"
                x={bandX}
                y={MARGIN.top}
                width={band}
                height={PLOT_HEIGHT}
              />
              {week.loans > 0 && (
                <path
                  className="chart-mark"
                  d={columnPath(bandX + (band - barWidth) / 2, y(week.loans), barWidth, height)}
                />
              )}
              {index % labelEvery === 0 && (
                <text
                  className="chart-tick"
                  x={bandX + band / 2}
                  y={HEIGHT - MARGIN.bottom + 18}
                  textAnchor="middle"
                >
                  {weekLabel(week.week_start)}
                </text>
              )}
            </g>
          );
        })}
        <line
          className="chart-axis"
          x1={MARGIN.left}
          x2={WIDTH - MARGIN.right}
          y1={y(0)}
          y2={y(0)}
        />
      </svg>
      {shown && active !== null && (
        <div
          className="chart-tooltip"
          style={{ left: `${((MARGIN.left + (active + 0.5) * band) / WIDTH) * 100}%` }}
          role="status"
        >
          <strong>{shown.loans}</strong> {shown.loans === 1 ? 'loan' : 'loans'}
          <span>Week of {weekLabel(shown.week_start)}</span>
        </div>
      )}
    </div>
  );
}

/** The chart's numbers as a table, for screen readers and exact values. */
export function WeeklyLoansTable({ weeks }: { weeks: WeekCount[] }) {
  return (
    <details className="chart-table">
      <summary>Show as table</summary>
      <table className="catalog">
        <thead>
          <tr>
            <th scope="col">Week of</th>
            <th scope="col" className="numeric">
              Loans
            </th>
          </tr>
        </thead>
        <tbody>
          {weeks.map((week) => (
            <tr key={week.week_start}>
              <td>{weekLabel(week.week_start)}</td>
              <td className="numeric">{week.loans}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
