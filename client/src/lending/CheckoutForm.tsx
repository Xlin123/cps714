import { useState } from 'react';
import { FieldError } from '../components/FieldError';
import { invalidProps } from '../components/invalidProps';
import { useSubmit } from '../hooks/useSubmit';
import type { Book } from '../catalog/api';
import { checkOut } from './api';
import type { Loan } from './api';

/** Lends one available book to a member by email. */
export function CheckoutForm({
  books,
  onCheckedOut,
}: {
  books: Book[];
  onCheckedOut: (loan: Loan) => void;
}) {
  const [bookId, setBookId] = useState('');
  const [email, setEmail] = useState('');
  const [lent, setLent] = useState<Loan | null>(null);
  const { error, fieldErrors, submitting, onSubmit } = useSubmit(async () => {
    setLent(null);
    const loan = await checkOut(Number(bookId), email);
    setLent(loan);
    setBookId('');
    setEmail('');
    onCheckedOut(loan);
  }, ['book_id', 'borrower_email']);

  return (
    <form className="narrow" onSubmit={onSubmit}>
      <label htmlFor="checkout-book">Book</label>
      <select
        id="checkout-book"
        value={bookId}
        onChange={(e) => setBookId(e.target.value)}
        required
        {...invalidProps('checkout-book', fieldErrors.book_id)}
      >
        <option value="">Choose a book…</option>
        {books.map((book) => (
          <option key={book.id} value={book.id} disabled={!book.is_available}>
            {book.title} ({book.available_copies} of {book.total_copies} available)
          </option>
        ))}
      </select>
      <FieldError inputId="checkout-book" message={fieldErrors.book_id} />
      <label htmlFor="checkout-email">Member email</label>
      <input
        id="checkout-email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        {...invalidProps('checkout-email', fieldErrors.borrower_email)}
      />
      <FieldError inputId="checkout-email" message={fieldErrors.borrower_email} />
      {error && <p className="error">{error}</p>}
      {lent && (
        <p role="status">
          Lent {lent.book_title} to {lent.borrower_name}, due{' '}
          {new Date(lent.due_at).toLocaleDateString()}.
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? 'Checking out…' : 'Check out'}
      </button>
    </form>
  );
}
