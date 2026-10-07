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

/** Matches the server default; the server rejects anything above 100. */
export const PAGE_SIZE = 50;

export async function fetchBooks(offset: number): Promise<BookPage> {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
  const res = await fetch(`/api/books?${params}`);
  if (!res.ok) throw new Error(`GET /api/books failed with ${res.status}`);
  return res.json();
}
