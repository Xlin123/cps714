# Meeting Minutes — Sprint 1

## Week 1 — Async Check-in

- **Date:** 2026-09-30
- **Format:** Async — Discord thread (no live meeting was held this week)
- **Attendees:** Xavier Lin (Developer), Sean Rodriguez Lee (Product Owner), Liam Sheils (Scrum Master)

### Discussed / Decided
- Reviewed the TA's Sprint 1 management-plan requirements (team roles, communication plan, initial risk register) and agreed to draft them for Lab 1 and finalize after AA feedback for Lab 2.
- Agreed on the initial tech stack for the Library Management System: Node.js + Express + TypeScript on the backend, React + TypeScript on the frontend.
- Decided to handle authentication (GitHub issues #2 "Register for a member account" and #3 "Log in and log out") using **oauth2-proxy** in front of the app, authenticating against **Google**, rather than building custom password-based login. Registration becomes a one-time local-profile step (name only) after first Google sign-in.
- Selected Sprint 1 work items: issue **#3** (Log in and log out, already assigned to Xavier) and issue **#2** (Register for a member account), both in the Accounts epic.

### Next Steps
- Xavier: scaffold `server/` and `client/`, implement oauth2-proxy + Google OAuth setup and the register/session endpoints (#2, #3).
- Liam: hold the team's first live (or clearly-documented async) Daily Scrum this week and keep the sprint board current.
- Sean: keep the backlog in `docs/REQUIREMENTS.md` / GitHub Issues groomed and be ready to relay AA feedback after Lab 1's draft presentation.
- Present the draft management plan (`sprint1-management-plan.md`) in Lab 1.
