"""Tests for Auth/Security, Users, Hardware CRUD, and the Rental Engine
(hard state guards) in `main.py`.

The Inventory Auditor / AI-powered endpoints are covered separately in
`test_auditor.py`. See `conftest.py` for the shared `client` fixture (an
isolated in-memory-SQLite-backed TestClient, logged in as a bootstrap admin
by default), the `login()`/`auth_headers()` helpers used to act as a
*different*, specific user, and the `llm` autouse fixture that guarantees no
real network call ever happens.
"""

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
import models
import security
from conftest import (
    BOOTSTRAP_ADMIN_EMAIL,
    BOOTSTRAP_ADMIN_PASSWORD,
    auth_headers,
    create_device,
    login,
    register_user,
)
from database import get_db

# --------------------------------------------------------------------------
# Auth & Security
# --------------------------------------------------------------------------


def test_login_rejects_non_booksy_domain(client):
    response = client.post(
        "/api/auth/login", json={"email": "someone@gmail.com", "password": "whatever"}
    )
    assert response.status_code == 400
    assert "booksy.com" in response.json()["detail"]


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/auth/login", json={"email": "ghost@booksy.com", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_rejects_wrong_password(client):
    register_user(client, "wronged@booksy.com", "correct-password")
    response = client.post(
        "/api/auth/login", json={"email": "wronged@booksy.com", "password": "not-it"}
    )
    assert response.status_code == 401
    # Same generic message for "unknown email" and "wrong password" - must
    # never leak which one it was.
    assert response.json()["detail"] == "Invalid email or password"


