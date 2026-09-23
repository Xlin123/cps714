# Library Management System — Requirements & Product Backlog

> This document is the single source of truth for scope and the product backlog.
> Each backlog item maps 1:1 to a GitHub issue.

---

## 1. Overview / Purpose

The **Library Management System (LMS)** is a web application that lets a library manage
its collection and lets people find and borrow items. **Guests** can browse and search
the catalog. **Members** can log in, search, and track the books they have borrowed.
**Librarians** manage the catalog and handle checkouts and returns. **Admins** manage
staff accounts and system settings. The goal is a clean, usable system that covers the
core lending workflow end-to-end.

---

## 2. Goals & Non-Goals

### Goals
- Provide a searchable, browsable catalog of library items.
- Support the full borrowing lifecycle: check out → track due date → check in/return.
- Enforce role-based access so each user only sees/does what they should.
- Be simple enough for 3 people to build, test, and demo in one semester.

### Non-Goals (explicitly out of scope for MVP)
- Online payments or fine collection.
- E-book reading, file hosting, or DRM.
- Inter-library loans between institutions.
- Barcode/RFID hardware or self-checkout kiosks.
- Mobile native apps (web only).

---

## 3. User Roles & Permissions

| Capability | Guest | Member | Librarian | Admin |
|---|:---:|:---:|:---:|:---:|
| Browse / search catalog | ✅ | ✅ | ✅ | ✅ |
| Register / log in | — | ✅ | ✅ | ✅ |
| View own current loans & due dates | — | ✅ | ✅ | ✅ |
| Add / edit / delete books (catalog CRUD) | — | — | ✅ | ✅ |
| Check out / check in books | — | — | ✅ | ✅ |
| View any member's profile & loan history | — | — | ✅ | ✅ |
| Create / manage librarian (staff) accounts | — | — | — | ✅ |
| System settings | — | — | — | ✅ |

---

## 4. Functional Requirements

Grouped by feature area (**Epic**). These describe *what* the system does, independent of
technology.

### Epic A — Accounts & Authentication
- A1. Visitors can register for a Member account (name, email, password).
- A2. Registered users can log in and log out.
- A3. Every account has a role (Member / Librarian / Admin) that controls access.
- A4. Passwords are stored securely (hashed, never plaintext).

### Epic B — Catalog Management
- B1. Librarians can add a book (title, author, ISBN, category, copies).
- B2. Librarians can edit a book's details.
- B3. Librarians can delete a book.
- B4. Anyone can view a book's detail page (with availability).

### Epic C — Search & Browse
- C1. Any user (incl. guest) can search the catalog by title, author, or keyword.
- C2. Any user can browse the full catalog list, showing availability status.

### Epic D — Borrowing
- D1. Librarians can check out an available book to a member; system sets a due date and
  marks the copy unavailable.
- D2. Librarians can check in / return a book; system marks the copy available again.
- D3. The system prevents checking out a book with no available copies.
- D4. Members can view their current loans and due dates.

### Epic E — Member Management
- E1. Librarians can look up a member's profile.
- E2. Librarians can view a member's borrowing history.

### Epic F — Administration
- F1. Admins can create and manage librarian (staff) accounts.
- F2. Admins can access basic system settings (e.g. default loan period).

---

## 5. Non-Functional Requirements

- **Usability:** Clear navigation; core tasks doable in a few clicks; readable on desktop
  and tablet.
- **Security:** Hashed passwords; role-based access control on every protected action;
  input validation to prevent malformed data.
- **Performance:** Catalog search returns results quickly for a demo-sized dataset
  (hundreds–low thousands of items).
- **Reliability:** Data persists correctly across sessions; no data loss on normal use.
- **Maintainability:** Organized code, meaningful names, and a short README so all 3
  teammates can contribute.

---

## 6. Initial Product Backlog (Prioritized)

User stories in the form *"As a [role], I want [feature], so that [benefit]."*
Priority: **P1** = high, **P2** = medium, **P3** = nice to have.
Estimate is a rough T-shirt size (S / M / L).
Each row = one GitHub issue.

### P1 — high (Core MVP)

