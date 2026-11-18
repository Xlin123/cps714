# Member lookup decisions

## 2026-11-18: Librarians view a member's profile and loans (LMS-13; #14, #57, #58)

**Context.** Librarians need to look up a member and see their active and past
loans to help them. The ticket named `GET /api/members/:id`, but finding the
member first needs a search, and a long history needs paging.

**Decision.**

- A new capability, `view_members`, granted to librarian and admin. Today it
  goes to the same roles as `lend_books`, but looking people up is a separate
  permission from lending and may diverge (e.g. a read-only helpdesk role).
- Three routes under `/api/members` in `lms/members.py`:
  - `GET /api/members?q=` searches name and email with a case-insensitive
    substring match. `%` and `_` in `q` are escaped so they match literally.
    `q` is capped at 100 characters. Deactivated members are included so their
    history stays reachable.
  - `GET /api/members/{id}` returns the member with loan counts.
  - `GET /api/members/{id}/loans` reuses `list_borrower_loans` from
    `lms/loans.py`, so staff see exactly the rows (and reminders) the member
    sees on `/api/loans/mine`.
- Only `role == member` accounts are visible. A staff id answers 404
  `MEMBER_NOT_FOUND`, the same as an unknown id, so the route cannot be used to
  enumerate staff accounts.
- `members.py` depends on `loans.py`, never the reverse.

**Consequences.**

- The client's loan table and status filter moved to
  `client/src/lending/LoanTable.tsx`, shared by My loans and the member profile.
- The search is a `LIKE '%q%'` scan of the user table. Fine at library scale;
  an index or full-text search would be needed for a large membership.
