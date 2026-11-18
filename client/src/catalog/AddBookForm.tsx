import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../api/http';
import { FieldError } from '../components/FieldError';
import { invalidProps } from '../components/invalidProps';
import { useSubmit } from '../hooks/useSubmit';
import { createBook } from './api';
import type { Book } from './api';

const EMPTY_FORM = {
  title: '',
  author: '',
  isbn: '',
  category: '',
  totalCopies: '1',
};

const BOOK_FIELDS = ['title', 'author', 'isbn', 'category', 'total_copies'] as const;

export function AddBookForm({ onAdded }: { onAdded?: () => void }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [added, setAdded] = useState<Book | null>(null);
  const { error, fieldErrors, submitting, onSubmit } = useSubmit(async () => {
    setAdded(null);
    const totalCopies = Number(form.totalCopies);
    if (!Number.isInteger(totalCopies) || totalCopies < 0) {
      throw new ApiError('', { total_copies: 'Must be a whole number of zero or more.' });
    }
    const book = await createBook({
      title: form.title,
      author: form.author,
      isbn: form.isbn,
      category: form.category,
      total_copies: totalCopies,
    });
    setForm(EMPTY_FORM);
    setAdded(book);
    onAdded?.();
  }, BOOK_FIELDS);

  function update(field: keyof typeof EMPTY_FORM, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <section id="add-book" className="add-book" aria-labelledby="add-book-title">
      <h2 id="add-book-title">Add a book</h2>
      <form onSubmit={onSubmit}>
        <label htmlFor="book-title">Title</label>
        <input
          id="book-title"
          maxLength={300}
          value={form.title}
          onChange={(event) => update('title', event.target.value)}
          required
          {...invalidProps('book-title', fieldErrors.title)}
        />
        <FieldError inputId="book-title" message={fieldErrors.title} />

        <label htmlFor="book-author">Author</label>
        <input
          id="book-author"
          maxLength={200}
          value={form.author}
          onChange={(event) => update('author', event.target.value)}
          required
          {...invalidProps('book-author', fieldErrors.author)}
        />
        <FieldError inputId="book-author" message={fieldErrors.author} />

        <label htmlFor="book-isbn">ISBN</label>
        <input
          id="book-isbn"
          maxLength={17}
          value={form.isbn}
          onChange={(event) => update('isbn', event.target.value)}
          required
          {...invalidProps('book-isbn', fieldErrors.isbn)}
        />
        <FieldError inputId="book-isbn" message={fieldErrors.isbn} />

        <label htmlFor="book-category">Category</label>
        <input
          id="book-category"
          maxLength={50}
          value={form.category}
          onChange={(event) => update('category', event.target.value)}
          required
          {...invalidProps('book-category', fieldErrors.category)}
        />
        <FieldError inputId="book-category" message={fieldErrors.category} />

        <label htmlFor="book-copies">Copies</label>
        <input
          id="book-copies"
          type="number"
          min={0}
          step={1}
          value={form.totalCopies}
          onChange={(event) => update('totalCopies', event.target.value)}
          required
          {...invalidProps('book-copies', fieldErrors.total_copies)}
        />
        <FieldError inputId="book-copies" message={fieldErrors.total_copies} />

        {error && <p className="error">{error}</p>}
        {added && (
          <p className="success" role="status">
            Added <strong>{added.title}</strong> to the catalogue.{' '}
            <Link to="/">View catalogue</Link>
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Adding book…' : 'Add book'}
        </button>
      </form>
    </section>
  );
}
