"""Shared pytest fixtures/helpers for the backend test suite.

Key ideas:
- Every test gets a brand-new, fully isolated in-memory SQLite database via
  dependency-override of `get_db` - tests never touch the real
  `backend/hardware.db` file and never leak state into one another.
- `run_seed()` (which normally runs on FastAPI startup and would otherwise
  create/seed the real `hardware.db`) is disabled for the test app.
- Every endpoint requires a valid, signed session token now (see
  `auth.py`), so the `client` fixture bootstraps one admin account directly
  in the DB (bypassing the API, the same way `run_seed()` does in
  production) and logs in as them, setting that token as the client's
  *default* `Authorization` header. Tests therefore act as an admin unless
  they explicitly override the header (see `auth_headers()`/`login()`) to
  exercise a specific non-admin user or an unauthenticated request.
- The OpenRouter/OpenAI client used by `auditor.py` is mocked for *every*
  test automatically (autouse `llm` fixture below), so the whole suite is
  free, deterministic, and can never make a real network call - even by
  accident. Tests that exercise an AI-powered code path opt in to a
  specific canned response via `llm(content=..., error=..., ...)`.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auditor
import main
import models
import security
from database import get_db

BOOTSTRAP_ADMIN_EMAIL = "bootstrap-admin@booksy.com"
BOOTSTRAP_ADMIN_PASSWORD = "bootstrap-admin-password"


@pytest.fixture()
def db_session_factory():
    """A sessionmaker bound to a fresh, isolated in-memory SQLite database.

    `StaticPool` is required so every connection made from this engine
    shares the *same* in-memory database - by default, each new SQLite
    connection would otherwise get its own empty `:memory:` database,
    which would make writes from one session invisible to another.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield testing_session_local
    models.Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(db_session_factory, monkeypatch):
    """A `TestClient` wired to the isolated in-memory DB instead of the real
    `backend/hardware.db`, with startup seeding disabled, and logged in as a
    bootstrap admin by default (see module docstring)."""
    monkeypatch.setattr(main, "run_seed", lambda: None)

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db

    # There's no "become the first admin" API by design (closed system) -
    # in production that first account comes from `run_seed()`, which is
    # disabled for tests, so we insert it directly here instead.
    bootstrap_session = db_session_factory()
    try:
        bootstrap_session.add(
            models.User(
                email=BOOTSTRAP_ADMIN_EMAIL,
                hashed_password=security.hash_password(BOOTSTRAP_ADMIN_PASSWORD),
                role="admin",
            )
        )
        bootstrap_session.commit()
    finally:
        bootstrap_session.close()

    with TestClient(main.app) as test_client:
        token = login(test_client, BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD)
        test_client.headers.update(auth_headers(token))
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def llm(monkeypatch):
    """Mocks the OpenRouter/OpenAI client used by `auditor.py` for *every*
    test, so nothing in the suite ever makes a real, billable network call.

    Returns a `configure(...)` callable a test can use to set up the next
    `chat.completions.create(...)` response:
    - `llm(content="...")` - a normal text/JSON response.
    - `llm(error=SomeException("..."))` - the API call itself raises.
    - `llm(raw_response=some_object)` - full control over the returned
      object, e.g. to simulate a malformed SDK response missing `.choices`.
    - `llm(side_effect=callable)` - full control via a custom callable,
      e.g. to simulate another request mutating the DB mid-flight (race
      condition tests).

    If a test reaches this client without configuring it first, the mock
    raises loudly instead of silently attempting a real API call.
    """
    fake_client = MagicMock()

    def _unconfigured(*_args, **_kwargs):
        raise AssertionError(
            "This test reached the OpenRouter/OpenAI client without "
            "configuring a fake response first - call the `llm(...)` fixture."
        )

    fake_client.chat.completions.create.side_effect = _unconfigured

    monkeypatch.setattr(auditor, "OpenAI", MagicMock(return_value=fake_client))
    monkeypatch.setattr(auditor, "OPENROUTER_API_KEY", "test-key-not-real")

    def configure(content=None, error=None, raw_response=None, side_effect=None):
        create_mock = fake_client.chat.completions.create
        create_mock.side_effect = None
        create_mock.return_value = None

        if side_effect is not None:
            create_mock.side_effect = side_effect
        elif error is not None:
            create_mock.side_effect = error
        elif raw_response is not None:
            create_mock.return_value = raw_response
        else:
            create_mock.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )
        return fake_client

    return configure


def login(client, email, password):
    """Logs in through the public API and returns the signed session token.

    Note: pass a `client` that is *not* relying on its own default
    Authorization header for this call - login itself never requires one,
    so any client works, including the default admin-authenticated one.
    """
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth_headers(token):
    """`Authorization` header dict for a given session token, to override a
    `client` fixture's default (admin) header on a specific request, e.g.
    `client.get(path, headers=auth_headers(some_users_token))`."""
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email, password, role="user"):
    """Helper: creates a user account through the (admin-only) public API -
    the passed-in `client` must already be authenticated as an admin (true
    for the default `client` fixture)."""
    response = client.post(
        "/api/users", json={"email": email, "password": password, "role": role}
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_device(client, **overrides):
    """Helper: creates a device through the public API with sane defaults
    for every field, returns the parsed JSON response."""
    payload = {
        "name": "Test Laptop",
        "brand": "Dell",
        "category": "Laptop",
        "serialNumber": "SN-TEST-0001",
        "purchaseDate": "2024-01-01",
        "status": "Available",
    }
    payload.update(overrides)
    response = client.post("/api/devices", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
