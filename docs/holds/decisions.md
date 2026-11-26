# Holds decisions

## 2026-11-25: Members queue for checked-out books (LMS-16; #17, #64–#66)

**Context.** A member wants to reserve a book whose copies are all out and be
told when it comes back. The tickets named `POST /api/books/:id/hold` and
"queue/notify logic". Notifications are in-app only (see
`docs/borrowing/decisions.md`, due-soon reminders).

**Options for what a hold guarantees.**

| Option | Notes |
|---|---|
| Notice only | Shows "a copy is back"; anyone can still borrow it first. A hold promises nothing. |
| Reserve the returned copy for the first in line | Checkout enforces the queue; the holder's notice is reliable. |
| Auto-lend to the first in line on return | No pickup step, but the member is charged a loan (and fines) for a book they have not collected. |

**Decision.** Reserve.

- A `hold` table: `book_id`, `member_id`, `placed_at`, and `fulfilled_at` /
  `cancelled_at` instead of deleting rows, so history stays. A partial unique
  index allows one active hold per member and book. Queue order is the row
  id.
- A member may place a hold only when no copy is free for them: active
  loans plus active holds already cover every copy. They may not hold a book
  they have on loan.
- Checkout lends only while `active loans + holds ahead of the borrower <
  total copies`, inside the same `INSERT … SELECT` that already makes
  checkout race-safe. A borrower with no hold has every hold ahead of them.
  The loan fulfils the borrower's own hold in the same transaction. A refused
  checkout of a reserved copy is `LOAN_RESERVED_FOR_HOLD`.
- A hold is ready when its position is at most the free shelf copies (total
  copies minus active loans). Ready holds show as "Ready for pickup" notices
  in the Holds section of My loans. Nothing is stored or scheduled, like
  reminders.
- Cancelling a ready hold passes the copy to the next in line. Retiring a
  book cancels its holds.
- New capability `place_holds`, members only, since only members borrow.
- The loan and hold counts live in `lms/availability.py`; `loans.py` and
  `catalog.py` depend on `holds.py`, never the reverse.

**Consequences.**

- A ready hold has no pickup deadline: an uncollected hold blocks the copy
  until the member borrows it or cancels. An expiry would need a scheduled
  job or a check at read time.
- The "My loans" nav badge counts loan reminders only, so a ready hold is
  seen on My loans, not in the nav bar.
- `available_copies` still counts reserved shelf copies, so the lending page
  lists them; the catalogue shows "Reserved for holds" instead of a count.
