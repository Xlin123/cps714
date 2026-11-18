import { HISTORY_PAGE_SIZE } from './api';
import type { LoanStatus, MemberLoan, MemberLoanPage } from './api';

const STATUS_LABELS: { status: LoanStatus; label: string }[] = [
  { status: 'all', label: 'All' },
  { status: 'active', label: 'On loan' },
  { status: 'returned', label: 'Returned' },
];

const formatDate = (iso: string) => new Date(iso).toLocaleDateString();

/** Buttons choosing which loans a history shows. */
export function LoanStatusFilter({
  status,
  onChange,
}: {
  status: LoanStatus;
  onChange: (status: LoanStatus) => void;
}) {
  return (
    <div className="status-filter" role="group" aria-label="Show loans">
      {STATUS_LABELS.map((f) => (
        <button key={f.status} aria-pressed={f.status === status} onClick={() => onChange(f.status)}>
          {f.label}
        </button>
      ))}
    </div>
  );
}

function ReturnedCell({ loan }: { loan: MemberLoan }) {
  if (loan.returned_at) return <td>{formatDate(loan.returned_at)}</td>;
  if (loan.reminder === 'overdue') return <td className="overdue">Overdue</td>;
  if (loan.reminder === 'due_soon') return <td className="due-soon">Due soon</td>;
  return <td>On loan</td>;
}

/**
 * One page of a borrower's loans with a pager. Pages are `HISTORY_PAGE_SIZE`
 * long; `onPage` receives the new offset.
 *
 *     <LoanTable page={state.data} offset={offset} onPage={setOffset} />
 */
export function LoanTable({
  page,
  offset,
  onPage,
}: {
  page: MemberLoanPage;
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
