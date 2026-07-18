# Hardware Management System — MVP

System do zarządzania sprzętem firmowym (wypożyczenia, panel admina, status
urządzeń). Obejmuje kompletny CRUD, "Rental Engine" z twardą walidacją stanów,
zamknięty system logowania z rolami (`admin`/`user`) oraz "Inventory Auditor"
— proaktywny skan bazy sprzętu w poszukiwaniu anomalii (OpenAI przez
OpenRouter), z akcją "jednym kliknięciem AI" Predictive Maintenance
("Create service history" — zgłoszona usterka staje się wpisem w historii +
statusem "Repair").

## Stos technologiczny

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vue 3 (`<script setup>`, Composition API), Vite, Tailwind CSS
- **Inventory Auditor:** model OpenAI routowany przez [OpenRouter](https://openrouter.ai) (`openai` SDK jako klient wskazujący na OpenRouter, Chat Completions API)

## Struktura projektu

```
hardware_hub_booksy/
├── backend/
│   ├── main.py            # Endpointy REST API
│   ├── models.py          # Modele SQLAlchemy (Device, User)
│   ├── schemas.py         # Schematy Pydantic
│   ├── database.py        # Konfiguracja SQLite + sesji (ścieżka absolutna)
│   ├── security.py        # Hashowanie haseł (passlib + bcrypt)
│   ├── auditor.py          # Inventory Auditor: skan anomalii przez OpenRouter
│   ├── seed.py             # Wgrywa hardware_data.json + konto demo admina
│   ├── hardware_data.json  # Kopia danych startowych
│   ├── .env                # OPENROUTER_API_KEY / OPENROUTER_MODEL (NIE commitować!)
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── views/          # LoginView, HardwareListView, MyRentalsView, AdminPanelView
    │   ├── components/     # Sidebar, StatusBadge, DeviceModal, AdminHardwareTab,
    │   │                   # AdminUsersTab, CreateUserModal, AiHealthCheck, ...
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
starcie serwera (dzięki `seed.py` wywoływanemu w `lifespan` handlerze
aplikacji FastAPI). Można też wywołać seed ręcznie:

```bash
python seed.py
```

> **Aktualizacja schematu:** jeśli masz już plik `backend/hardware.db` z
> wcześniejszej wersji projektu (kolumna `password` zamiast
> `hashed_password` w `users`, brak kolumny `notes` w `devices`, albo stara
> kolumna `notes` w miejscu dzisiejszego `issue`), usuń go przed ponownym
> startem serwera — SQLAlchemy nie robi automatycznych migracji, a stary
> schemat jest niekompatybilny z nowym modelem.

API dostępne pod `http://localhost:8000`, dokumentacja Swaggera pod
`http://localhost:8000/docs`.

### Inventory Auditor ("Zero-UI") — konfiguracja (OpenRouter)

Zapytania AI nie idą bezpośrednio do OpenAI — przechodzą przez
[OpenRouter](https://openrouter.ai), które udostępnia modele OpenAI (i inne)
pod jednym, ujednoliconym API zgodnym z klientem `openai`. `backend/.env`
musi więc zawierać klucz API **z OpenRouter** (do wygenerowania na
[openrouter.ai/keys](https://openrouter.ai/keys) — **nie** klucz
`sk-...` z platform.openai.com, tylko klucz OpenRouter), oraz nazwę modelu w
formacie OpenRouter (z prefiksem dostawcy, np. `openai/gpt-4o-mini` dla
modelu OpenAI dostępnego przez OpenRouter):

```
OPENROUTER_API_KEY=twoj-klucz-api-z-openrouter
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Backend (`backend/auditor.py`) tworzy klienta `OpenAI(...)` z pakietu
`openai`, ale z `base_url` wskazującym na `https://openrouter.ai/api/v1` —
to jedyna różnica względem wywoływania OpenAI bezpośrednio, więc cała
pozostała logika (system prompty, `response_format: json_object`, obsługa
błędów) działa bez zmian.

Backend (`GET /api/auditor/run`) skanuje **całą** bazę
`devices` w poszukiwaniu anomalii: sprzęt oznaczony jako "Available", mimo
notatek/historii o naprawie/uszkodzeniu, daty zakupu z przyszłości, brakujące
dane, błędy w nazwach marek. Wynik to **ustrukturyzowany
JSON** (nie wolny tekst) generowany jednym zapytaniem przez OpenRouter
(`response_format: json_object`) — cały inwentarz trafia do modelu jako JSON
w jednej wiadomości, ze ściśle zdefiniowanym system promptem. Odpowiedź jest
podzielona na kategorie (np. "🔴 Critical Business Risks"), a każdy problem
(`issue`) może być powiązany z konkretnym urządzeniem (`device_id`) i
oznaczony jako `actionable`, jeśli da się go rozwiązać automatycznie.

Frontend (`AiHealthCheck.vue`, widoczny wyłącznie w **Admin Panel**) wywołuje
ten endpoint automatycznie po wejściu do panelu (`onMounted`), pokazuje
spinner "AI is analyzing inventory records…", a po odpowiedzi renderuje
kafelki pogrupowane w kategorie — z opcją ponownego uruchomienia skanu lub
zamknięcia karty.

Każdy `issue` audytu ma pole `actionable`, które mówi UI, czy pokazać na
kafelku przycisk "Create service history":

**"Naprawa Sprzętu" / Predictive Maintenance — przycisk "Create service history"
(`actionable: true`):** pokazuje się dla urządzeń ze statusem innym
niż `"Repair"` i **niepustym polem `issue`** opisującym realną, otwartą
usterkę. Kolumna `history` to tylko dziennik zdarzeń ("co już zrobiono ze
sprzętem") i nigdy sama nie uruchamia tego przycisku — nawet jeśli audytor
wykryje w niej wzmiankę o defekcie, zgłosi to jako nieakcjonowalną notatkę
informacyjną. Kliknięcie wywołuje `POST /api/devices/{id}/resolve-issue`, który:
1. Wysyła treść pola `issue` przez OpenRouter (do modelu OpenAI) z promptem proszącym o wygenerowanie
   krótkiego, profesjonalnego wpisu do historii sprzętu (**bez** szacowania
   liczby dni naprawy — tylko fakt zgłoszenia i wysłania do serwisu).
2. Zapisuje wygenerowany tekst w kolumnie `history` (z datą, w nowej linii).
3. Zmienia `status` urządzenia na `"Repair"` i czyści `issue` (problem uznany
   za zgłoszony/rozwiązany).
4. **"Lemon" detection:** po zapisie liczy, ile razy w kolumnie `history`
   występuje bieżący rok (np. `"2026"`). Jeśli 3 lub więcej razy, wpisuje (o
   ile jest wtedy puste) w niezależne pole `notes` ostrzeżenie: *"⚠️ UWAGA:
   Urządzenie awaryjne. Wymagało serwisu 3 lub więcej razy w tym roku."* —
   sygnał dla admina, że sprzęt regularnie się psuje, bez konieczności
   czytania całej historii. Ostrzeżenie ląduje w `notes`, a nie w `issue`,
   żeby nie zostało błędnie zinterpretowane przez Inventory Auditor jako nowa,
   otwarta usterka do naprawy.

Inne anomalie wykryte przez audytora (literówki w marce/nazwie, błędne daty,
brakujące dane, nierozpoznane statusy) są tylko informacyjne (`actionable:
false`) — nie ma dla nich automatycznej akcji naprawczej.

Po sukcesie kafelek płynnie znika z widoku (`<TransitionGroup>`, Local State
Mutation — bez przeładowania całego raportu), a tabela sprzętu w zakładce
"Hardware" odświeża się automatycznie.

Bez skonfigurowanego `OPENROUTER_API_KEY` obie ścieżki (`/api/auditor/run`,
`/api/devices/{id}/resolve-issue`) zwrócą błąd `502` z czytelnym komunikatem.

## Uruchomienie — Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplikacja wystartuje na `http://localhost:5173` i komunikuje się z
backendem pod adresem zdefiniowanym w `frontend/.env`
(`VITE_API_URL=http://localhost:8000/api`).

## Logowanie — system zamknięty (Closed System)

Nie istnieje żadna rejestracja/self-service sign-up. Jedynym sposobem
uzyskania dostępu do systemu jest utworzenie konta przez admina w zakładce
**Admin Panel → Users**. Hasła są hashowane (`passlib` + `bcrypt`) i
przechowywane w tabeli `users`; logowanie fizycznie porównuje hash w bazie.

- **Admin (seed):** `demo@booksy.com` / `demo123` — pełny dostęp do
  "Admin Panel".
- **User (seed):** `user@booksy.com` / `user123` — zwykłe konto (rola
  `user`), tworzone automatycznie przez `seed.py` do testów "Hardware List" /
  "My Rentals" bez dostępu do panelu admina.
- **Nowi użytkownicy:** admin tworzy konta w zakładce "Users" (pola Email,
  Password oraz **Role** — `user` albo `admin`). Konta z rolą `user` mają
  dostęp tylko do "Hardware List" i "My Rentals"; konta z rolą `admin` mają
  pełny dostęp do "Admin Panel" (Hardware, Users, Inventory Auditor).

Frontend waliduje domenę email (`@booksy.com`) po stronie klienta; backend
dodatkowo weryfikuje to samo (przy logowaniu i przy tworzeniu konta) jako
zabezpieczenie.

## Rental Engine — twarda walidacja stanów (Guards)

Statusy urządzenia: `Available` → (Rent) → `In Use` → (Return) → `Available`,
oraz `Repair` jako stan wyłączony z wypożyczeń. Walidacja jest wymuszona
**po stronie backendu**, nie tylko w UI:

- `POST /api/devices/{id}/rent` — 409, jeśli urządzenie ma status `Repair`
  lub `In Use`. W przeciwnym razie ustawia `In Use` i `assignedTo`.
- `POST /api/devices/{id}/return` — 409, jeśli urządzenie nie ma statusu
  `In Use`. W przeciwnym razie ustawia `Available` i czyści `assignedTo`.

Przycisk w "Hardware List" jest dynamiczny: "Rent" (Available), "Return"
(In Use i przypisane do zalogowanego użytkownika), lub disabled (Repair,
albo In Use przypisane do kogoś innego).

**Bezpieczeństwo przy równoczesnych żądaniach (race conditions):** guard nie
jest osobnym `SELECT` + sprawdzeniem w Pythonie, a częścią jednego atomowego
zapytania `UPDATE ... WHERE status = ...`. Dzięki temu, gdy dwie osoby klikną
"Rent" na tym samym urządzeniu w tej samej chwili, tylko jedno żądanie
rzeczywiście zmieni wiersz w bazie (0 zmienionych wierszy dla drugiego =
odrzucenie z `409`) — bez tego zabezpieczenia druga osoba mogłaby po cichu
nadpisać przypisanie pierwszej (obie dostałyby odpowiedź `200`, ale w bazie
zostałaby tylko jedna z nich). Ten sam wzorzec (atomowy `UPDATE` z warunkiem
w `WHERE` sprawdzającym, że kolumna(y) wciąż mają wartość odczytaną przed
zapytaniem do AI) chroni też `POST /api/devices/{id}/resolve-issue`, gdzie
okno na race jest jeszcze większe (trwa całe zapytanie przez OpenRouter).
Zweryfikowane testem: 10 równoczesnych żądań "Rent"/"Return" na tym samym
urządzeniu → zawsze dokładnie 1 sukces, reszta `409`.

## Smart Dashboard — wyszukiwanie, filtrowanie, sortowanie

Zarówno "Hardware List" jak i "Admin Panel → Hardware" mają pasek narzędzi
nad tabelą: wyszukiwanie po nazwie/marce, filtr statusu (`All`, `Available`,
`In Use`, `Repair`), filtr marki oraz filtr kategorii (`Category` — oba
generowane dynamicznie z danych), z przyciskiem "Clear filters" widocznym,
gdy jakiś filtr jest aktywny. W "Hardware List" nagłówki kolumn (Name,
Brand, Category, Purchase Date) są klikalne i sortują tabelę
rosnąco/malejąco (z ikoną strzałki wskazującą aktywne sortowanie). Logika
filtrowania/sortowania działa po stronie frontendu.

Tabela w "Admin Panel → Hardware" pokazuje dodatkowo kolumny `Assigned To`,
`Issue`, `Notes` i `History` — długi tekst w ostatnich trzech zawija się, a
po przekroczeniu ~10 linii przewija się wewnętrznie (nie rozciąga wiersza).

## Endpointy API

| Metoda | Ścieżka                        | Opis                                   |
|--------|---------------------------------|-----------------------------------------|
| POST   | `/api/auth/login`               | Logowanie (weryfikacja hasha w DB)      |
| GET    | `/api/users`                     | Lista kont użytkowników (Admin)         |
| POST   | `/api/users`                     | Utworzenie nowego konta z rolą `user`/`admin` (Admin) |
| GET    | `/api/devices`                  | Lista urządzeń                          |
| GET    | `/api/devices/{id}`             | Szczegóły urządzenia                    |
| POST   | `/api/devices`                  | Dodanie urządzenia (Admin)              |
| PUT    | `/api/devices/{id}`             | Edycja urządzenia, w tym `issue`/`notes`/`history` (Admin) |
| DELETE | `/api/devices/{id}`             | Usunięcie urządzenia (Admin)            |
| PATCH  | `/api/devices/{id}/repair`      | Ustawienie statusu "Repair" (Admin)     |
| PATCH  | `/api/devices/{id}/restore`      | Przywrócenie z "Repair" do "Available" (Admin) |
| POST   | `/api/devices/{id}/rent`        | Wypożyczenie urządzenia (atomowy guard, nie z "Repair"/"In Use") |
| POST   | `/api/devices/{id}/return`      | Zwrot urządzenia (atomowy guard, tylko z "In Use") |
| GET    | `/api/rentals?email=...`        | Lista wypożyczeń danego użytkownika     |
| GET    | `/api/auditor/run`                | Inventory Auditor — skan anomalii, zwraca kategorie/kafelki z `actionable` (OpenRouter) |
| POST   | `/api/devices/{id}/resolve-issue` | "Create service history" — generuje wpis do historii, ustawia status "Repair", czyści `issue`, + Lemon detection (OpenRouter, atomowy guard) |
| GET    | `/api/health`                     | Health-check (status serwera)           |

> Uwaga: logowanie realnie weryfikuje email + hash hasła w tabeli `users`,
> ale nie ma jeszcze prawdziwego JWT/sesji (token zwracany przez
> `/api/auth/login` jest placeholderem) — wystarczające dla zakresu MVP.
> Ograniczenie dostępu do Admin Panelu odbywa się na poziomie UI (router
> guard) na podstawie roli zwróconej przy logowaniu; endpointy `/api/users`
> i CRUD urządzeń nie są jeszcze chronione po stronie serwera.
