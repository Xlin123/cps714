import { Fragment, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { useLoad } from '../hooks/useLoad';
import { BookEditForm } from './BookEditForm';
import { EditBookButton } from './EditBookButton';
import { fetchBooks, PAGE_SIZE } from './api';
import type { Book } from './api';

function availability(book: Book): string {
  if (!book.is_available) return 'Unavailable';
  return `${book.available_copies} of ${book.total_copies} available`;
}

export function CatalogPage() {
  const { user } = useAuth();
  const [offset, setOffset] = useState(0);
  const [editingBook, setEditingBook] = useState<Book | null>(null);
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
                  <Fragment key={book.id}>
                    <tr>
                      <td>{book.title}</td>
                      <td>{book.author}</td>
                      <td className="category">{book.category}</td>
                      <td className={book.is_available ? undefined : 'unavailable'}>
                        {availability(book)}
                      </td>
                      {canManageCatalog && (
                        <td>
                          <EditBookButton
                            title={book.title}
                            onEdit={() => setEditingBook(book)}
                          />
                        </td>
                      )}
                    </tr>
                    {editingBook?.id === book.id && (
                      <tr className="edit-row">
                        <td colSpan={canManageCatalog ? 5 : 4}>
                          <BookEditForm
                            key={editingBook.id}
                            book={editingBook}
                            onSaved={(updated) => {
                              setEditingBook(updated);
                              reload();
                            }}
                            onRemoved={() => {
                              setEditingBook(null);
                              if (page.items.length === 1 && offset > 0) {
                                setOffset(offset - PAGE_SIZE);
                              } else {
                                reload();
                              }
                            }}
                            onCancel={() => setEditingBook(null)}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
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
