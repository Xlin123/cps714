# Sprint 1 — Management Plan (Draft)

> Status: **Draft** — presented in Lab 1 of Sprint 1. Will be finalized after AA feedback and presented as the completed version in Lab 2.

---

## 1. Team Roles & Responsibilities

| Name | Role | Responsibilities |
|---|---|---|
| Sean Rodriguez Lee | Product Owner | Owns and prioritizes the product backlog (`docs/REQUIREMENTS.md` / GitHub Issues); writes and refines user stories and acceptance criteria; accepts or rejects completed work each sprint; primary liaison with the AA (acting stakeholder) and channels their feedback into the backlog. |
| Liam Sheils | Scrum Master | Facilitates the Daily Scrum; tracks the sprint board and removes blockers reported by the team; ensures Scrum process artifacts (this plan, meeting minutes, risk register) are kept up to date and ready for each lab. |
| Xavier Lin | Developer | Implements backlog items assigned each sprint; writes automated tests for completed features; participates in code review on pull requests; reports progress and blockers to the Scrum Master. |

Note: with a 3-person team, the Product Owner and Scrum Master also pick up development and testing tasks alongside their primary roles — the roles above describe primary ownership, not the only work each person does.

---

## 2. Communication Plan

- **Daily Scrum:** Async check-in posted in the team's Discord server. Each teammate posts what they did, what they're doing next, and any blockers. *(Sprint 1, Week 1 was fully async — no live meeting was held; see `meeting-minutes.md`. The team plans to move to a short live/voice standup once everyone's schedules line up.)*
- **Tools:**
  - **Discord** — day-to-day chat, async Daily Scrum updates, and ad hoc voice calls.
  - **GitHub Issues & Pull Requests** — task tracking (one issue per backlog item), code review, and technical discussion.
- **Decision recording:** Decisions specific to a backlog item are recorded as comments on that item's GitHub issue. Cross-cutting decisions (e.g. tech stack, sprint scope) are recorded in `docs/management/meeting-minutes.md` so they're visible to the whole team and to the AA/TA reviewing sprint artifacts.

---

## 3. Initial Risk Register

| # | Risk | Likelihood | Impact | Planned Response | Owner |
|---|---|---|---|---|---|
| 1 | Small team (3 people) — if one person becomes unavailable, a whole role or set of tasks stalls. | Medium | High | Keep GitHub issues small and well-documented so anyone can pick one up; cross-train on both frontend and backend pieces rather than siloing by person. | Liam Sheils (Scrum Master) |
| 2 | Scope creep — pulling P2/P3 backlog items (see `docs/REQUIREMENTS.md`) into the sprint before the P1 MVP items are done. | Medium | Medium | Product Owner enforces sprint scope at planning; backlog is groomed and re-prioritized each sprint rather than mid-sprint. | Sean Rodriguez Lee (Product Owner) |
| 3 | Misconfigured oauth2-proxy / Google OAuth client — e.g. trusting forwarded-auth headers from outside the proxy, or a wrong redirect URI, could let unauthenticated requests through or break login entirely. | Medium | High | Only trust `X-Forwarded-Email`/`X-Forwarded-User` headers on requests that pass through oauth2-proxy (network-isolated via Docker Compose); document Google OAuth client setup in the README; require code review before merging auth-related PRs. | Xavier Lin (Developer) |
| 4 | Async-only communication (no live meetings) causes missed context or duplicated work. | Medium | Low | Record all cross-cutting decisions in `meeting-minutes.md` and issue comments so nothing depends on someone having seen a chat message live. | Liam Sheils (Scrum Master) |
