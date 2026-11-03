import { useLoad } from '../hooks/useLoad';
import { BOOK_PICKER_LIMIT, fetchBookChoices } from './api';
import { CheckoutForm } from './CheckoutForm';

/** Staff page for lending books. */
export function LendingPage() {
  const { state, reload } = useLoad(fetchBookChoices, []);

  return (
    <div className="page">
      <h1>Lending</h1>
      <h2>Check out</h2>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && <p className="error">Could not load books: {state.error}</p>}
      {state.status === 'loaded' && (
        <>
          <CheckoutForm books={state.data.items} onCheckedOut={reload} />
          {state.data.total > BOOK_PICKER_LIMIT && (
            <p>
              Showing the first {BOOK_PICKER_LIMIT} of {state.data.total} books.
            </p>
          )}
        </>
      )}
    </div>
  );
}
