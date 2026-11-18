# Validation and error message decisions

## 2026-11-18: One 422 shape and inline field errors (LMS-15; #16, #62, #63)

**Context.** Invalid input should show helpful inline messages, with no silent
failures. FastAPI's default 422 body is a list of raw pydantic errors: worded
for developers, a different shape from every other refusal (`detail` as a
string code), and it echoes each rejected `input` back, which includes
submitted passwords. The client showed a generic fallback for any 422.

**Options.**

| Option | Notes |
|---|---|
| String code + `errors` list | `{"detail": "VALIDATION_FAILED", "errors": [{field, message}]}`. Keeps `detail` a string code like every other refusal. |
| Object in `detail` | `{"detail": {"code", "fields": {name: message}}}`, like fastapi-users' `REGISTER_INVALID_PASSWORD`. Breaks the string-code convention. |

**Decision.** String code + `errors` list.

- `lms/validation.py` holds a pure `field_errors` mapping pydantic error types
  to plain messages, and installs a `RequestValidationError` handler. Only
  `type`, `loc`, `ctx` and `msg` are read, never `input`.
- `field` is the innermost name in `loc`; `null` when no single field is to
  blame (malformed JSON, a list index).
- Status stays 422, so existing tests that check only the status still hold.
- Client: `ApiError` carries `fieldErrors`. Refusal codes about one input
  (`CATALOG_DUPLICATE_ISBN`, `LOAN_BORROWER_NOT_FOUND`, …) are mapped to their
  field in `ERROR_FIELDS`, and `REGISTER_INVALID_PASSWORD` goes to `password`,
  so they show inline too.
- `useSubmit(action, inlineFields)` returns the field errors a form renders and
  folds any others into the form-level `error`, so a refusal is never dropped.
  Client-side checks throw `ApiError` the same way.
- Requests that get no response (offline, server down) throw `ApiError` from
  `reach`, and logout and the post-login session check now report failures;
  both previously failed silently as unhandled rejections.

**Consequences.**

- New refusal codes need text in `ERROR_MESSAGES`, and a field in
  `ERROR_FIELDS` if they concern one input.
- Unknown pydantic error types fall back to pydantic's own `msg`; add a case
  to `_message` when one shows up in a form.
