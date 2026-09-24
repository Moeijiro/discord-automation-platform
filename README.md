# Discord Automation Platform

**Portfolio case study:** [moeijiro.github.io/portfolio/projects/discord-automation-platform](https://moeijiro.github.io/portfolio/projects/discord-automation-platform/) · **Live demo:** not hosted — the app runs locally in a few commands (see below).

A small, production-shaped platform for managing Discord server automation from a web
dashboard: sign in with Discord, configure verification, welcome messages and role
automation for a server you administrate, and read back an audit trail of everything the
automation did.

It is built as a portfolio project — the interesting part is not the feature count but the
boundaries: an OAuth2 flow whose tokens never reach the browser, a permission gate that
asks Discord rather than trusting its own cache, and automations that refuse to run when
Discord would reject them anyway.

```
FastAPI backend · Discord.py gateway bot · React + TypeScript dashboard · SQLite/PostgreSQL
```

---

## Contents

- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [API overview](#api-overview)
- [Security notes](#security-notes)
- [Demo mode](#demo-mode)
- [Tests](#tests)
- [Project structure](#project-structure)

---

## Screenshots

| | |
|---|---|
| ![Login](docs/screenshots/login.png) | ![Server list](docs/screenshots/dashboard.png) |
| *Discord OAuth2 entry point* | *Servers the signed-in account can manage* |
| ![Server dashboard](docs/screenshots/server.png) | ![Audit log](docs/screenshots/logs.png) |
| *Automation configuration and quick actions* | *Filterable audit trail* |

> Captured from the running stack in demo mode — no Discord application required. The
> servers and roles are mock structure; the audit entries are the actions actually taken
> during that session.

---

## Architecture

```mermaid
flowchart TD
    U["User<br/>(browser)"] -->|"HttpOnly session cookie"| D["Dashboard<br/>React + TypeScript"]
    D -->|"REST /api/*"| A["FastAPI backend"]

    A -->|"OAuth2 code exchange"| O["Discord OAuth2"]
    A -->|"REST: roles, channels, messages<br/>(bot token)"| X["Discord API"]
    A <-->|"users · guilds · settings · audit log"| DB[("Database<br/>SQLite / PostgreSQL")]

    B["Automation bot<br/>discord.py gateway"] -->|"member_join, guild_join"| DB
    X -.->|"gateway events"| B
    B -->|"welcome message, autorole"| X

    subgraph Shared["One automation service"]
        A
        B
    end
```

Two processes, one codebase:

| Process | Responsibility |
|---|---|
| `uvicorn app.main:app` | REST API, OAuth2 flow, permission checks, audit trail |
| `python -m app.bot` | Discord gateway connection; reacts to member joins |

Both import `app.services.automation`, so "what happens when a member joins" is written once
and behaves identically whether it was triggered by a gateway event or a dashboard click.

**Request path for a role change**

```
Dashboard  →  POST /api/guilds/{id}/roles/add
           →  session cookie → user
           →  membership + Manage Server permission
           →  bot present? bot has MANAGE_ROLES? role below the bot's highest role?
           →  Discord REST (with X-Audit-Log-Reason)
           →  audit entry (success *or* failure)
```

---

## Features

**Discord login** — OAuth2 authorisation-code flow with `identify` and `guilds` scopes.
The user's Discord ID, username, avatar and guild list are stored; access and refresh
tokens are encrypted at rest and never serialised into any API response.

**Server dashboard** — one card per server Discord reports for the account, showing whether
the bot is connected and whether the account has the permission needed to configure it.
Per-server: member/online counts, automation status, recent events and quick actions.

**Verification** — an admin configures `verified_role_id`; a member triggers verification
and the bot assigns the role. Members may verify themselves; verifying someone else
requires Manage Server.

**Role automation** — assign or remove a role from a member, with the role hierarchy and
integration-managed roles respected. Optional join autorole.

**Welcome automation** — configurable channel and message template with `{user}`,
`{username}`, `{server}` and `{member_count}` placeholders, posted by the bot on join.

**Audit logs** — every event (`verification_completed`, `role_added`, `role_removed`,
`member_joined`, `welcome_sent`, `settings_updated`, `webhook_received`,
`automation_failed`) is stored with actor, target, guild, timestamp and metadata, and
surfaced on a filterable, paged page.

**Webhooks** — `POST /api/webhooks/custom` accepts HMAC-SHA256 signed events from external
systems, validates them strictly, records them in the audit trail and can announce them in
a Discord channel.

**Rate limiting** — fixed-window limits on login, verification, role changes, settings
updates and the webhook endpoint, keyed per session (falling back to IP).

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI + Pydantic v2 | typed request/response models, OpenAPI for free |
| ORM | SQLAlchemy 2.0 (typed) | SQLite by default, PostgreSQL by changing one URL |
| Bot | discord.py | gateway events (`on_member_join`) |
| Auth | Discord OAuth2 + JWT session cookie | no password storage, no token in the browser |
| Crypto | `cryptography` (Fernet + HKDF), PyJWT | encrypted tokens, signed sessions, signed webhooks |
| Dashboard | React 19 + TypeScript + Vite | small, typed, fast |
| Styling | Tailwind CSS v4 | design tokens in one `@theme` block |
| Tests | pytest | 49 tests over auth, permissions, validation, webhooks, limits |

---

## Getting started

Requirements: Python 3.11+, Node 18+.

```bash
git clone https://github.com/Moeijiro/discord-automation-platform.git
cd discord-automation-platform
cp .env.example backend/.env        # demo mode works with the defaults
make install                        # venv + pip install + npm install
```

Run the two processes (each in its own terminal):

```bash
make api    # http://localhost:8000  (docs at /docs)
make web    # http://localhost:5173
```

Open <http://localhost:5173> and sign in. With the default `.env` this runs in
[demo mode](#demo-mode) and needs no Discord application.

### Connecting a real Discord application

1. Create an application at <https://discord.com/developers/applications>.
2. **OAuth2 → Redirects**: add `http://localhost:8000/api/auth/callback`.
3. **Bot**: create the bot, copy the token, and enable the **Server Members Intent**
   (without it `on_member_join` never fires).
4. Invite the bot with the `bot` scope and the **Manage Roles** and **Send Messages**
   permissions, and make sure its role sits *above* any role it should assign.
5. Fill `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_BOT_TOKEN` in `backend/.env`
   and set `DEMO_MODE=false`.
6. Start the gateway bot alongside the API:

```bash
make bot
```

### Switching to PostgreSQL

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/discord_automation
```

No code changes: connection arguments are chosen from the URL scheme.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` enables the startup safety checks |
| `DEMO_MODE` | `true` | serve mock Discord data; refused in production |
| `DISCORD_CLIENT_ID` | — | OAuth2 application ID |
| `DISCORD_CLIENT_SECRET` | — | OAuth2 application secret |
| `DISCORD_BOT_TOKEN` | — | bot token, used for all guild operations |
| `DISCORD_REDIRECT_URI` | `http://localhost:8000/api/auth/callback` | must match the portal exactly |
| `DATABASE_URL` | `sqlite:///./discord_automation.db` | any SQLAlchemy URL |
| `SESSION_SECRET` | dev placeholder | signs sessions, derives the token-encryption key |
| `SESSION_TTL_MINUTES` | `10080` | session cookie lifetime |
| `COOKIE_SECURE` | `false` | set `true` behind HTTPS |
| `COOKIE_SAMESITE` | `lax` | `none` (with `COOKIE_SECURE=true`) when the dashboard is on another domain |
| `WEBHOOK_SECRET` | dev placeholder | HMAC key for `/api/webhooks/custom` |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin and post-login redirect |

`.env` is git-ignored; `.env.example` is the template. No secret is committed.

---

## API overview

Interactive documentation: <http://localhost:8000/docs>.

| Method | Route | Auth | Notes |
|---|---|---|---|
| `GET` | `/api/health` | public | status, mode, database |
| `GET` | `/api/auth/mode` | public | live or demo |
| `GET` | `/api/auth/login` | public | redirects to Discord with a signed state cookie |
| `GET` | `/api/auth/callback` | public | exchanges the code, issues the session |
| `POST` | `/api/auth/logout` | session | clears the cookie |
| `POST` | `/api/auth/refresh-guilds` | session | re-syncs guild access from Discord |
| `GET` | `/api/me` | session | current user (never tokens) |
| `GET` | `/api/guilds` | session | servers, with `manageable` per server |
| `GET` | `/api/guilds/{guild_id}` | membership | dashboard payload: roles, channels, settings, stats |
| `GET` | `/api/guilds/{guild_id}/settings` | membership | automation settings |
| `PATCH` | `/api/guilds/{guild_id}/settings` | **Manage Server** | partial update, IDs validated against the guild |
| `GET` | `/api/guilds/{guild_id}/logs` | membership | paged, filterable audit trail |
| `POST` | `/api/guilds/{guild_id}/verify` | membership (self) / **Manage Server** (others) | runs verification |
| `POST` | `/api/guilds/{guild_id}/roles/add` | **Manage Server** | assigns a role |
| `POST` | `/api/guilds/{guild_id}/roles/remove` | **Manage Server** | removes a role |
| `POST` | `/api/webhooks/custom` | HMAC signature | external event → audit trail (+ optional message) |

Status codes are used as intended: `401` unauthenticated, `403` authenticated but not
permitted, `404` for a guild the caller cannot see (so the API never confirms a server's
existence to an outsider), `409` when Discord would refuse the action, `422` for validation
failures, `429` when rate limited.

**Calling the webhook**

```bash
BODY='{"event":"deployment","guild_id":"<guild id>","message":"v1.4.0 shipped"}'
SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | cut -d' ' -f1)"

curl -X POST http://localhost:8000/api/webhooks/custom \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY"
```

---

## Security notes

- **Tokens never reach the browser.** The OAuth access and refresh tokens are encrypted with
  Fernet before they are stored and are used only server side. The browser holds an HttpOnly,
  SameSite session cookie containing a signed JWT with a user ID — nothing else.
- **Separate keys from one secret.** The session-signing key and the token-encryption key are
  derived from `SESSION_SECRET` through HKDF with different info labels, so the two never
  share key material.
- **CSRF on the OAuth round trip.** `state` is random per attempt, stored in a short-lived
  HttpOnly cookie scoped to `/api/auth`, and compared in constant time.
- **Permissions are re-checked, not remembered.** Guild membership and permission bitfields
  are re-read from Discord on every login and can be re-synced on demand; stale memberships
  are deleted. `ADMINISTRATOR` implies everything, exactly as Discord treats it.
- **Two-sided checks before any mutation.** The caller must hold Manage Server *and* the bot
  must be present, hold `MANAGE_ROLES`, and outrank the target role. Integration-managed
  roles and `@everyone` are rejected outright.
- **Webhooks are verified before parsing.** The HMAC is computed over the exact bytes
  received and compared with `hmac.compare_digest`; oversized bodies are refused.
- **Production refuses unsafe configuration.** With `ENVIRONMENT=production`, the app will
  not start with demo mode on, a weak `SESSION_SECRET`, or missing Discord credentials.
- **Audit trail records failures too.** A refused or failed automation writes
  `automation_failed`, so a silent no-op is never mistaken for success.
- Responses carry `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and
  `Cache-Control: no-store`; CORS allows exactly one origin with credentials.

---

## Demo mode

Discord credentials are optional. With `DEMO_MODE=true` (the default) the backend swaps the
live REST client for a mock implementing the same interface: three servers, their roles and
channels, and a demo sign-in that skips the Discord round trip.

What demo mode does **not** do is invent activity. Role changes and verifications performed
in demo mode are recorded in the real database and shown in the real audit trail — the
numbers on screen are the ones the session produced. Every response reports its mode
(`GET /api/health`), the dashboard states it in a banner on every page, and
`ENVIRONMENT=production` refuses to boot with demo mode enabled.

---

## Tests

```bash
make test        # or: cd backend && .venv/bin/python -m pytest
```

49 tests covering the parts worth protecting:

- every guild route rejects an anonymous caller; a tampered cookie is refused
- a forged OAuth `state` never produces a session
- Manage Server is required for writes; a guild the caller cannot see returns 404
- settings reject blank messages, malformed snowflakes, unknown fields, and IDs belonging
  to a different server
- role automation refuses managed roles and unknown roles
- webhooks reject unsigned, mis-signed and malformed payloads
- rate limits trigger, report `Retry-After`, and stay scoped per route

---

## Project structure

```
backend/
  app/
    api/
      deps.py            session → user → membership → permission chain
      routes/            auth, users, guilds, automation, webhooks, system
    bot/                 discord.py gateway client (python -m app.bot)
    core/                config, security (JWT/Fernet/HMAC), rate limiting, permissions
    db/                  engine, session, declarative base
    models/              User, Guild, GuildMembership, GuildSettings, AutomationLog
    schemas/             Pydantic request/response models
    services/            Discord gateway (live + demo), automation, audit, guild sync
    main.py              app wiring: middleware, error handlers, routers
  tests/                 pytest suite
frontend/
  src/
    components/          AppShell, LogTable, GuildIcon, StatTile + ui/ primitives
    context/             auth provider and hook
    hooks/               useAsync
    lib/                 API client, shared types, formatting helpers
    pages/               Login, Dashboard, ServerDetail, ServerLogs, Settings
docs/screenshots/        README images
.env.example             every variable, documented
Makefile                 install / api / bot / web / test
```

---

## Deployment

There is no hosted instance; the project is set up to deploy as separate processes:

- **API:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` with `ENVIRONMENT=production`. The app refuses to start in production if `DEMO_MODE` is on, `SESSION_SECRET` is weak or the Discord credentials are missing.
- **Web:** `cd frontend && npm ci && npm run build` produces a static `dist/`. Serve it from the same origin as the API (proxy `/api` to it), or set `VITE_API_BASE_URL`.
- **Bot:** `python -m app.bot` with `DISCORD_BOT_TOKEN` is a separate process sharing the database with the API.
- **Database:** `DATABASE_URL` takes any SQLAlchemy URL. The project is developed and tested on SQLite.
- **Cookies:** serve the web app and the API from the same site (for example `app.example.com` and `api.example.com`) so the SameSite session cookie is sent, and set `COOKIE_SECURE=true` behind HTTPS.

## Project status

Complete portfolio project. Runs end to end in demo mode; the live Discord path needs a bot token and an OAuth2 application. CI runs the backend tests and the dashboard build on every push.

## Licence

MIT — see [LICENSE](LICENSE).
