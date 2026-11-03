import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { useLoad } from '../hooks/useLoad';
import { fetchBooks, PAGE_SIZE } from './api';
import type { Book } from './api';
import { RemoveBookButton } from './RemoveBookButton';

function availability(book: Book): string {
  if (!book.is_available) return 'Unavailable';
  return `${book.available_copies} of ${book.total_copies} available`;
}

export function CatalogPage() {
  const { user } = useAuth();
  const [offset, setOffset] = useState(0);
  const { state, reload } = useLoad(() => fetchBooks(offset), [offset]);

  if (state.status === 'failed') {
    return <div className="page error">Could not load the catalogue: {state.error}</div>;
  }
  if (state.status === 'loading') return <div className="page">Loading…</div>;

  const page = state.data;
  const canManageCatalog = user?.capabilities.includes('manage_catalog') ?? false;
  const hasPrevious = offset > 0;
  const hasNext = offset + PAGE_SIZE < page.total;

  return (
    <div className="page wide">
      <div className="page-heading">
        <h1>Catalogue</h1>
        {canManageCatalog && (
          <Link className="button" to="/staff#add-book">
            Add book
          </Link>
        )}
      </div>
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
                  {canManageCatalog && (
                    <th scope="col" className="action-column">
                      <span className="visually-hidden">Action</span>
                    </th>
                  )}
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
                    {canManageCatalog && (
                      <td>
                        <RemoveBookButton
                          bookId={book.id}
                          title={book.title}
                          onRemoved={() => {
                            if (page.items.length === 1 && offset > 0) {
                              setOffset(offset - PAGE_SIZE);
                            } else {
                              reload();
                            }
                          }}
                        />
                      </td>
                    )}
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
