# Borrowing decisions

## 2026-11-02: Checkout (LMS-8; #9)

**Context.** Librarians lend books to members. The catalog
counts copies per book (`total_copies`) but has no table of physical copies.

**Decision.**

- A `loan` row records one lent copy: book, borrower, who lent it, when, when
  it is due. Columns for the return (`returned_at`, `returned_to_id`) are
  there for check-in (LMS-9). A loan is active while `returned_at` is null.
- Availability is computed, not stored: `total_copies` minus active loans, in
  one grouped query for the catalog page.
- Checkout is a single `INSERT … SELECT` that inserts only while
  `active loans < total_copies`. SQLite runs the count and the insert under one
  write lock, so two librarians cannot both lend the last copy.
  `test_racing_checkouts_lend_the_last_copy_only_once` covers this; a naive
  check-then-insert fails it.
- Only active `member` accounts can borrow. Staff and deactivated accounts get
  `LOAN_BORROWER_NOT_FOUND`.
- A member holds at most one active loan per book (partial unique index),
  reported as `LOAN_ALREADY_BORROWED`.
- The loan period comes from `LMS_LOAN_PERIOD_DAYS` (default 14). F2 (admin
  settings) can move it into the database later.
- Refusals are sent as stable codes in `detail` (`LOAN_*`); the client maps
  them to text in `client/src/api/http.ts`.

**Consequences.**

- SQLite now enforces foreign keys (`PRAGMA foreign_keys=ON` per connection).
  A book with loan records cannot be deleted; LMS-7 (delete book) must handle
  that, and editing must not cut `total_copies` below active loans (the
  catalog clamps availability at zero if it happens).
- The `loan` table is new, so `create_all` adds it to existing databases. A
  change to an existing table would still need a reset or a migration tool.
