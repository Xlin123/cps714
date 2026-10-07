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

## 2026-10-07: Demo accounts behind a server flag

**Context.** The team wants login-page buttons that fill in a member, librarian
or admin test account.

**Options.**

| Option | Notes |
|---|---|
| Server flag | `LMS_DEMO_DATA=true` seeds the accounts at startup and serves their logins at `/api/dev/demo-accounts`; the page shows buttons only if that endpoint answers. One switch, credentials defined once. |
| Build flag + CLI seed | `VITE_DEMO_ACCOUNTS` bakes credentials into the JS bundle; accounts are seeded by hand. Credentials defined in both TS and Python. |

**Decision.** Server flag.

**Consequences.**

- Off by default. When off, the endpoint is not mounted (404) and no accounts
  are created. Docker Compose turns it on because it is the local dev stack.
- Turning the flag off later does not delete accounts already seeded; their
  public passwords keep working until the accounts are removed.
- Seeding is idempotent and fails startup if a demo email belongs to an account
  with a different role.

Renamed to `LMS_DEMO_DATA` on 2026-10-07 when it started seeding sample books
too (see `docs/catalog/decisions.md`).

## 2026-10-07: Role-based access through a server-side capability map (LMS-3)

**Context.** LMS-3 needs protected pages and actions blocked for roles that
aren't allowed, verified for each role. No staff or admin feature exists yet.

**Decision.**

- `server/src/lms/permissions.py` maps each role to a set of capabilities,
  mirroring `docs/REQUIREMENTS.md` §3. Endpoints are guarded with
  `Auth.require_capability`, which builds on `require_role`.
- `/api/auth/me` returns the user's capabilities. The client gates links and
  pages on that list and keeps no role table, so the rules exist once.
- LMS-3 is shown with empty placeholder pages, `/staff` (librarian, admin) and
  `/admin` (admin), chosen over example pages listing accounts. Each page reads
  its text from a guarded endpoint, so a wrong role is refused by the server
  (403), not just by a hidden link.

**Consequences.** Later stories add a capability, grant it in the map, and
guard their endpoints with it. The client's guard is a convenience; the
server's is the enforcement.
