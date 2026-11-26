import { useState } from 'react';
import { StatTile } from '../dashboard/StatTile';
import { useLoad } from '../hooks/useLoad';
import { BarList } from './BarList';
import { fetchReport, WEEK_PRESETS } from './api';
import type { Report } from './api';
import { WeeklyLoansChart, WeeklyLoansTable } from './WeeklyLoansChart';

/** Admin usage reports: loans over time and what is popular (LMS-20). */
export function ReportsPage() {
  const [weeks, setWeeks] = useState<number>(12);
  const { state } = useLoad(() => fetchReport(weeks), [weeks]);

  return (
    <div className="page wide">
      <h1>Reports</h1>
      <div className="status-filter" role="group" aria-label="Report period">
        {WEEK_PRESETS.map((preset) => (
          <button key={preset} aria-pressed={preset === weeks} onClick={() => setWeeks(preset)}>
            Last {preset} weeks
          </button>
        ))}
      </div>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load the report: {state.error}</p>
      )}
      {state.status === 'loaded' && <ReportBody report={state.data} />}
    </div>
  );
}

function ReportBody({ report }: { report: Report }) {
  const since = new Date(report.period_start).toLocaleDateString(undefined, { timeZone: 'UTC' });
  return (
    <>
      <p>
        From the week of {since} to today. Weeks start on Monday (UTC).
      </p>
      <div className="stat-row">
        <StatTile label="Loans" value={report.totals.loans} />
        <StatTile label="Borrowers" value={report.totals.borrowers} />
      </div>
      <h2>Loans per week</h2>
      <WeeklyLoansChart weeks={report.loans_per_week} />
      <WeeklyLoansTable weeks={report.loans_per_week} />
      <div className="report-columns">
        <section aria-labelledby="titles-heading">
          <h2 id="titles-heading">Popular titles</h2>
          {report.popular_titles.length === 0 ? (
            <p>No loans in this period.</p>
          ) : (
            <BarList
              unit="loans"
              bars={report.popular_titles.map((title) => ({
                key: title.book_id,
                label: title.title,
                detail: title.author,
                value: title.loans,
              }))}
            />
          )}
        </section>
        <section aria-labelledby="categories-heading">
          <h2 id="categories-heading">Popular categories</h2>
          {report.popular_categories.length === 0 ? (
            <p>No loans in this period.</p>
          ) : (
            <BarList
              unit="loans"
              bars={report.popular_categories.map((category) => ({
                key: category.category,
                label: category.category,
                value: category.loans,
              }))}
            />
          )}
        </section>
      </div>
    </>
  );
}
