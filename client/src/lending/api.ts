import { getJson, jsonBody, send } from '../api/http';
import type { BookPage } from '../catalog/api';

export interface Loan {
  id: number;
  book_id: number;
  book_title: string;
  borrower_id: string;
  borrower_name: string;
  borrower_email: string;
  checked_out_at: string;
  due_at: string;
  returned_at: string | null;
}

/** The server's page-size cap; the picker lists at most this many books. */
export const BOOK_PICKER_LIMIT = 100;

export async function fetchBookChoices(): Promise<BookPage> {
  return getJson<BookPage>(`/api/books?limit=${BOOK_PICKER_LIMIT}`);
}

export async function checkOut(bookId: number, borrowerEmail: string): Promise<Loan> {
  const res = await send(
    '/api/loans',
    jsonBody('POST', { book_id: bookId, borrower_email: borrowerEmail }),
    'Checkout failed.',
  );
  return res.json();
}
