# Dashboard decisions

## 2026-11-25: Librarian dashboard (LMS-19; #20, #73, #74)

**Context.** Librarians want key stats and an overdue list in one place. The
tickets named `GET /api/dashboard/stats` and "stat widgets".

**Decision.**

- One `GET /api/dashboard`, so the page makes one request and every number
  comes from the same moment.
- A new capability, `view_dashboard`, for librarian and admin. It goes to the
  same roles as `lend_books` today but is a separate permission, like
  `view_members`.
- Headline numbers are stat tiles, not charts: each is a single value. Most
  borrowed (top five, all time, removed books left out, ties by title) and
  the overdue list are tables.
- The overdue list is `loans.list_overdue_loans`, returning the member-loan
  shape, so it carries the same `fine_cents` members see. It is capped at
  `PAGE_SIZE_MAX` loans with a `total`.
- `dashboard.py` depends on `loans.py` and `availability.py`, never the
  reverse.

**Consequences.** Counts are computed per request with a handful of
aggregate queries, fine at library scale. Past 100 overdue loans the page
says how many are not shown; paging that list would be the next step.
