# Auth decisions

## 2026-10-07: Replace oauth2-proxy + Google with password login on FastAPI

**Context.** The team wants a normal email/password login with three roles
(member, librarian, admin), matching REQUIREMENTS.md A1–A4, rather than Google
sign-in. The backend moves from Express to FastAPI.

**Options.**

| Option | Notes |
|---|---|
| fastapi-users | Register, login, logout, user model, argon2 hashing out of the box. In maintenance mode: security fixes only. |
| AuthX | JWT issue/verify only; registration, user table and hashing written by us. |
| pwdlib + Starlette sessions | Fewest deps, but login/session logic is hand-rolled. |

**Decision.** fastapi-users with SQLAlchemy (async, aiosqlite).

**Consequences.**

- Sessions: cookie transport + database token strategy. Tokens are opaque and
  stored server-side, so logout revokes immediately. Chosen over JWT, which
  cannot be revoked before expiry.
- Cookie is `HttpOnly`, `SameSite=Lax`, `Secure` unless `LMS_COOKIE_SECURE=false`.
- The base role is named `member` (as in REQUIREMENTS.md), not `user`, to avoid
  confusion with the `User` model.
- `role` is the only authority for access. fastapi-users' `is_superuser` column
  exists because the library requires it, but nothing reads or sets it. For the
  same reason the fastapi-users `users` router (whose admin routes key off
  `is_superuser`) is not mounted; `/api/auth/me` is our own endpoint.
- Self-registration rejects unknown fields, so a visitor cannot send `role`.
  Staff accounts are created only through the `lms create-user` CLI, which is
  never reachable over HTTP.
- Reset-password and email-verification routers are not mounted, so no token
  secret is configured. Mounting either requires adding one.
- Tables are created with `create_all` at startup. Schema changes will need a
  migration tool (e.g. Alembic) once there is data worth keeping.