def test_login_success_returns_user_and_token(client):
    register_user(client, "success@booksy.com", "s3cretpw!", role="admin")
    response = client.post(
        "/api/auth/login", json={"email": "success@booksy.com", "password": "s3cretpw!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "success@booksy.com"
    assert body["user"]["role"] == "admin"
    assert body["token"]
    # A real, signed token - not the old `f"mock-token-{email}"` placeholder.
    assert "success@booksy.com" not in body["token"]


def test_login_domain_check_is_case_insensitive(client):
    register_user(client, "case@booksy.com", "pw123456")
    response = client.post(
        "/api/auth/login", json={"email": "CASE@Booksy.com", "password": "pw123456"}
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------
# Session tokens (auth.py)
# --------------------------------------------------------------------------


def test_request_without_authorization_header_returns_401(client):
    # `client` is pre-authenticated by default (see conftest.py) - clearing
    # the header for this one request simulates a caller that never logged
    # in at all, while still using the isolated test DB (never the real one).
    response = client.get("/api/devices", headers={"Authorization": ""})
    assert response.status_code == 401


def test_request_with_malformed_authorization_header_returns_401(client):
    response = client.get("/api/devices", headers={"Authorization": "not-a-bearer-token"})
    assert response.status_code == 401


def test_request_with_tampered_token_returns_401(client):
    real_token = login(client, BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD)
    tampered = real_token[:-1] + ("A" if real_token[-1] != "A" else "B")
    response = client.get("/api/devices", headers=auth_headers(tampered))
    assert response.status_code == 401


def test_request_with_token_for_deleted_user_returns_401(client, db_session_factory):
    register_user(client, "temp@booksy.com", "pw123456")
    token = login(client, "temp@booksy.com", "pw123456")

    session = db_session_factory()
    try:
        user = session.query(models.User).filter(models.User.email == "temp@booksy.com").first()
        session.delete(user)
        session.commit()
    finally:
        session.close()

    response = client.get("/api/devices", headers=auth_headers(token))
    assert response.status_code == 401


# --------------------------------------------------------------------------
# Users (accounts management - the only way to gain access to the system)
# --------------------------------------------------------------------------


def test_create_user_rejects_non_booksy_domain(client):
    response = client.post(
        "/api/users", json={"email": "nope@gmail.com", "password": "password1"}
    )
    assert response.status_code == 400


def test_create_user_rejects_duplicate_email(client):
    register_user(client, "dup@booksy.com", "password1")
    response = client.post(
        "/api/users", json={"email": "dup@booksy.com", "password": "password2"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_user_rejects_invalid_role(client):
    # `role` is a Pydantic `Literal["user", "admin"]` now (schemas.py) - an
    # unrecognized value is rejected as a 422 validation error before the
    # handler even runs, not a handwritten 400 check inside it.
    response = client.post(
        "/api/users",
        json={"email": "badrole@booksy.com", "password": "password1", "role": "superadmin"},
    )
    assert response.status_code == 422


def test_create_user_rejects_short_password(client):
    response = client.post(
        "/api/users", json={"email": "shortpw@booksy.com", "password": "short"}
    )
    assert response.status_code == 422


def test_create_user_defaults_role_to_user(client):
    user = register_user(client, "defaultrole@booksy.com", "password1")
    assert user["role"] == "user"


def test_create_user_can_set_admin_role(client):
    user = register_user(client, "admin2@booksy.com", "password1", role="admin")
    assert user["role"] == "admin"


def test_create_user_response_never_includes_password_hash(client):
    user = register_user(client, "nopeek@booksy.com", "password1")
    assert "hashed_password" not in user
    assert "password" not in user


def test_list_users_returns_created_accounts(client):
    register_user(client, "one@booksy.com", "password1")
    register_user(client, "two@booksy.com", "password2", role="admin")
    response = client.get("/api/users")
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert {"one@booksy.com", "two@booksy.com"} <= emails


def test_non_admin_cannot_list_users(client):
    register_user(client, "plainuser@booksy.com", "password1")
    token = login(client, "plainuser@booksy.com", "password1")
    response = client.get("/api/users", headers=auth_headers(token))
    assert response.status_code == 403


def test_non_admin_cannot_create_user(client):
    """Guards against privilege escalation: a regular user hitting the
    account-creation endpoint themselves (e.g. to mint their own admin
    account) must be rejected, not just hidden from the UI."""
    register_user(client, "plainuser2@booksy.com", "password1")
    token = login(client, "plainuser2@booksy.com", "password1")
    response = client.post(
        "/api/users",
        json={"email": "newadmin@booksy.com", "password": "password1", "role": "admin"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------
# Hardware CRUD
# --------------------------------------------------------------------------


def test_list_devices_starts_empty(client):
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert response.json() == []


def test_create_device_defaults_purchase_date_when_missing(client):
    response = client.post("/api/devices", json={"name": "No Date Laptop", "brand": "Acer"})
    assert response.status_code == 201
    body = response.json()
    assert body["purchaseDate"]  # auto-filled with today's date
    assert body["status"] == "Available"


def test_get_device_by_id(client):
    device = create_device(client, name="Get Me")
    response = client.get(f"/api/devices/{device['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Me"


def test_get_device_not_found(client):
    response = client.get("/api/devices/9999")
    assert response.status_code == 404


def test_update_device_partial_fields_only_touches_provided_ones(client):
    device = create_device(client, name="Old Name", brand="OldBrand")
    response = client.put(f"/api/devices/{device['id']}", json={"name": "New Name"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["brand"] == "OldBrand"  # untouched (exclude_unset)


def test_update_device_not_found(client):
    response = client.put("/api/devices/9999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_delete_device(client):
    device = create_device(client)
    response = client.delete(f"/api/devices/{device['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/devices/{device['id']}").status_code == 404


def test_delete_device_not_found(client):
    response = client.delete("/api/devices/9999")
    assert response.status_code == 404


def test_send_to_repair_and_restore_round_trip(client):
    device = create_device(client)

    repaired = client.patch(f"/api/devices/{device['id']}/repair")
    assert repaired.status_code == 200
    assert repaired.json()["status"] == "Repair"

    restored = client.patch(f"/api/devices/{device['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "Available"
    assert restored.json()["assignedTo"] is None


def test_send_to_repair_not_found(client):
    assert client.patch("/api/devices/9999/repair").status_code == 404


def test_restore_from_repair_not_found(client):
    assert client.patch("/api/devices/9999/restore").status_code == 404


# --------------------------------------------------------------------------
# Hardware CRUD - non-admin access is rejected (BOLA/IDOR fix)
# --------------------------------------------------------------------------


def test_non_admin_can_list_and_get_devices(client):
    """Reading hardware is fine for any authenticated user (the Hardware
    List dashboard) - only *writes* are admin-only."""
    device = create_device(client)
    register_user(client, "reader@booksy.com", "password1")
    token = login(client, "reader@booksy.com", "password1")

    assert client.get("/api/devices", headers=auth_headers(token)).status_code == 200
    assert (
        client.get(f"/api/devices/{device['id']}", headers=auth_headers(token)).status_code
        == 200
    )


def test_non_admin_cannot_create_device(client):
    register_user(client, "writer@booksy.com", "password1")
    token = login(client, "writer@booksy.com", "password1")
    response = client.post(
        "/api/devices", json={"name": "Sneaky Laptop"}, headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_non_admin_cannot_update_device(client):
    device = create_device(client)
    register_user(client, "writer2@booksy.com", "password1")
    token = login(client, "writer2@booksy.com", "password1")
    response = client.put(
        f"/api/devices/{device['id']}",
        json={"name": "Hacked"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_non_admin_cannot_delete_device(client):
    device = create_device(client)
    register_user(client, "writer3@booksy.com", "password1")
    token = login(client, "writer3@booksy.com", "password1")
    response = client.delete(f"/api/devices/{device['id']}", headers=auth_headers(token))
    assert response.status_code == 403


def test_non_admin_cannot_send_to_repair(client):
    device = create_device(client)
    register_user(client, "writer4@booksy.com", "password1")
    token = login(client, "writer4@booksy.com", "password1")
    response = client.patch(
        f"/api/devices/{device['id']}/repair", headers=auth_headers(token)
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------
# Rental Engine - hard state guards (Rent / Return)
# --------------------------------------------------------------------------


def test_rent_available_device_happy_path(client):
    device = create_device(client, status="Available")
    register_user(client, "renter@booksy.com", "pw123456")
    token = login(client, "renter@booksy.com", "pw123456")

    response = client.post(f"/api/devices/{device['id']}/rent", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "In Use"
    assert body["assignedTo"] == "renter@booksy.com"


def test_rent_ignores_email_in_request_body(client):
    """Regression test for the Mass Assignment / impersonation bug: the
    renter must always be the *authenticated* caller, never a value the
    client can put in the request body."""
    device = create_device(client, status="Available")
    register_user(client, "realrenter@booksy.com", "pw123456")
    token = login(client, "realrenter@booksy.com", "pw123456")

    response = client.post(
        f"/api/devices/{device['id']}/rent",
        json={"email": "someone-else@booksy.com"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["assignedTo"] == "realrenter@booksy.com"


def test_rent_device_in_repair_returns_409(client):
    device = create_device(client, status="Repair")
    response = client.post(f"/api/devices/{device['id']}/rent")
    assert response.status_code == 409
    assert "Repair" in response.json()["detail"]


def test_rent_device_already_in_use_returns_409(client):
    device = create_device(client, status="In Use", assignedTo="other@booksy.com")
    response = client.post(f"/api/devices/{device['id']}/rent")
    assert response.status_code == 409
    # The rejected attempt must never clobber the existing assignment.
    assert (
        client.get(f"/api/devices/{device['id']}").json()["assignedTo"]
        == "other@booksy.com"
    )


def test_rent_device_not_found(client):
    response = client.post("/api/devices/9999/rent")
    assert response.status_code == 404


def test_return_device_happy_path(client):
    register_user(client, "owner@booksy.com", "pw123456")
    token = login(client, "owner@booksy.com", "pw123456")
    device = create_device(client, status="In Use", assignedTo="owner@booksy.com")

    response = client.post(f"/api/devices/{device['id']}/return", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Available"
    assert body["assignedTo"] is None


def test_return_device_forbidden_for_non_owner(client):
    """A regular user may only return a device assigned to *themselves* -
    fixes the IDOR where anyone could return (and thus free up / reassign)
    any device regardless of who actually has it."""
    register_user(client, "notmine@booksy.com", "pw123456")
    token = login(client, "notmine@booksy.com", "pw123456")
    device = create_device(client, status="In Use", assignedTo="someoneelse@booksy.com")

    response = client.post(f"/api/devices/{device['id']}/return", headers=auth_headers(token))
    assert response.status_code == 403
    # Must remain untouched.
    assert client.get(f"/api/devices/{device['id']}").json()["status"] == "In Use"


def test_admin_can_force_return_any_device(client):
    """Admins are allowed to bypass the ownership check (e.g. an employee
    left without returning their gear)."""
    device = create_device(client, status="In Use", assignedTo="someoneelse@booksy.com")
    response = client.post(f"/api/devices/{device['id']}/return")  # default admin client
    assert response.status_code == 200
    assert response.json()["status"] == "Available"


def test_return_device_not_in_use_returns_409(client):
    device = create_device(client, status="Available")
    response = client.post(f"/api/devices/{device['id']}/return")
    assert response.status_code == 409


def test_return_device_not_found(client):
    response = client.post("/api/devices/9999/return")
    assert response.status_code == 404


def test_rent_then_return_round_trip(client):
    device = create_device(client, status="Available")
    device_id = device["id"]
    client.post(f"/api/devices/{device_id}/rent")
    response = client.post(f"/api/devices/{device_id}/return")
    assert response.status_code == 200
    assert response.json()["status"] == "Available"


def test_my_rentals_filters_by_assigned_email(client):
    create_device(client, name="Mine", status="In Use", assignedTo="me@booksy.com")
    create_device(client, name="Not Mine", status="In Use", assignedTo="other@booksy.com")
    register_user(client, "me@booksy.com", "pw123456")
    token = login(client, "me@booksy.com", "pw123456")

    response = client.get("/api/rentals", headers=auth_headers(token))
    assert response.status_code == 200
    assert [d["name"] for d in response.json()] == ["Mine"]


def test_concurrent_rent_requests_only_one_succeeds(monkeypatch):
    """Verifies the atomic `UPDATE ... WHERE status NOT IN (...)` guard:
    firing several simultaneous "Rent" requests at the same Available
    device must result in exactly one 200 and the rest 409 - the guard is
    part of the UPDATE itself, not a separate read-then-check-then-write
    that two threads could both pass at once.

    Uses its own temp-file-backed SQLite DB (with a real per-connection
    pool + a busy `timeout`), rather than the shared in-memory `client`
    fixture: a single shared `:memory:` connection isn't safe for genuine
    multi-threaded concurrent writes, which would make this test flaky for
    reasons unrelated to the guard being tested. A busy timeout makes
    SQLite queue up concurrent writers instead of instantly erroring out,
    so every request still gets a clean 200/409 - matching how the real
    file-backed `hardware.db` behaves under concurrent requests.
    """
    monkeypatch.setattr(main, "run_seed", lambda: None)

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = None
    try:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        models.Base.metadata.create_all(bind=engine)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def override_get_db():
            db = session_local()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db
        with TestClient(main.app) as test_client:
            # Bootstrap + log in an admin directly, same as the `client`
            # fixture does, since every endpoint needs a real token now.
            bootstrap_db = session_local()
            try:
                bootstrap_db.add(
                    models.User(
                        email="concurrency-admin@booksy.com",
                        hashed_password=security.hash_password("irrelevant-password"),
                        role="admin",
                    )
                )
                bootstrap_db.commit()
            finally:
                bootstrap_db.close()

            token = login(test_client, "concurrency-admin@booksy.com", "irrelevant-password")
            test_client.headers.update(auth_headers(token))

            device = create_device(test_client, status="Available")
            device_id = device["id"]

            def attempt(_n):
                return test_client.post(f"/api/devices/{device_id}/rent").status_code

            with ThreadPoolExecutor(max_workers=10) as pool:
                results = list(pool.map(attempt, range(10)))

        assert results.count(200) == 1
        assert results.count(409) == 9
    finally:
        main.app.dependency_overrides.clear()
        if engine is not None:
            engine.dispose()  # release the file handle before removing it (Windows)
        try:
            os.remove(db_path)
        except OSError:
            pass  # best-effort cleanup of the temp file; not test-critical


# --------------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------------


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
