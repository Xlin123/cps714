import { useLoad } from '../hooks/useLoad';
import { AddBookForm } from '../catalog/AddBookForm';
import { fetchActiveLoans, fetchBookChoices, LENDING_LIST_LIMIT } from './api';
import { ActiveLoans } from './ActiveLoans';
import { CheckoutForm } from './CheckoutForm';

function Truncated({ total, noun }: { total: number; noun: string }) {
  if (total <= LENDING_LIST_LIMIT) return null;
  return (
    <p>
      Showing the first {LENDING_LIST_LIMIT} of {total} {noun}.
    </p>
  );
}

/** Staff page for lending books and checking them back in. */
export function LendingPage() {
  const books = useLoad(fetchBookChoices, []);
  const loans = useLoad(fetchActiveLoans, []);
  // Either action changes both availability and the loan list.
  const reloadAll = () => {
    books.reload();
    loans.reload();
  };

  return (
    <div className="page wide">
      <h1>Lending</h1>
      <AddBookForm onAdded={books.reload} />
      <h2>Check out</h2>
      {books.state.status === 'loading' && <p>Loading…</p>}
      {books.state.status === 'failed' && (
        <p className="error">Could not load books: {books.state.error}</p>
      )}
      {books.state.status === 'loaded' && (
        <>
          <CheckoutForm books={books.state.data.items} onCheckedOut={reloadAll} />
          <Truncated total={books.state.data.total} noun="books" />
        </>
      )}
      <h2>On loan</h2>
      {loans.state.status === 'loading' && <p>Loading…</p>}
      {loans.state.status === 'failed' && (
        <p className="error">Could not load loans: {loans.state.error}</p>
      )}
      {loans.state.status === 'loaded' && (
        <>
          <ActiveLoans loans={loans.state.data.items} onReturned={reloadAll} />
          <Truncated total={loans.state.data.total} noun="loans" />
        </>
      )}
    </div>
  );
}
