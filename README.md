# CPS714 Library Management System

See `docs/REQUIREMENTS.md` for the full product backlog and `docs/management/` for Sprint management docs (team roles, communication plan, risk register, meeting minutes).

Stack: FastAPI (Python 3.12, managed with [uv](https://docs.astral.sh/uv/)) backend, React + TypeScript (Vite) frontend, SQLite for storage. Accounts and sessions are handled by [fastapi-users](https://fastapi-users.github.io/fastapi-users/). Design decisions are recorded per feature in `docs/<feature>/decisions.md` (`auth`, `catalog`, `borrowing`, `staff-accounts`).

## How auth works

- Email + password login. Passwords are hashed with argon2 (via fastapi-users).
- On login the server sets an `HttpOnly`, `SameSite=Lax` cookie (`lms_session`) holding an opaque token stored server-side; logging out deletes the token, so the cookie stops working immediately.
- Every account has one role: `member`, `librarian` or `admin`.
- Visitors can self-register, and always get `member`. Admins create librarian accounts on the Staff accounts page (below). Admin accounts are created only with the `lms create-user` command.

| Method | Path                  | Body                                    | Result                        |
|--------|-----------------------|-----------------------------------------|-------------------------------|
| POST   | `/api/auth/register`  | JSON `{email, password, name}`          | 201 with the new user         |
| POST   | `/api/auth/login`     | form `username=<email>&password=...`    | 204 and sets the cookie       |
| POST   | `/api/auth/logout`    | -                                       | 204 and revokes the session   |
| GET    | `/api/auth/me`        | -                                       | the signed-in user (with `capabilities`), or 401 |

## Role-based access

What each role may do lives in one place, `server/src/lms/permissions.py` (`ROLE_CAPABILITIES`), mirroring the table in `docs/REQUIREMENTS.md` section 3. `/api/auth/me` returns the signed-in user's `capabilities`, and the client shows or hides links and pages from that list; it keeps no role table of its own.

Protecting an endpoint:

```python
lend = auth.require_capability(Capability.LEND_BOOKS)

@router.get("/api/loans")
async def active_loans(user: Annotated[User, Depends(lend)]) -> ...: ...
```

Signed-out callers get 401; signed-in callers whose role lacks the capability get 403.

| Capability       | Roles            | Pages and endpoints                     |
|------------------|------------------|-----------------------------------------|
| `lend_books`     | librarian, admin | `/staff` (Lending), `/api/loans`        |
| `manage_staff`   | admin            | `/admin` (Staff accounts), `/api/staff` |
| `manage_catalog` | librarian, admin | `/staff` (Add a book), `/api/books`     |
| `view_own_loans` | member           | `/history` (My loans), `/api/loans/mine` |
| `view_members`   | librarian, admin | `/members` (Members), `/api/members`    |
| `place_holds`    | member           | `/` (Place hold), `/history` (Holds), `/api/holds` |
| `view_dashboard` | librarian, admin | `/dashboard` (Dashboard), `/api/dashboard` |

## Catalog

`GET /api/books?q=&limit=50&offset=0` is public. It returns `{"items": [...], "total": n}`, ordered by title, with each book's `available_copies` (total copies minus active loans) and `is_available`. `limit` is 1-100. `q` (at most 100 characters) keeps only books whose title, author, ISBN or category contains it, ignoring case; `total` then counts the matches. The catalog page at `/` has a search bar and pages through the results.

Every list endpoint pages the same way (`server/src/lms/paging.py`).

Librarians and admins can add a book from the Lending page or with `POST /api/books`. Send JSON containing `title`, `author`, `isbn`, `category`, and `total_copies`. Duplicate ISBNs are rejected, and new books immediately appear in the public catalog.

Catalog managers can edit a book with `PATCH /api/books/{id}`. The edit form
changes title, author, ISBN, genre, and total copies. Available copies remain
computed from active loans, and total copies cannot be reduced below the number
currently on loan.

Catalog managers can remove a book with `DELETE /api/books/{id}`. Removal is a
soft delete: the book disappears from browsing and cannot be checked out, while
its loan history remains intact. A book with active loans must be checked in
first. Retired ISBNs remain reserved.

## Lending

Requires `lend_books`. The Lending page (`/staff`) checks books out and back in.

| Method | Path                       | Body                               | Result |
|--------|----------------------------|------------------------------------|--------|
| POST   | `/api/loans`               | JSON `{book_id, borrower_email}`   | 201 with the loan, due `LMS_LOAN_PERIOD_DAYS` from now |
| GET    | `/api/loans?limit&offset`  | -                                  | active loans, soonest due first |
| POST   | `/api/loans/{id}/return`   | -                                  | 200 with the returned loan |
| GET    | `/api/loans/mine?status&limit&offset` | `status`: `all` (default), `active`, `returned` | the member's own loans, newest first, each with `reminder` |
| GET    | `/api/loans/mine/reminders` | -                                 | the member's overdue and due-soon loans (`LMS_DUE_SOON_DAYS`), soonest due first |
| GET    | `/api/loans/mine/fines`    | -                                  | `{total_cents, per_day_cents}`: the member's fines across all loans |

The borrower must be an active member. Refusals come back as a code in `detail`: `LOAN_BOOK_NOT_FOUND` and `LOAN_BORROWER_NOT_FOUND` (404); `LOAN_NO_COPIES_AVAILABLE`, `LOAN_ALREADY_BORROWED`, `LOAN_RESERVED_FOR_HOLD` and `LOAN_ALREADY_RETURNED` (409); `LOAN_NOT_FOUND` (404). Rules and the race-safety design: `docs/borrowing/decisions.md`.

Every loan in `/api/loans/mine` and `/api/members/{id}/loans` carries `fine_cents`: each started day past its due date adds `LMS_FINE_PER_DAY_CENTS` (default 25; 0 turns fines off). A returned loan's fine stops at its return. Fines are shown, not collected. See `docs/borrowing/decisions.md`.

## Holds

Requires `place_holds` (member). A member can hold a book when no copy is free for them; the catalogue shows a Place hold button and each book's `on_hold` count. Holds queue in the order placed. When a copy comes back it is reserved for the first member in line: their hold shows "Ready for pickup" under Holds on My loans, and checkout to anyone else is refused with `LOAN_RESERVED_FOR_HOLD` until they borrow it or cancel. Borrowing fulfils the hold; removing a book cancels its holds.

| Method | Path               | Body              | Result |
|--------|--------------------|-------------------|--------|
| POST   | `/api/holds`       | JSON `{book_id}`  | 201 with the hold's `position` and `is_ready` |
| GET    | `/api/holds/mine`  | -                 | the member's active holds, oldest first |
| DELETE | `/api/holds/{id}`  | -                 | 204; cancels one of the member's own holds |

Refusals: `HOLD_BOOK_NOT_FOUND` and `HOLD_NOT_FOUND` (404); `HOLD_BOOK_AVAILABLE`, `HOLD_ALREADY_BORROWED` and `HOLD_ALREADY_PLACED` (409). See `docs/holds/decisions.md`.

## Members

Requires `view_members`. The Members page (`/members`) searches member accounts; each result opens a profile (`/members/{id}`) with the member's details and loan history.

| Method | Path                                    | Query                         | Result |
|--------|-----------------------------------------|-------------------------------|--------|
| GET    | `/api/members?q&limit&offset`           | `q`: name or email fragment, case-insensitive, at most 100 characters; empty lists everyone | member accounts (active and deactivated), by name |
| GET    | `/api/members/{id}`                     | -                             | the member with `active_loans`, `total_loans` and `fines_cents` |
| GET    | `/api/members/{id}/loans?status&limit&offset` | `status`: `all` (default), `active`, `returned` | the member's loans, same shape as `/api/loans/mine` |

Staff accounts are never returned: an unknown id or a staff id gives `MEMBER_NOT_FOUND` (404). See `docs/members/decisions.md`.

## Dashboard

Requires `view_dashboard`. `GET /api/dashboard` returns `counts` (titles, copies, on loan, overdue, holds waiting, active members), the five `most_borrowed` books of all time, and `overdue`: up to 100 overdue loans, longest overdue first, each with its borrower and `fine_cents` (same shape as `/api/loans/mine`). The Dashboard page (`/dashboard`) shows them as tiles and tables, linking each borrower to their profile. See `docs/dashboard/decisions.md`.

## Staff accounts

Requires `manage_staff` (admin). The Staff accounts page (`/admin`) creates librarians and deactivates or reactivates them.

| Method | Path                     | Body                          | Result |
|--------|--------------------------|-------------------------------|--------|
| POST   | `/api/staff`             | JSON `{email, name, password}` | 201 with the new librarian; there is no `role` field |
| GET    | `/api/staff?limit&offset` | -                            | librarian accounts |
| PATCH  | `/api/staff/{id}`        | JSON `{is_active}`            | 200; deactivating signs them out at once |

Only librarian accounts can be changed (`STAFF_NOT_FOUND` otherwise). See `docs/staff-accounts/decisions.md`.

## Errors

Every refusal has a stable code in `detail`. Request-validation failures (bad JSON, missing or out-of-range fields, bad query parameters) are always:

```json
HTTP 422
{
  "detail": "VALIDATION_FAILED",
  "errors": [
    {"field": "title", "message": "Required."},
    {"field": "total_copies", "message": "Must be 0 or more."}
  ]
}
```

`field` is the API's field name, or `null` when the whole request is at fault (e.g. malformed JSON). Messages are written for users, and submitted values are never echoed back. The client shows each field's message under its input (`useSubmit` with the form's field names, `components/FieldError`); any field error a form doesn't render is folded into the form-level message so nothing is dropped. See `docs/validation/decisions.md`.

## Adding a feature

- Server: a module in `server/src/lms/` with its schemas, logic and a router factory that takes only what it needs; add the router to the list in `create_app` (`app.py`). Guard endpoints with a capability from `permissions.py`, and add the new capability to `GUARDED_REQUEST_FOR` and `EXPECTED` in `tests/test_permissions.py`.
- Refusals: raise a stable code as `detail`, and add its user-facing text to `ERROR_MESSAGES` in `client/src/api/http.ts`. If the code is about one input, also map it to that field in `ERROR_FIELDS` so forms show it inline.
- Client: a folder in `client/src/<feature>/` with an `api.ts` built on `getJson`/`send` from `api/http.ts`, pages using `useLoad` for data and `useSubmit` (or `components/ActionButton`) for actions. Mirror new capabilities in `client/src/auth/api.ts`.
- Tables: new tables are created at startup. The startup schema step also adds the
  book retirement column to existing databases. Other changes to existing
  tables still need a migration or database reset.

## Local development

Two terminals:

```bash
cd server
uv sync
LMS_COOKIE_SECURE=false uv run uvicorn --factory lms.app:app_from_env --reload   # http://localhost:8000
```

```bash
cd client
npm install
npm run dev         # http://localhost:5173, proxies /api to :8000
```

For test data, add `LMS_DEMO_DATA=true` to the server command. That adds 12 sample books and creates `member@example.com`, `librarian@example.com` and `admin@example.com` (password `library-demo`), and the login page shows a button per role that fills in the form. The passwords are public, so never enable it outside your own machine.

Create the first admin (prompts for the password):

```bash
cd server
uv run lms create-user --email admin@example.com --name Admin --role admin
```

Configuration is via `LMS_*` environment variables; see `.env.example`.

Server tests and lint:

```bash
cd server
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Full stack (Docker Compose)

```bash
docker compose up --build    # http://localhost:8000
docker compose exec app /app/server/.venv/bin/lms create-user --email admin@example.com --name Admin --role admin
```

Compose enables the demo data (`LMS_DEMO_DATA=true`); set it to `false` in `.env` to turn them off. Pass `--build` after code changes, otherwise Compose reuses the old image.

The database lives in the `lms-data` volume. Compose sets `LMS_COOKIE_SECURE=false` because it serves plain HTTP; set it to `true` behind HTTPS.

## Documents

Gantt Chart : https://docs.google.com/document/d/1FqA0hwHrnps754bklaw-2B9ZYNS_FJOhthRWKsUfDlQ/edit?tab=t.0
Meeting Minutes : https://docs.google.com/document/d/1Sf_fg_BmK7BCHXbzODVwBaH_tWu6HV2jHdwOciHaYKg/edit?tab=t.0
Risk Management : https://docs.google.com/document/d/1U3XcoCLSrkeQf5sLgHIS153qTGFA1qcM_4ZZR_kKM8M/edit?tab=t.0
Feedback Document : https://docs.google.com/document/d/1l1r-HCLpY4q3L92tEEquB7oW03fmuqmQKNi6TD9OXSs/edit?tab=t.0