| ID | User Story | Epic | Priority | Est. | Acceptance Criteria |
|---|---|---|---|:---:|---|
| LMS-1 | As a visitor, I want to register for a member account, so that I can use the library online. | A | P1 | M | Can register with name/email/password; duplicate email rejected; account created with Member role. |
| LMS-2 | As a user, I want to log in and log out, so that my session is secure. | A | P1 | S | Valid credentials log in; invalid rejected; logout ends session. |
| LMS-3 | As the system, I want role-based access control, so that users only do what they're allowed. | A | P1 | M | Protected pages/actions blocked for unauthorized roles; verified for each role. |
| LMS-4 | As a guest or member, I want to search the catalog by title/author/keyword, so that I can find books. | C | P1 | M | Search returns matching books; empty result shows a clear message. |
| LMS-5 | As a guest or member, I want to browse the catalog, so that I can see what's available. | C | P1 | S | Catalog list shows title, author, and availability status. |
| LMS-6 | As a librarian, I want to add a book, so that it appears in the catalog. | B | P1 | M | New book with required fields is saved and searchable. |
| LMS-7 | As a librarian, I want to edit and delete books, so that the catalog stays accurate. | B | P1 | M | Edits persist; deleted book no longer appears; confirm before delete. |
| LMS-8 | As a librarian, I want to check out a book to a member, so that lending is recorded. | D | P1 | M | Sets due date; marks copy unavailable; blocks checkout if none available. |
| LMS-9 | As a librarian, I want to check in a returned book, so that it becomes available again. | D | P1 | S | Loan marked returned; copy availability restored. |
| LMS-10 | As a member, I want to view my current loans and due dates, so that I know what I owe. | D | P1 | S | Member sees a list of their active loans with due dates. |
| LMS-11 | As an admin, I want to create and manage librarian accounts, so that staff can use the system. | F | P1 | M | Admin can create a librarian; new librarian can log in with staff permissions. |

### P2 — medium

| ID | User Story | Epic | Priority | Est. | Acceptance Criteria |
|---|---|---|---|:---:|---|
| LMS-12 | As a member, I want to view my borrowing history, so that I can see past loans. | D/E | P2 | S | Member sees list of returned loans with dates. |
| LMS-13 | As a librarian, I want to view a member's profile and loan history, so that I can assist them. | E | P2 | M | Librarian can look up a member and see active + past loans. |
| LMS-14 | As a librarian, I want the catalog to track multiple copies, so that popular books can be lent more than once. | B/D | P2 | M | Book shows total vs. available copies; checkouts decrement availability. |
| LMS-15 | As a user, I want clear validation and error messages, so that I understand what went wrong. | All | P2 | S | Invalid input shows helpful inline messages; no silent failures. |

### P3 — nice to have (post-MVP roadmap)

| ID | User Story | Epic | Priority | Est. | Acceptance Criteria |
|---|---|---|---|:---:|---|
| LMS-16 | As a member, I want to reserve/hold a checked-out book, so that I get it next. | D | P3 | M | Member can place a hold; notified/queued when returned. |
| LMS-17 | As a librarian, I want overdue fines calculated automatically, so that late returns are tracked. | D | P3 | M | Fine accrues per day overdue based on a configurable rate. |
| LMS-18 | As a member, I want due-soon / overdue notifications, so that I return on time. | D | P3 | L | System generates notifications for upcoming/overdue due dates. |
| LMS-19 | As a librarian, I want a dashboard (most borrowed, overdue list), so that I can manage the library. | E/F | P3 | M | Dashboard shows key stats and an overdue-items list. |
| LMS-20 | As an admin, I want reports/analytics, so that I can understand usage. | F | P3 | L | Admin can view summary reports (loans over time, popular titles). |

---

## 7. Suggested Sprint Breakdown

- **Sprint 1 — Accounts & Catalog view:** LMS-1, LMS-2, LMS-3, LMS-5. *(A member can log
  in and browse.)*
- **Sprint 2 — Catalog management & search:** LMS-6, LMS-7, LMS-4. *(Librarian manages
  books; everyone can search.)*
- **Sprint 3 — Borrowing (the core loop):** LMS-8, LMS-9, LMS-10, LMS-11. *(Full checkout
  → return → view loans works end-to-end — MVP complete.)*
- **Sprint 4 — Polish & Should-haves:** LMS-12 → LMS-15, testing, demo prep. Pull in
  Could-haves only if ahead of schedule.
