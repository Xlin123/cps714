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
| GET    | `/api/auth/me`        | —                                       | the signed-in user, or 401    |

Protecting an endpoint by role:

```python
staff = auth.require_role(Role.LIBRARIAN, Role.ADMIN)

@router.post("/api/books")
async def add_book(user: User = Depends(staff)) -> ...: ...
```

Signed-out callers get 401; signed-in callers without a listed role get 403.

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

The database lives in the `lms-data` volume. Compose sets `LMS_COOKIE_SECURE=false` because it serves plain HTTP; set it to `true` behind HTTPS.
