# OmniCare

Consent-first healthcare platform. This repo currently contains the
**authentication vertical slice**: registration, login, session restore, token
refresh, and an authenticated profile fetch — frontend to database, no mocks.

## Stack

| Layer    | Choice                                             |
| -------- | -------------------------------------------------- |
| Frontend | React 19 + Vite, plain JS, Axios, React Router 7    |
| Backend  | Flask 3, SQLAlchemy 2, Alembic, Flask-JWT-Extended  |
| Database | SQLite in dev (`DATABASE_URL` swaps to Postgres)    |

## Running it

Two terminals.

**Backend** — http://127.0.0.1:5000

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # optional in dev; required in production
.venv/bin/flask --app wsgi db upgrade
.venv/bin/python wsgi.py
```

**Frontend** — http://localhost:5173

```bash
npm install
npm run dev
```

The frontend reads `VITE_API_BASE_URL` (see `.env.example`) and defaults to
`http://127.0.0.1:5000/api`.

Note: email addresses on reserved TLDs (`.test`, `.local`, `.invalid`) are
rejected by validation. Use a real domain when trying the signup form.

## API

| Method | Path                 | Auth    | Purpose                      |
| ------ | -------------------- | ------- | ---------------------------- |
| GET    | `/api/health`        | –       | Liveness                     |
| POST   | `/api/auth/register` | –       | Create account, issue tokens |
| POST   | `/api/auth/login`    | –       | Authenticate, issue tokens   |
| POST   | `/api/auth/refresh`  | refresh | New access token             |
| GET    | `/api/auth/me`       | access  | Current user                 |

Responses are uniform: `{"data": ...}` on success, `{"message": ..., "errors":
{...}}` on failure. `errors` is keyed by form field so the UI renders messages
inline.

## Project layout

```
backend/
  app/
    __init__.py        app factory, CORS, JSON error handlers
    config.py          env-driven config
    models/user.py     User model, scrypt hashing
    auth/routes.py     register / login / refresh / me
    auth/schemas.py    request validation
  migrations/          Alembic
  wsgi.py
src/
  lib/api.js           Axios instance, token refresh, error normalisation
  services/            backend calls, grouped by domain
  context/AuthContext.jsx
  pages/               Register, Login, Dashboard
```

## Database changes

Models live in `backend/app/models/`. After editing one:

```bash
cd backend
.venv/bin/flask --app wsgi db migrate -m "what changed"
.venv/bin/flask --app wsgi db upgrade
```

Review the generated migration before committing — Alembic autogenerate does
not reliably detect column renames or type narrowing.

The dev database is a local artifact and is **not** tracked in git. Delete
`backend/instance/omnicare.db` and re-run `db upgrade` for a clean slate.

## Security notes

Passwords are hashed with scrypt (`werkzeug`, cost 32768:8:1). `ProductionConfig`
refuses to boot if `SECRET_KEY` or `JWT_SECRET_KEY` are still the dev defaults.
CORS is an explicit origin allowlist, never `*`.

## Known gaps

- **Token storage.** Tokens are in `localStorage`, readable by any script that
  achieves XSS. Should move to httpOnly + `Secure` + `SameSite` cookies with
  CSRF protection before real patient data is handled.
- **No token revocation.** Sign-out is a client-side discard; a stolen token
  stays valid until it expires. Needs a server-side JTI denylist.
- **No rate limiting** on `/auth/login` or `/auth/register` — open to
  credential stuffing and signup spam.
- **No email verification**, so addresses are unproven.
- **No automated tests.** The flow was verified by driving a real browser; that
  needs to become a committed pytest + Playwright suite.

## Not yet built

Doctors, reports, appointments, pharmacy, Omni AI, rides, disease intelligence,
and consent management are not implemented. Auth is the foundation they attach
to.
