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

## Catalog

`GET /api/books?limit=50&offset=0` is public. It returns `{"items": [...], "total": n}`, ordered by title, with each book's `available_copies` (total copies minus active loans) and `is_available`. `limit` is 1-100. The catalog page at `/` pages through it.

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

The borrower must be an active member. Refusals come back as a code in `detail`: `LOAN_BOOK_NOT_FOUND` and `LOAN_BORROWER_NOT_FOUND` (404); `LOAN_NO_COPIES_AVAILABLE`, `LOAN_ALREADY_BORROWED` and `LOAN_ALREADY_RETURNED` (409); `LOAN_NOT_FOUND` (404). Rules and the race-safety design: `docs/borrowing/decisions.md`.

## Staff accounts

Requires `manage_staff` (admin). The Staff accounts page (`/admin`) creates librarians and deactivates or reactivates them.

| Method | Path                     | Body                          | Result |
|--------|--------------------------|-------------------------------|--------|
| POST   | `/api/staff`             | JSON `{email, name, password}` | 201 with the new librarian; there is no `role` field |
| GET    | `/api/staff?limit&offset` | -                            | librarian accounts |
| PATCH  | `/api/staff/{id}`        | JSON `{is_active}`            | 200; deactivating signs them out at once |

Only librarian accounts can be changed (`STAFF_NOT_FOUND` otherwise). See `docs/staff-accounts/decisions.md`.

## Adding a feature

- Server: a module in `server/src/lms/` with its schemas, logic and a router factory that takes only what it needs; add the router to the list in `create_app` (`app.py`). Guard endpoints with a capability from `permissions.py`, and add the new capability to `GUARDED_REQUEST_FOR` and `EXPECTED` in `tests/test_permissions.py`.
- Refusals: raise a stable code as `detail`, and add its user-facing text to `ERROR_MESSAGES` in `client/src/api/http.ts`.
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
