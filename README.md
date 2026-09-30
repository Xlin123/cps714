# CPS714 Library Management System

See `docs/REQUIREMENTS.md` for the full product backlog and `docs/management/` for Sprint management docs (team roles, communication plan, risk register, meeting minutes).

Stack: Node.js + Express + TypeScript backend, React + TypeScript (Vite) frontend, SQLite for storage. Login/logout is handled by [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/) in front of the app, authenticating against Google — the app never sees or stores a password.

## How auth works

1. `oauth2-proxy` sits in front of the Express app and requires a Google sign-in before any request reaches it.
2. Once signed in, oauth2-proxy forwards `X-Forwarded-Email` / `X-Forwarded-User` headers to the app on every request.
3. The app checks `GET /api/auth/session`: if no local profile exists yet for that email, the frontend shows a one-field registration form (name) — submitting it calls `POST /api/auth/register`, which creates a `member` profile.
4. Logging out just navigates to `/oauth2/sign_out`, which oauth2-proxy handles.

## Local development (without Docker)

Two terminals:

```bash
cd server
npm install
npm run dev        # http://localhost:4000
```

```bash
cd client
npm install
npm run dev         # http://localhost:5173, proxies /api to :4000 if configured, or hit :4000 directly
```

Without oauth2-proxy running, `/api/auth/session` will always 401 (no `X-Forwarded-Email` header) — for local UI work without Google, you can pass the header manually with a tool like `curl -H "X-Forwarded-Email: you@example.com"` or a browser extension.

Run the server test suite:

```bash
cd server
npm test
```

## Full stack with oauth2-proxy + Google (Docker Compose)

1. Create a Google OAuth client:
   - Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
   - Create an **OAuth client ID** of type **Web application**.
   - Add authorized redirect URI: `http://localhost:4180/oauth2/callback`.
   - Copy the generated Client ID and Client Secret.
2. Copy `.env.example` to `.env` and fill in:
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` from step 1.
   - `OAUTH2_PROXY_COOKIE_SECRET` — a random 32-byte secret, e.g. `openssl rand -base64 32 | head -c 32 | base64`.
3. Start everything:

   ```bash
   docker compose up --build
   ```

4. Visit `http://localhost:4180` — you'll be redirected to Google sign-in, then back to the app. First-time sign-ins are prompted to complete registration (name only).
5. To log out, visit `http://localhost:4180/oauth2/sign_out`.
