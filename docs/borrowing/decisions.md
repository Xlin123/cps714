# Borrowing decisions

## 2026-11-02: Checkout and check-in (LMS-8, LMS-9; #9, #10)

**Context.** Librarians lend books to members and take them back. The catalog
counts copies per book (`total_copies`) but has no table of physical copies.

**Decision.**

- A `loan` row records one lent copy: book, borrower, who lent it, when, when
  it is due, and (once back) when it was returned and who received it. A loan
  is active while `returned_at` is null.
- Availability is computed, not stored: `total_copies` minus active loans, in
  one grouped query for the catalog page.
- Checkout is a single `INSERT … SELECT` that inserts only while
  `active loans < total_copies`. SQLite runs the count and the insert under one
  write lock, so two librarians cannot both lend the last copy.
  `test_racing_checkouts_lend_the_last_copy_only_once` covers this; a naive
  check-then-insert fails it.
- Check-in is `UPDATE … WHERE id = ? AND returned_at IS NULL`, so a second
  check-in is refused (409) instead of overwriting the first.
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
  Books are retired rather than physically deleted so loan history remains
  valid; a book with active loans cannot be retired. Editing must not cut
  `total_copies` below active loans (the catalog clamps availability at zero
  if it happens).
- `GET /api/loans` lists active loans only. Member history (LMS-12, LMS-13)
  can add a filter.
- The `loan` table is new, so `create_all` adds it to existing databases. A
  change to an existing table would still need a reset or a migration tool.

## 2026-11-17: Member borrowing history (LMS-12)

**Context.** Members need to see their past and current loans. Every loan row
already keeps its checkout, due and return times, and retired books stay in
storage, so the history needs no new data.

**Decision.**

- `GET /api/loans/mine?status=all|active|returned&limit&offset` returns the
  signed-in member's loans, most recently checked out first (`status` defaults
  to `all`). The borrower is always the session user; there is no parameter
  that names another borrower.
- It is guarded by a new `view_own_loans` capability, held by members only.
  `REQUIREMENTS.md` §3 lists "view own loans" for every signed-in role, but
  staff accounts cannot borrow, so their history would always be empty.
- Loans of books retired since are included, with their titles.
- The client shows it at `/history` ("My loans"), with All / On loan /
  Returned filters. Unreturned loans past their due date show as overdue.

**Consequences.** Staff viewing a member's history (LMS-13) can reuse
`list_borrower_loans` behind `LEND_BOOKS`, once member lookup (E1) exists.

## 2026-11-17: Due-soon and overdue reminders

**Context.** Members want to be reminded before a loan falls due and once it
is overdue, so they return on time. Reminders are shown in the web app only:
no email, push or device notifications.

**Decision.**

- Reminders are computed when requested, from each loan's `due_at`; nothing is
  stored and no scheduled job runs. A loan is **overdue** from the instant it
  falls due and **due soon** within `LMS_DUE_SOON_DAYS` (default 3) before
  that. Returned loans never have one. The server decides, with its own
  clock, so a wrong clock on the member's computer cannot change the answer.
- `GET /api/loans/mine/reminders` lists the member's overdue and due-soon
  loans, soonest due first (so overdue ones lead). `GET /api/loans/mine` marks
  every loan with the same `reminder` field.
- The client shows a badge on the "My loans" nav link: a red count if
  anything is overdue, an amber count if loans are only due soon, and a green
  check when nothing needs attention (shown only after reminders load, so a
  failed request never claims "all clear"). It also shows a "Needs attention"
  list at the top of My loans, and "Due soon" / "Overdue" in the history
  table. Reminders refetch on
  each navigation; due dates change by the day, so there is no polling.
- A due-soon reminder can be dismissed; the dismissal is kept per user in the
  browser's `localStorage`. Overdue reminders cannot be dismissed: they stay
  until the book is returned. A dismissed due-soon loan that becomes overdue
  shows again.

**Consequences.** Dismissals do not follow a member to another browser;
storing them on the server would need a new table. A bell-and-dropdown
becomes worthwhile once there are other notification types (e.g. holds,
LMS-16).

## 2026-11-25: Overdue fines (LMS-17; #18, #67–#69)

**Context.** Late returns should accrue a fine at a configurable daily rate.
Collecting payment is a non-goal (`docs/REQUIREMENTS.md` section 2). #68 asked
for an admin-configurable rate.

**Options for the rate.**

| Option | Notes |
|---|---|
| `LMS_FINE_PER_DAY_CENTS` environment variable | Same as the loan period and due-soon window; changed by restarting. |
| Settings table and admin page | Changeable live by an admin; needs a new table, API and page. |

**Decision.**

- The rate is `LMS_FINE_PER_DAY_CENTS` (default 25, 0 turns fines off),
  chosen by the team. Money is whole cents, never floats.
- Fines are computed when requested, by `lms/fines.py`, from `due_at`,
  `returned_at` and the server clock; nothing is stored. Each started day
  past `due_at` costs the daily rate, so one second late is one day. A loan
  still out keeps accruing; a returned loan's fine stops at `returned_at`.
- Members see a fine per loan and their total on My loans
  (`GET /api/loans/mine/fines`); staff see the same per-loan fines and a
  total (`fines_cents`) on the member profile.
- `loans.py` and `members.py` depend on `fines.py`, never the reverse.

**Consequences.**

- Changing the rate rewrites every fine, past ones included, because fines
  are not stored. Freezing a fine at return would need a column on `loan`.
- There is no "paid" or "waived" state; that arrives with fine collection.
- The rate is not editable in the app (F2 "system settings" is not built).
