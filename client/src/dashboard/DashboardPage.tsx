import { Link } from 'react-router-dom';
import { useLoad } from '../hooks/useLoad';
import { formatCents } from '../lending/money';
import type { MemberLoan } from '../lending/api';
import { fetchDashboard } from './api';
import type { BookLoanCount, Dashboard } from './api';
import { StatTile } from './StatTile';

const DAY_MS = 24 * 60 * 60 * 1000;

/** Whole days a loan is past due, counting a started day, as fines do. */
const daysLate = (loan: MemberLoan, now: number) =>
  Math.max(1, Math.ceil((now - new Date(loan.due_at).getTime()) / DAY_MS));

/** Librarian overview: stock, lending, holds and what is overdue (LMS-19). */
export function DashboardPage() {
  const { state } = useLoad(async () => ({ data: await fetchDashboard(), at: Date.now() }), []);

  return (
    <div className="page wide">
      <h1>Dashboard</h1>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load the dashboard: {state.error}</p>
      )}
      {state.status === 'loaded' && <DashboardBody {...state.data} />}
    </div>
  );
}

function DashboardBody({ data, at }: { data: Dashboard; at: number }) {
  const { counts } = data;
  return (
    <>
      <div className="stat-row">
        <StatTile label="Overdue loans" value={counts.overdue} tone="attention" />
        <StatTile label="On loan" value={counts.on_loan} />
        <StatTile label="Holds waiting" value={counts.holds_waiting} />
        <StatTile label="Titles" value={counts.titles} />
        <StatTile label="Copies" value={counts.copies} />
        <StatTile label="Active members" value={counts.active_members} />
      </div>
      <h2>Overdue</h2>
      <OverdueTable loans={data.overdue.items} now={at} />
      {data.overdue.total > data.overdue.items.length && (
        <p>
          Showing the {data.overdue.items.length} longest overdue of {data.overdue.total}.
        </p>
      )}
      <h2>Most borrowed</h2>
      <MostBorrowed books={data.most_borrowed} />
    </>
  );
}

function OverdueTable({ loans, now }: { loans: MemberLoan[]; now: number }) {
  if (loans.length === 0) return <p>Nothing is overdue.</p>;
  return (
    <div className="table-scroll">
      <table className="catalog">
        <thead>
          <tr>
            <th scope="col">Book</th>
            <th scope="col">Member</th>
            <th scope="col">Due</th>
            <th scope="col" className="numeric">
              Days late
            </th>
            <th scope="col" className="numeric">
              Fine
            </th>
          </tr>
        </thead>
        <tbody>
          {loans.map((loan) => (
            <tr key={loan.id}>
              <td>{loan.book_title}</td>
              <td>
                <Link to={`/members/${loan.borrower_id}`}>{loan.borrower_name}</Link>
              </td>
              <td>{new Date(loan.due_at).toLocaleDateString()}</td>
              <td className="numeric overdue">{daysLate(loan, now)}</td>
              <td className="numeric">{formatCents(loan.fine_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MostBorrowed({ books }: { books: BookLoanCount[] }) {
  if (books.length === 0) return <p>No books have been lent yet.</p>;
  return (
    <div className="table-scroll">
      <table className="catalog">
        <thead>
          <tr>
            <th scope="col">Title</th>
            <th scope="col">Author</th>
            <th scope="col" className="numeric">
              Loans
            </th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => (
            <tr key={book.book_id}>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td className="numeric">{book.loans}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
