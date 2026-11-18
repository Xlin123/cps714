import type { MemberLoan } from './api';
import { useReminders } from './useReminders';

const DAY_MS = 24 * 60 * 60 * 1000;

/** Whole calendar days from `from` to `to` in the viewer's time zone. */
function calendarDaysBetween(from: number, to: number): number {
  const start = new Date(from).setHours(0, 0, 0, 0);
  const end = new Date(to).setHours(0, 0, 0, 0);
  // Rounding absorbs the 23- or 25-hour days around daylight-saving changes.
  return Math.round((end - start) / DAY_MS);
}

const shortDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

function describe(loan: MemberLoan, now: number): string {
  const due = new Date(loan.due_at).getTime();
  if (loan.reminder === 'overdue') {
    const late = calendarDaysBetween(due, now);
    if (late <= 0) return `was due today (${shortDate(loan.due_at)})`;
    return `is ${late} ${late === 1 ? 'day' : 'days'} overdue (due ${shortDate(loan.due_at)})`;
  }
  const left = calendarDaysBetween(now, due);
  if (left <= 0) return `is due today (${shortDate(loan.due_at)})`;
  if (left === 1) return `is due tomorrow (${shortDate(loan.due_at)})`;
  return `is due in ${left} days (${shortDate(loan.due_at)})`;
}

/** Overdue and due-soon loans at the top of My loans. Renders nothing when none. */
export function ReminderNotices() {
  const { reminders, loadedAt, dismiss } = useReminders();
  if (reminders.length === 0) return null;

  return (
    <section aria-labelledby="reminders-heading">
      <h2 id="reminders-heading">Needs attention</h2>
      <ul className="notices">
        {reminders.map((loan) => (
          <li
            key={loan.id}
            className={loan.reminder === 'overdue' ? 'notice overdue' : 'notice due-soon'}
          >
            <span>
              <strong>{loan.book_title}</strong> {describe(loan, loadedAt)}
            </span>
            {loan.reminder === 'due_soon' && (
              <button
                aria-label={`Dismiss reminder for ${loan.book_title}`}
                onClick={() => dismiss(loan.id)}
              >
                Dismiss
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
