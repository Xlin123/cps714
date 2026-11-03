import { ActionButton } from '../components/ActionButton';
import { checkIn } from './api';
import type { Loan } from './api';

/** Table of loans not yet returned, each with a check-in action. */
export function ActiveLoans({ loans, onReturned }: { loans: Loan[]; onReturned: () => void }) {
  if (loans.length === 0) return <p>No books are on loan.</p>;

  return (
    <div className="table-scroll">
      <table className="catalog">
        <thead>
          <tr>
            <th scope="col">Book</th>
            <th scope="col">Member</th>
            <th scope="col">Due</th>
            <th scope="col">
              <span className="visually-hidden">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {loans.map((loan) => (
            <tr key={loan.id}>
              <td>{loan.book_title}</td>
              <td>
                {loan.borrower_name}
                <br />
                <small>{loan.borrower_email}</small>
              </td>
              <td>{new Date(loan.due_at).toLocaleDateString()}</td>
              <td>
                <ActionButton
                  label="Check in"
                  busyLabel="Checking in…"
                  accessibleLabel={`Check in ${loan.book_title}`}
                  action={async () => {
                    await checkIn(loan.id);
                    onReturned();
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
