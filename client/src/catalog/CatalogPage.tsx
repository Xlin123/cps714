import { useState } from 'react';
import { useLoad } from '../hooks/useLoad';
import { fetchBooks, PAGE_SIZE } from './api';
import type { Book } from './api';

function availability(book: Book): string {
  if (!book.is_available) return 'Unavailable';
  return `${book.available_copies} of ${book.total_copies} available`;
}

export function CatalogPage() {
  const [offset, setOffset] = useState(0);
  const { state } = useLoad(() => fetchBooks(offset), [offset]);

  if (state.status === 'failed') {
    return <div className="page error">Could not load the catalogue: {state.error}</div>;
  }
  if (state.status === 'loading') return <div className="page">Loading…</div>;

  const page = state.data;
  const hasPrevious = offset > 0;
  const hasNext = offset + PAGE_SIZE < page.total;

  return (
    <div className="page wide">
      <h1>Catalogue</h1>
      {page.total === 0 ? (
        <p>No books in the catalogue yet.</p>
      ) : (
        <>
          <div className="table-scroll">
            <table className="catalog">
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Author</th>
                  <th scope="col" className="category">
                    Category
                  </th>
                  <th scope="col">Availability</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((book) => (
                  <tr key={book.id}>
                    <td>{book.title}</td>
                    <td>{book.author}</td>
                    <td className="category">{book.category}</td>
                    <td className={book.is_available ? undefined : 'unavailable'}>
                      {availability(book)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
