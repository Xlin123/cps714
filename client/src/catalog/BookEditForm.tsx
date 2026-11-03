import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { deleteBook, updateBook } from './api';
import type { Book, BookInput } from './api';

// Trash-2 icon from Lucide (https://lucide.dev/icons/trash-2), ISC licensed.
function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3 6h18" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" x2="10" y1="11" y2="17" />
      <line x1="14" x2="14" y1="11" y2="17" />
    </svg>
  );
}

function toForm(book: Book): BookInput {
  return {
    title: book.title,
    author: book.author,
    isbn: book.isbn,
    category: book.category,
    total_copies: book.total_copies,
  };
}

export function BookEditForm({
  book,
  onSaved,
  onRemoved,
  onCancel,
}: {
  book: Book;
  onSaved: (book: Book) => void;
  onRemoved: () => void;
  onCancel: () => void;
}) {
  const panel = useRef<HTMLElement>(null);
  const [form, setForm] = useState(() => toForm(book));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    panel.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, []);

  function update(field: keyof BookInput, value: string | number) {
    setError(null);
    setSuccess(null);
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!Number.isInteger(form.total_copies) || form.total_copies < 0) {
      setError('Copies must be a whole number of zero or more.');
      return;
    }

    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const updated = await updateBook(book.id, form);
      setForm(toForm(updated));
      setSuccess('Changes saved.');
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Remove "${book.title}" from the catalogue?`)) return;

    setError(null);
    setSuccess(null);
    setRemoving(true);
    try {
      await deleteBook(book.id);
      onRemoved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRemoving(false);
    }
  }

  const busy = saving || removing;

  return (
    <section
      ref={panel}
      id={`edit-book-${book.id}`}
      className="book-edit-panel"
      aria-labelledby={`edit-book-title-${book.id}`}
    >
      <div className="edit-panel-heading">
        <h2 id={`edit-book-title-${book.id}`}>Edit book</h2>
        <button type="button" onClick={onCancel} disabled={busy}>
          Close
        </button>
      </div>
      <p>
        {book.available_copies} of {book.total_copies} copies currently available. Total copies
        cannot be set below the number currently on loan.
      </p>
      <form onSubmit={save}>
        <label htmlFor="edit-book-title">Title</label>
        <input
          id="edit-book-title"
          maxLength={300}
          value={form.title}
          onChange={(event) => update('title', event.target.value)}
          autoFocus
          required
        />

        <label htmlFor="edit-book-author">Author</label>
        <input
          id="edit-book-author"
          maxLength={200}
          value={form.author}
          onChange={(event) => update('author', event.target.value)}
          required
        />

        <label htmlFor="edit-book-isbn">ISBN</label>
        <input
          id="edit-book-isbn"
          maxLength={17}
          value={form.isbn}
          onChange={(event) => update('isbn', event.target.value)}
          required
        />

        <label htmlFor="edit-book-category">Genre</label>
        <input
          id="edit-book-category"
          maxLength={50}
          value={form.category}
          onChange={(event) => update('category', event.target.value)}
          required
        />

        <label htmlFor="edit-book-copies">Total copies</label>
        <input
          id="edit-book-copies"
          type="number"
          min={0}
          step={1}
          value={form.total_copies}
          onChange={(event) => update('total_copies', Number(event.target.value))}
          required
        />

        {error && <p className="error">{error}</p>}
        {success && (
          <p className="success" role="status">
            {success}
          </p>
        )}
        <div className="edit-panel-actions">
          <button type="submit" disabled={busy}>
            {saving ? 'Saving...' : 'Save changes'}
          </button>
          <button
            type="button"
            className="remove-book"
            onClick={remove}
            disabled={busy}
            aria-label={
              removing ? `Removing ${book.title}` : `Remove ${book.title} from catalogue`
            }
            title="Remove from catalogue"
          >
            <TrashIcon />
          </button>
          <button type="button" className="cancel-edit" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
}
