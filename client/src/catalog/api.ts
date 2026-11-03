import { getJson, jsonBody, send } from '../api/http';

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string;
  category: string;
  total_copies: number;
  available_copies: number;
  is_available: boolean;
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

export async function fetchBooks(offset: number): Promise<BookPage> {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
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
