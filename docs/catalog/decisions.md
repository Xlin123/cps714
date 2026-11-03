# Catalog decisions

## 2026-10-07: Browse catalog for Sprint 1 (LMS-5)

**Context.** LMS-5 (browse) is in Sprint 1, but adding books (LMS-6) is
Sprint 2, so the catalog would start empty.

**Options.**

| Option | Notes |
|---|---|
| Seed sample books behind the demo switch | Stays in sprint scope; real deployments start empty. |
| Pull LMS-6 forward | Real "add book" action, but brings a Sprint 2 story into Sprint 1. |
| `lms add-book` CLI | No UI for adding; another operator command to maintain. |

**Decision.** Seed 12 sample books when `LMS_DEMO_DATA=true` (renamed from
`LMS_DEMO_ACCOUNTS`). Seeding inserts only missing ISBNs, so restarts are
harmless. The sample ISBNs are not checked against real editions.

**Consequences.**

- `GET /api/books` is public and paginated: `limit` 1–100 (default 50),
  `offset` ≥ 0, ordered by title then id, with a `total` count.
- `available_copies` equals `total_copies` until loans exist (Sprint 3). It is
  computed in one function, `catalog.available_copies`, which loans will change.
- Search (LMS-4) is not included.
