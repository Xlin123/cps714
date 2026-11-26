import { getJson, jsonBody, send } from '../api/http';

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string;
  category: string;
  total_copies: number;
  /** Copies on the shelf, including any reserved for members with holds. */
  available_copies: number;
  is_available: boolean;
  /** Members queued for this book. */
  on_hold: number;
}

export interface BookPage {
  items: Book[];
  total: number;
}

export interface BookInput {
  title: string;
  author: string;
  isbn: string;
  category: string;
  total_copies: number;
}

/** Matches the server default; the server rejects anything above 100. */
export const PAGE_SIZE = 50;

/** The server rejects longer search queries. */
export const SEARCH_MAX_LENGTH = 100;

/** One page of books whose title, author, ISBN or category contains `query`. */
export async function fetchBooks(query: string, offset: number): Promise<BookPage> {
  const params = new URLSearchParams({
    q: query,
    limit: String(PAGE_SIZE),
    offset: String(offset),
  });
  return getJson<BookPage>(`/api/books?${params}`);
}

/** Adds a book. The server only permits this for catalog managers. */
export async function createBook(input: BookInput): Promise<Book> {
  const res = await send(
    '/api/books',
    jsonBody('POST', input),
    'Please check the book details and try again.',
  );
  return res.json();
}

/** Updates a book. The server only permits this for catalog managers. */
export async function updateBook(bookId: number, input: BookInput): Promise<Book> {
  const res = await send(
    `/api/books/${bookId}`,
    jsonBody('PATCH', input),
    'Please check the book details and try again.',
  );
  return res.json();
}

/** Removes a book from the active catalog while preserving loan history. */
export async function deleteBook(bookId: number): Promise<void> {
  await send(`/api/books/${bookId}`, { method: 'DELETE' }, 'Could not remove the book.');
}
