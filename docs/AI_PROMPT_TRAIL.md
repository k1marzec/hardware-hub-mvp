# Prompt trail — architecture & design

This is a curated history of the **prompts that shaped the system**, not a full chat dump. Each entry notes what the ask was and what landed in the product.

---



## 1. MVP skeleton

**Ask:** Senior-fullstack style brief: create `backend/` + `frontend/`; FastAPI + SQLAlchemy + SQLite and Vue 3 / Vite / Tailwind; Device model matching `hardware_data.json`; seed from JSON + demo admin; mock login; admin CRUD; recreate Login / Hardware List / Admin UI from screenshots `@booksy.com` validation);

**Result:** Working closed loop: seed DB, login page (`@booksy.com`), Hardware List, Admin panel, basic API.

---



## 2. Closed system & accounts

**Ask:** Only admins may create accounts; User model with hashed passwords; `POST /api/users`; Admin tabs Hardware / Users; no public register button.

**Result:** Real bcrypt login; Manage Accounts as the only way in.

---



## 3. Rental engine (hard guards)

**Ask:** `POST …/rent` and `…/return` with server-side status checks; UI Rent / Return / disabled by status and ownership.

**Result:** Status machine `Available` ↔ `In Use`, `Repair` blocked. Later hardened with atomic `UPDATE … WHERE` after race findings.

---



## 4. Smart dashboard

**Ask:** Sorting and filtering on the hardware list (status, brand, category; sortable headers).

**Result:** Client-side toolbar + shared composables (`useDeviceFilters`, `useRowHighlight`) reused in Admin → Hardware (filters only; sort stays on Hardware List).

---



## 5. Inventory Auditor (Zero-UI → interactive)

**Ask:** `GET /api/auditor/run` with a strict system prompt; Admin “AI Health Check” then renamed Inventory Auditor; structured JSON tiles; “Create service history” via `POST …/resolve-issue`.

**Result:** OpenRouter + `openai` SDK; actionable tiles; lemon detection; prompt rules: ignore `history` / `notes`, act only on open `issue`; duplicate `serialNumber` checks.

---



## 6. Field model: `issue` vs `notes` vs `history`

**Ask:** Defect text for the auditor must live in `issue`; free-form admin text in `notes`; `history` is a log only and must not drive findings; lemon warning goes to `notes`.

**Result:** Schema rename, seed refresh, prompt rewrite, README migration note (delete old `hardware.db`).

---



## 7. Security hardening

**Ask:** SAST-style review (OWASP: BOLA/IDOR, mass assignment, validation, data exposure), then implement fixes #1 and #2 (real auth + role assignment).

**Result:** Signed session tokens (`itsdangerous`), `Depends(get_current_user)` / `require_admin`, rent/return/rentals identity from token, `Literal` roles in Pydantic.

---



## 8. Tests & cleanup

**Ask:** Backend pytest suite (~80%+ coverage); frontend Vitest; extract duplicated filter/highlight logic; English-only UI/docs; accurate README.

**Result:** 76 backend tests (100% on `main.py` + `auditor.py` with mocked AI); Vitest for stores/composables/API/StatusBadge; README + this prompt trail.

---

