# Hardware Hub Booksy — MVP

App for managing company hardware: rent devices, admin panel, user roles, and an AI **Inventory Auditor** (OpenAI through OpenRouter).

**Tech:** Python/FastAPI, SQLite · Vue 3, Vite, Tailwind · OpenRouter

---

## Quick start

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Copy .env.example → .env, then set OPENROUTER_API_KEY and SESSION_SECRET_KEY
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

- API: `http://localhost:8000`



### Demo logins

Created automatically on first start:


| Email             | Password  | Role  |
| ----------------- | --------- | ----- |
| `demo@booksy.com` | `demo123` | admin |
| `user@booksy.com` | `user123` | user  |


- Emails must end with `@booksy.com`.
- **Login page** checks the domain in the browser and again on the server.
- **Create user** (admin form) does **not** check the domain in the browser — only the server does.
- Nobody can sign up themselves. Only an admin can create accounts.

If you upgrade from an older version and the app breaks, delete `backend/hardware.db` and restart (the DB schema is not migrated automatically).

### AI setup (Inventory Auditor)

Put this in `backend/.env`:

```env
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o-mini
SESSION_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
```

Get the API key from [openrouter.ai/keys](https://openrouter.ai/keys) (OpenRouter key, not a normal OpenAI key).

Optional (rarely needed):

```env
# OPENROUTER_SITE_URL=http://localhost:5173
# OPENROUTER_SITE_NAME=Hardware Hub Booksy
```

---



## What works


| Area                  | Details                                                                                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Login & roles**     | Passwords are hashed. Login returns a signed token. The frontend sends it as `Authorization: Bearer …`. The API checks who you are and whether you are an admin.     |
| **Users**             | Only admins can list or create users. Role is only `user` or `admin` (invalid roles are rejected).                                                                   |
| **Hardware**          | Admins can add, edit, delete devices; send to repair / mark available again. Fields include `issue`, `notes`, `history`, serial number, category.                    |
| **Rent / return**     | Safe updates so two people cannot rent the same device at once. You rent as yourself (from your token). You can only return your own device (admins can return any). |
| **Filters & sort**    | Search + filters by status / brand / category on Hardware List and Admin → Hardware. Clickable column sort only on Hardware List.                                    |
| **Inventory Auditor** | AI scans the inventory for problems (e.g. available but broken, bad dates, brand typos, duplicate serial numbers). Useful items show **Create service history**.     |
| **Service history**   | That button writes an AI history note, sets status to `Repair`, clears `issue`. If the device was serviced 3+ times this year, a warning is stored in `notes`.       |
| **Tests**             | Backend: 76 pytest tests on `main.py` and `auditor.py` (AI is mocked). Frontend: Vitest for filters, row highlight, auth store, API helper, StatusBadge. |

### Device statuses

`Available` → **Rent** → `In Use` → **Return** → `Available`

You cannot rent a device that is already `In Use` or in `Repair`.

### Main API routes


| Method              | Path                                    | Who       | What                   |
| ------------------- | --------------------------------------- | --------- | ---------------------- |
| POST                | `/api/auth/login`                       | anyone    | Login                  |
| GET / POST          | `/api/users`                            | admin     | List / create users    |
| GET                 | `/api/devices`…                         | logged in | List / view devices    |
| POST / PUT / DELETE | `/api/devices`…                         | admin     | Manage devices         |
| PATCH               | `/api/devices/{id}/repair` or `restore` | admin     | Repair on/off          |
| POST                | `/api/devices/{id}/rent` or `return`    | logged in | Rent / return          |
| GET                 | `/api/rentals`                          | logged in | My rentals             |
| GET                 | `/api/auditor/run`                      | admin     | Run AI scan            |
| POST                | `/api/devices/{id}/resolve-issue`       | admin     | Create service history |
| GET                 | `/api/health`                           | anyone    | Is the server up?      |




### Run tests

```bash
# Backend
cd backend && pip install -r requirements-dev.txt
pytest --cov=main --cov=auditor --cov-report=term-missing

# Frontend
cd frontend && npm run test
```

---

## Shortcuts we took (and why)

Things built the simple way for this MVP.

### 1. Session token in `localStorage`

- **What:** After login, the token is stored in the browser and sent on each request.
- **Why:** Real login checks on the server without a full JWT / cookie setup.
- **Later:** Shorter-lived tokens, secure cookies, refresh tokens, forced logout.

### 2. SQLite file, no migrations

- **What:** One local database file. Schema changes mean delete the DB and re-seed.
- **Why:** Easy local demo. Seed data covers many edge cases.
- **Later:** Proper migrations; a bigger database (e.g. Postgres) if needed.

### 3. Filters and sort in the browser

- **What:** Filtering (and sorting on Hardware List) happens in the UI on the full list.
- **Why:** Small inventory; keeps the API simple.
- **Later:** Filtering/sorting/pagination on the server when the list gets large.

### 4. Missing session secret

- **What:** If `SESSION_SECRET_KEY` is empty, the server makes a random one at start. Restart logs everyone out.
- **Why:** App still runs for a first demo with almost no setup.
- **Later:** Require the secret in production.

### 5. AI does most of the audit

- **What:** One AI call returns a JSON report. Extra Python code cleans up messy answers.
- **Why:** Quick Inventory Auditor feature; easy to change models via OpenRouter.
- **Later:** Hard checks in code for duplicates/dates/statuses; use AI mainly for free-text issues.

### 6. “Lemon” (repeat offender) detection

- **What:** Counts how often the current year appears in `history` text. If ≥ 3, write a warning into `notes`.
- **Why:** No separate service-events table yet.
- **Later:** Real dated service records and a clearer rule.

---

## Not finished / cut

| Item | Note |
|------|------|
| AI “fix data” button (typos / dates) | Removed. Those findings are info-only. |
| Ask-AI chat | Removed. Only the Inventory Auditor uses AI. |
| Logout API / token revoke / refresh | Not built |
| DB migrations / deploy setup | Manual DB reset only |
| Password reset / invite emails | Out of scope (admins create accounts) |

---

## If we had one more day

1. **GitHub Actions CI** — run backend pytest and frontend tests (and `npm run build`) on every PR so broken main is caught before merge.
2. **Autonomous Inventory Auditor** — scheduled run with no admin clicks: safe findings auto-apply; notify admin for the rest.
3. **Decision log** — store each AI action (device, finding, before/after) so autonomous changes are reviewable.

---

## AI development log

How AI tools were used on this project — and where human judgment overrode them.

### Tooling

| Tool | Role |
|------|------|
| **Cursor** (Agent chat) | Main coding partner: scaffolding, refactors, tests, docs, security review prompts |
| **Google Gemini** (early) | Extra help planning prompts and product decisions |
| **OpenRouter** + OpenAI-compatible SDK | Final path for Inventory Auditor (`OPENROUTER_API_KEY`, models like `openai/gpt-4o-mini`) |

### Data strategy

- **Source of truth:** `backend/hardware_data.json` loaded by `seed.py` into SQLite on first start.
- **Schema drift:** Renaming free-text “notes” into a real defect field (`issue`) plus a separate `notes` column broke old DBs (`no such column: devices.issue`). Fix was intentional: delete `hardware.db`, re-seed — not a silent AI migration.
- **AI + data audit:** Seed data was rewritten so the auditor can be tested by hand — e.g. battery swelling on `Available`, brand typo `Appel`, future purchase dates, status `Unknown`, long `history` that must **not** create findings, lemon candidates, and **duplicate serials** (`SN-DUPLICATE-001` on two rows).
- **What AI got wrong on data:** Early prompts let the model treat `history` as open defects (“history mentions past damage…”). That was wrong for the product. We tightened the system prompt (ignore `history` / `notes`) and checked the seed so empty-`issue` devices stay quiet.
- **Takeaway:** AI is useful for inventing edge-case rows; a human still has to check field meaning (`issue` vs `notes` vs `history`) and that the seed matches the schema after every rename.

### Prompt trail

Curated history of the asks that shaped architecture and design:

→ **[docs/AI_PROMPT_TRAIL.md](docs/AI_PROMPT_TRAIL.md)**

(MVP → closed accounts → rental guards → dashboard → AI experiments → Inventory Auditor → `issue`/`notes` model → security hardening → tests.)

### The “correction”

AI proposed a login that returned a fake token `mock-token-{email}` with no verification on the API side. Admin endpoints were public; the UI only hid them. I caught this in a security review I requested via a prompt. We fixed it: signed sessions, FastAPI dependencies for user/admin, identity taken from the token, a strict role, and tests that run as a logged-in user.

---

## Folder layout

```
docs/
  AI_PROMPT_TRAIL.md          # curated AI prompt history (architecture)
backend/
  main.py auth.py auditor.py models.py schemas.py security.py database.py seed.py
  hardware_data.json test_*.py conftest.py pytest.ini
  requirements.txt requirements-dev.txt .env.example
frontend/
  src/views/ components/ composables/ layouts/ stores/ services/ router/
  package.json vite.config.js   # npm run test
```

The Inventory Auditor UI file is still called `AiHealthCheck.vue` (old name); the screen title is **Inventory Auditor**.

The frontend may call the API from `http://localhost:5173` or `http://127.0.0.1:5173`.

Do not commit `backend/.env` or `hardware.db`.

