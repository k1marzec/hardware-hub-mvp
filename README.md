# Hardware Management System — MVP

System do zarządzania sprzętem firmowym (wypożyczenia, panel admina, status
urządzeń). MVP obejmuje kompletny CRUD i UI zgodny z przekazanymi
mock-upami — logika inteligentnego asystenta ("Ask AI") zostanie dodana w
kolejnej iteracji.

## Stos technologiczny

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vue 3 (`<script setup>`, Composition API), Vite, Tailwind CSS

## Struktura projektu

```
hardware_hub_booksy/
├── backend/
│   ├── main.py            # Endpointy REST API
│   ├── models.py          # Modele SQLAlchemy (Device, User)
│   ├── schemas.py         # Schematy Pydantic
│   ├── database.py        # Konfiguracja SQLite + sesji
│   ├── seed.py             # Wgrywa hardware_data.json + konto demo admina
│   ├── hardware_data.json  # Kopia danych startowych
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── views/          # LoginView, HardwareListView, MyRentalsView, AdminPanelView
    │   ├── components/     # Sidebar, StatusBadge, DeviceModal
    │   ├── layouts/         # DashboardLayout (sidebar + router-view)
    │   ├── stores/auth.js   # Prosty store sesji (localStorage)
    │   ├── services/api.js  # Klient REST (fetch)
    │   └── router/index.js
    ├── package.json
    └── tailwind.config.js
```

## Uruchomienie — Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Baza `hardware.db` oraz konto demo admina są tworzone automatycznie przy
starcie serwera (dzięki `seed.py` wywoływanemu w evencie `startup`). Można
też wywołać seed ręcznie:

```bash
python seed.py
```

API dostępne pod `http://localhost:8000`, dokumentacja Swaggera pod
`http://localhost:8000/docs`.

## Uruchomienie — Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplikacja wystartuje na `http://localhost:5173` i komunikuje się z
backendem pod adresem zdefiniowanym w `frontend/.env`
(`VITE_API_URL=http://localhost:8000/api`).

## Logowanie demo

- **Admin:** `demo@booksy.com` / `demo123` — pełny dostęp do "Admin Panel".
- **Zwykły użytkownik:** dowolny email z domeny `@booksy.com` (np.
  `j.doe@booksy.com`) z dowolnym niepustym hasłem — loguje jako rola `user`
  (bez dostępu do Admin Panel). Dzięki temu można od razu zobaczyć
  wypożyczenie słuchawek Sony przypisane do `j.doe@booksy.com` w "My Rentals".

Frontend waliduje domenę email (`@booksy.com`) już po stronie klienta;
backend dodatkowo weryfikuje to samo jako zabezpieczenie.

## Endpointy API

| Metoda | Ścieżka                        | Opis                                   |
|--------|---------------------------------|-----------------------------------------|
| POST   | `/api/auth/login`               | Mock logowania                          |
| GET    | `/api/devices`                  | Lista urządzeń                          |
| GET    | `/api/devices/{id}`             | Szczegóły urządzenia                    |
| POST   | `/api/devices`                  | Dodanie urządzenia (Admin)              |
| PUT    | `/api/devices/{id}`             | Edycja urządzenia (Admin)               |
| DELETE | `/api/devices/{id}`             | Usunięcie urządzenia (Admin)            |
| PATCH  | `/api/devices/{id}/repair`      | Ustawienie statusu "Repair" (Admin)     |
| POST   | `/api/devices/{id}/rent`        | Wypożyczenie urządzenia                 |
| POST   | `/api/devices/{id}/return`      | Zwrot urządzenia                        |
| GET    | `/api/rentals?email=...`        | Lista wypożyczeń danego użytkownika     |

> Uwaga: autoryzacja jest zamockowana (brak JWT/sesji) — wystarczająca dla
> zakresu MVP. Ograniczenie dostępu do Admin Panelu odbywa się na poziomie
> UI (router guard) na podstawie roli zwróconej przy logowaniu.
