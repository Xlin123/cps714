import { useState } from 'react';
import { useLoad } from '../hooks/useLoad';
import { fetchMyLoans, HISTORY_PAGE_SIZE } from './api';
import type { LoanStatus, MemberLoan } from './api';
import { ReminderNotices } from './ReminderNotices';

const FILTERS: { status: LoanStatus; label: string; empty: string }[] = [
  { status: 'all', label: 'All', empty: "You haven't borrowed any books yet." },
  { status: 'active', label: 'On loan', empty: 'You have no books on loan.' },
  { status: 'returned', label: 'Returned', empty: "You haven't returned any books yet." },
];

const formatDate = (iso: string) => new Date(iso).toLocaleDateString();

function ReturnedCell({ loan }: { loan: MemberLoan }) {
  if (loan.returned_at) return <td>{formatDate(loan.returned_at)}</td>;
  if (loan.reminder === 'overdue') return <td className="overdue">Overdue</td>;
  if (loan.reminder === 'due_soon') return <td className="due-soon">Due soon</td>;
  return <td>On loan</td>;
}

/** The signed-in member's borrowing history (LMS-12). */
export function HistoryPage() {
  const [status, setStatus] = useState<LoanStatus>('all');
  const [offset, setOffset] = useState(0);
  const { state } = useLoad(() => fetchMyLoans(status, offset), [status, offset]);
  const filter = FILTERS.find((f) => f.status === status) ?? FILTERS[0];

  const chooseStatus = (next: LoanStatus) => {
    setStatus(next);
    setOffset(0);
  };

  return (
    <div className="page wide">
      <h1>My loans</h1>
      <ReminderNotices />
      <div className="status-filter" role="group" aria-label="Show loans">
        {FILTERS.map((f) => (
          <button
            key={f.status}
            aria-pressed={f.status === status}
            onClick={() => chooseStatus(f.status)}
          >
            {f.label}
          </button>
        ))}
      </div>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load your loans: {state.error}</p>
      )}
      {state.status === 'loaded' &&
        (state.data.total === 0 ? (
          <p>{filter.empty}</p>
        ) : (
          <LoanHistory page={state.data} offset={offset} onPage={setOffset} />
        ))}
    </div>
  );
}

function LoanHistory({
  page,
  offset,
  onPage,
}: {
  page: { items: MemberLoan[]; total: number };
  offset: number;
  onPage: (offset: number) => void;
}) {
  const hasPrevious = offset > 0;
  const hasNext = offset + HISTORY_PAGE_SIZE < page.total;

  return (
    <>
      <div className="table-scroll">
        <table className="catalog">
          <thead>
            <tr>
              <th scope="col">Book</th>
              <th scope="col">Borrowed</th>
              <th scope="col">Due</th>
              <th scope="col">Returned</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((loan) => (
              <tr key={loan.id}>
                <td>{loan.book_title}</td>
                <td>{formatDate(loan.checked_out_at)}</td>
                <td>{formatDate(loan.due_at)}</td>
                <ReturnedCell loan={loan} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(hasPrevious || hasNext) && (
        <div className="pager">
          <button disabled={!hasPrevious} onClick={() => onPage(offset - HISTORY_PAGE_SIZE)}>
            Previous
          </button>
          <span>
            {offset + 1}–{offset + page.items.length} of {page.total}
          </span>
          <button disabled={!hasNext} onClick={() => onPage(offset + HISTORY_PAGE_SIZE)}>
            Next
          </button>
        </div>
      )}
    </>
  );
}
