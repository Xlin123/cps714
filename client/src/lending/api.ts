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

/** Which loans a history shows: still out, back, or both. */
export type LoanStatus = 'all' | 'active' | 'returned';

export interface LoanPage {
  items: Loan[];
  total: number;
}

/** The server's page-size cap; lists on the lending page show at most this many. */
export const LENDING_LIST_LIMIT = 100;

export async function fetchBookChoices(): Promise<BookPage> {
  return getJson<BookPage>(`/api/books?limit=${LENDING_LIST_LIMIT}`);
}

export async function checkOut(bookId: number, borrowerEmail: string): Promise<Loan> {
  const res = await send(
    '/api/loans',
    jsonBody('POST', { book_id: bookId, borrower_email: borrowerEmail }),
    'Checkout failed.',
  );
  return res.json();
}

/** Loans not yet returned, soonest due first. */
export async function fetchActiveLoans(): Promise<LoanPage> {
  return getJson<LoanPage>(`/api/loans?limit=${LENDING_LIST_LIMIT}`);
}

export async function checkIn(loanId: number): Promise<Loan> {
  const res = await send(`/api/loans/${loanId}/return`, { method: 'POST' }, 'Check-in failed.');
  return res.json();
}

/** Page size for the borrowing history; the server rejects anything above 100. */
export const HISTORY_PAGE_SIZE = 50;

/** Why an active loan needs attention; the server decides, using its own clock. */
export type Reminder = 'overdue' | 'due_soon';

/** A loan as its borrower sees it. */
export interface MemberLoan extends Loan {
  reminder: Reminder | null;
}

export interface MemberLoanPage {
  items: MemberLoan[];
  total: number;
}

/** The signed-in member's own loans, most recently checked out first. */
export async function fetchMyLoans(status: LoanStatus, offset: number): Promise<MemberLoanPage> {
  const query = new URLSearchParams({
    status,
    limit: String(HISTORY_PAGE_SIZE),
    offset: String(offset),
  });
  return getJson<MemberLoanPage>(`/api/loans/mine?${query}`);
}

/** The signed-in member's overdue and due-soon loans, soonest due first. */
export async function fetchMyReminders(): Promise<MemberLoanPage> {
  return getJson<MemberLoanPage>('/api/loans/mine/reminders');
}
