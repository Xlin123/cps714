# Catalog decisions

## 2026-10-07: Browse catalog for Sprint 1 (LMS-5)

**Context.** LMS-5 (browse) is in Sprint 1, but adding books (LMS-6) is
Sprint 2, so the catalog would start empty.

**Options.**

| Option | Notes |
|---|---|
| Seed sample books behind the demo switch | Stays in sprint scope; real deployments start empty. |
| Pull LMS-6 forward | Real "add book" action, but brings a Sprint 2 story into Sprint 1. |
| `lms add-book` CLI | No UI for adding; another operator command to maintain. |

**Decision.** Seed 12 sample books when `LMS_DEMO_DATA=true` (renamed from
`LMS_DEMO_ACCOUNTS`). Seeding inserts only missing ISBNs, so restarts are
harmless. The sample ISBNs are not checked against real editions.

**Consequences.**

- `GET /api/books` is public and paginated: `limit` 1–100 (default 50),
  `offset` ≥ 0, ordered by title then id, with a `total` count.
- `available_copies` equals `total_copies` until loans exist (Sprint 3). It is
  computed in one function, `catalog.available_copies`, which loans will change.
- Search (LMS-4) is not included.

## 2026-11-02: Availability from loans

`available_copies` is now `total_copies` minus active loans; see
`docs/borrowing/decisions.md`.

## 2026-11-03: Removing books without losing loan history

**Context.** A `loan` row references its `book` row, so physically deleting a
book that has ever circulated would either violate the foreign key or erase
the context needed by borrowing history.

**Decision.** `DELETE /api/books/{id}` is a soft delete. It sets
`book.retired_at` instead of deleting the row. Catalog queries exclude retired
books, and checkout excludes them as well. A book with an active loan cannot be
retired until every copy has been checked in. Removing an already retired book
is idempotent. A retired ISBN remains reserved to avoid conflating it with a
new catalog record.

**Consequences.** Existing loan history remains readable. Startup applies a
small additive schema migration to add `retired_at` to existing databases.
Restoring a retired title or reusing its ISBN will require a later explicit
catalog operation.

## 2026-11-03: Editing catalog entries

`PATCH /api/books/{id}` accepts the complete editable representation of a
book: title, author, ISBN, genre/category, and total copies. The update is one
conditional statement, so a checkout racing an edit cannot leave total copies
below the active-loan count. Duplicate ISBNs retain the same refusal code as
book creation. Available copies are always derived from active loans and are
never edited directly.

## 2026-11-25: Searching the catalog (LMS-4; #5, #32–#34)

**Context.** #5 was closed in Sprint 2, but no search was built: the ticket
plan named `GET /api/books/search`, and its sub-tasks stayed open.

**Options.**

| Option | Notes |
|---|---|
| `q` on `GET /api/books` | Same paging and `total` as browsing; matches `GET /api/members?q=`. |
| Separate `GET /api/books/search` | What the ticket named; duplicates the listing query and paging. |
| SQLite FTS5 index | Ranked, word-aware matching; needs a virtual table kept in sync with `book`. |

**Decision.** `q` on `GET /api/books`. A book matches when its title, author,
ISBN or category contains `q`, ignoring case; that covers "title, author or
keyword". The match lives in `lms/search.py` (`contains_any`), now shared with
member search, so `%` and `_` match literally in both and both cap `q` at 100
characters. A blank `q` lists the whole catalog.

**Consequences.** Search is a `LIKE '%q%'` scan, fine for the demo-sized
catalog in the non-functional requirements (hundreds to low thousands of
books). FTS5 would be the next step for a larger collection.
