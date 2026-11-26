import { Fragment, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { ActionButton } from '../components/ActionButton';
import { placeHold } from '../holds/api';
import { useLoad } from '../hooks/useLoad';
import { BookEditForm } from './BookEditForm';
import { EditBookButton } from './EditBookButton';
import { fetchBooks, PAGE_SIZE, SEARCH_MAX_LENGTH } from './api';
import type { Book } from './api';

/** True when every shelf copy is out or reserved, so a member must queue. */
const mustQueue = (book: Book) => book.available_copies <= book.on_hold;

function availability(book: Book): string {
  const queue = book.on_hold > 0 ? ` · ${book.on_hold} on hold` : '';
  if (!book.is_available) return `Unavailable${queue}`;
  if (mustQueue(book)) return `Reserved for holds${queue}`;
  return `${book.available_copies} of ${book.total_copies} available${queue}`;
}

export function CatalogPage() {
  const { user } = useAuth();
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [editingBook, setEditingBook] = useState<Book | null>(null);
  const [heldTitle, setHeldTitle] = useState<string | null>(null);
  const { state, reload } = useLoad(() => fetchBooks(query, offset), [query, offset]);

  function onSearch(event: FormEvent) {
    event.preventDefault();
    setQuery(draft.trim());
    setOffset(0);
    setEditingBook(null);
  }

  if (state.status === 'failed') {
    return <div className="page error">Could not load the catalogue: {state.error}</div>;
  }
  if (state.status === 'loading') return <div className="page">Loading…</div>;

  const page = state.data;
  const canManageCatalog = user?.capabilities.includes('manage_catalog') ?? false;
  const canPlaceHolds = user?.capabilities.includes('place_holds') ?? false;
  const hasActionColumn = canManageCatalog || canPlaceHolds;
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
      <form className="search-form" role="search" onSubmit={onSearch}>
        <label htmlFor="catalog-query">Title, author or keyword</label>
        <input
          id="catalog-query"
          type="search"
          maxLength={SEARCH_MAX_LENGTH}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit">Search</button>
      </form>
      {heldTitle && (
        <p role="status">
          Hold placed on {heldTitle}. Track it under <Link to="/history">My loans</Link>.
        </p>
      )}
      {page.total === 0 ? (
        <p>{query ? `No books match “${query}”.` : 'No books in the catalogue yet.'}</p>
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
                  {hasActionColumn && (
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
                      {canPlaceHolds && (
                        <td>
                          {mustQueue(book) && (
                            <ActionButton
                              label="Place hold"
                              busyLabel="Placing…"
                              accessibleLabel={`Place hold on ${book.title}`}
                              action={async () => {
                                await placeHold(book.id);
                                setHeldTitle(book.title);
                                reload();
                              }}
                            />
                          )}
                        </td>
                      )}
                    </tr>
                    {editingBook?.id === book.id && (
                      <tr className="edit-row">
                        <td colSpan={hasActionColumn ? 5 : 4}>
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
