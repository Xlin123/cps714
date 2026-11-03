# Staff accounts decisions

## 2026-11-02: Admins manage librarian accounts over HTTP (LMS-11; #12)

**Context.** F1 asks for admins to create and manage librarian accounts.
Until now staff accounts came only from the `lms create-user` CLI.

**Decision.**

- `/api/staff` (capability `MANAGE_STAFF`, admin only) can create, list and
  activate/deactivate librarians. "Manage" stops there: no rename, password
  reset or promotion of members.
- The create body has no `role` field and rejects unknown fields; the server
  always creates a `librarian`. Admin accounts are still CLI-only, so no HTTP
  request can mint an admin.
- The admin sets a starting password; the normal password rules apply.
- Updates only match librarian rows. Admins and members get 404, so an admin
  cannot deactivate another admin or themselves.
- Deactivating deletes the librarian's sessions in the same transaction, so
  they are signed out immediately, and those sessions stay dead if the account
  is reactivated.

**Consequences.**

- Supersedes "staff accounts are created only through the CLI" in
  `docs/auth/decisions.md` for librarians.
- Create errors reuse the self-registration codes
  (`REGISTER_USER_ALREADY_EXISTS`, `REGISTER_INVALID_PASSWORD`).
