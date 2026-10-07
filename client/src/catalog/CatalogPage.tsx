import { useEffect, useState } from 'react';
import { fetchBooks, PAGE_SIZE } from './api';
import type { Book, BookPage } from './api';

function availability(book: Book): string {
  if (!book.is_available) return 'Unavailable';
  return `${book.available_copies} of ${book.total_copies} available`;
}

export function CatalogPage() {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<BookPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    fetchBooks(offset)
      .then((found) => {
        if (!isCancelled) setPage(found);
      })
      .catch((err: unknown) => {
        if (!isCancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      isCancelled = true;
    };
  }, [offset]);

  if (error) return <div className="page error">Could not load the catalogue: {error}</div>;
  if (!page) return <div className="page">Loading…</div>;

  const hasPrevious = offset > 0;
  const hasNext = offset + PAGE_SIZE < page.total;

  return (
    <div className="page wide">
      <h1>Catalogue</h1>
      {page.total === 0 ? (
        <p>No books in the catalogue yet.</p>
      ) : (
        <>
          <table className="catalog">
            <thead>
              <tr>
                <th scope="col">Title</th>
                <th scope="col">Author</th>
                <th scope="col">Category</th>
                <th scope="col">Availability</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((book) => (
                <tr key={book.id}>
                  <td>{book.title}</td>
                  <td>{book.author}</td>
                  <td>{book.category}</td>
                  <td className={book.is_available ? undefined : 'unavailable'}>
                    {availability(book)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(hasPrevious || hasNext) && (
            <div className="pager">
              <button disabled={!hasPrevious} onClick={() => setOffset(offset - PAGE_SIZE)}>
                Previous
              </button>
              <span>
                {offset + 1}–{offset + page.items.length} of {page.total}
              </span>
              <button disabled={!hasNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
