# CPS714 Library Management System

See `docs/REQUIREMENTS.md` for the full product backlog and `docs/management/` for Sprint management docs (team roles, communication plan, risk register, meeting minutes).

Stack: FastAPI (Python 3.12, managed with [uv](https://docs.astral.sh/uv/)) backend, React + TypeScript (Vite) frontend, SQLite for storage. Accounts and sessions are handled by [fastapi-users](https://fastapi-users.github.io/fastapi-users/). Design decisions are recorded in `docs/auth/decisions.md`.

## How auth works

- Email + password login. Passwords are hashed with argon2 (via fastapi-users).
- On login the server sets an `HttpOnly`, `SameSite=Lax` cookie (`lms_session`) holding an opaque token stored server-side; logging out deletes the token, so the cookie stops working immediately.
- Every account has one role: `member`, `librarian` or `admin`.
- Visitors can self-register, and always get `member`. Librarian and admin accounts are created with the `lms create-user` command (below).

| Method | Path                  | Body                                    | Result                        |
|--------|-----------------------|-----------------------------------------|-------------------------------|
| POST   | `/api/auth/register`  | JSON `{email, password, name}`          | 201 with the new user         |
| POST   | `/api/auth/login`     | form `username=<email>&password=...`    | 204 and sets the cookie       |
| POST   | `/api/auth/logout`    | —                                       | 204 and revokes the session   |
| GET    | `/api/auth/me`        | —                                       | the signed-in user (with `capabilities`), or 401 |

## Role-based access

What each role may do lives in one place, `server/src/lms/permissions.py` (`ROLE_CAPABILITIES`), mirroring the table in `docs/REQUIREMENTS.md` §3. `/api/auth/me` returns the signed-in user's `capabilities`, and the client shows or hides links and pages from that list; it keeps no role table of its own.

Protecting an endpoint:

```python
staff = auth.require_capability(Capability.VIEW_STAFF_AREA)

@router.get("/api/staff/area")
async def staff_area(user: Annotated[User, Depends(staff)]) -> ...: ...
```

Signed-out callers get 401; signed-in callers whose role lacks the capability get 403. `/staff` (librarian, admin) and `/admin` (admin) are placeholder pages backed by `GET /api/staff/area` and `GET /api/admin/area`.

## Catalog

`GET /api/books?limit=50&offset=0` is public. It returns `{"items": [...], "total": n}`, ordered by title, with each book's `available_copies` and `is_available`. `limit` is 1–100. The catalog page at `/` pages through it.

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