"""FastAPI application exposing the Hardware Management REST API.

This is a *closed system*: there is no self-service sign-up. The only way to
obtain a login is for an admin to create an account via `POST /api/users`
(surfaced in the Admin Panel's "Users" tab, itself admin-only). Login
performs a real lookup + bcrypt hash comparison against the `users` table.

Every endpoint that reads or writes user/device data requires a valid,
signed session token (`Authorization: Bearer <token>`, see `auth.py`) via
`Depends(get_current_user)`; admin-only endpoints additionally require
`Depends(require_admin)`. Ownership is enforced server-side too, not just
in the UI - e.g. `rent`/`return` always use the *caller's* email from their
token, never a client-supplied value, and a non-admin can only return a
device currently assigned to themselves.
"""

from contextlib import asynccontextmanager
from datetime import date
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, literal, or_, update
from sqlalchemy.orm import Session

import models
import schemas
import security
from auditor import AuditorError, resolve_device_issue, run_audit
from auth import create_session_token, get_current_user, require_admin
from database import get_db
from seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates tables (if needed) and loads hardware_data.json + demo admin
    # the very first time the API starts, so `uvicorn main:app` alone is
    # enough to get a working, populated backend. Using the `lifespan`
    # parameter (rather than the deprecated `@app.on_event("startup")`)
    # since it's the officially supported hook going forward.
    run_seed()
    yield


app = FastAPI(title="Hardware Management API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()

    if not email.endswith("@booksy.com"):
        raise HTTPException(
            status_code=400, detail="Invalid domain. Please use @booksy.com"
        )

    user = db.query(models.User).filter(models.User.email == email).first()

    # Closed system: no account -> no access. Same generic error is used for
    # "unknown email" and "wrong password" so we don't leak which one it was.
    if user is None or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return schemas.LoginResponse(
        user=schemas.UserOut.model_validate(user),
        token=create_session_token(user.id),
    )


# --------------------------------------------------------------------------
# Users - accounts management (Admin "Manage Accounts")
# --------------------------------------------------------------------------


@app.get("/api/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    return db.query(models.User).order_by(models.User.id).all()


@app.post("/api/users", response_model=schemas.UserOut, status_code=201)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    email = payload.email.lower()

    if not email.endswith("@booksy.com"):
        raise HTTPException(
            status_code=400, detail="Invalid domain. Please use @booksy.com"
        )

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    # `payload.role` is a Pydantic `Literal["user", "admin"]` (schemas.py) -
    # anything else is already rejected as a 422 before this line runs, so
    # there's no free-text role value here to blindly trust/assign.
    user = models.User(
        email=email,
        hashed_password=security.hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------
# Devices - read
# --------------------------------------------------------------------------


@app.get("/api/devices", response_model=List[schemas.DeviceOut])
def list_devices(db: Session = Depends(get_db), _user: models.User = Depends(get_current_user)):
    return db.query(models.Device).order_by(models.Device.id).all()


@app.get("/api/devices/{device_id}", response_model=schemas.DeviceOut)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# --------------------------------------------------------------------------
# Devices - admin CRUD
# --------------------------------------------------------------------------


@app.post("/api/devices", response_model=schemas.DeviceOut, status_code=201)
def create_device(
    payload: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    data = payload.model_dump()
    if not data.get("purchaseDate"):
        data["purchaseDate"] = date.today().isoformat()

    device = models.Device(**data)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@app.put("/api/devices/{device_id}", response_model=schemas.DeviceOut)
def update_device(
    device_id: int,
    payload: schemas.DeviceUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, key, value)

    db.commit()
    db.refresh(device)
    return device


@app.delete("/api/devices/{device_id}", status_code=204)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()
    return None


@app.patch("/api/devices/{device_id}/repair", response_model=schemas.DeviceOut)
def send_to_repair(
    device_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "Repair"
    db.commit()
    db.refresh(device)
    return device


@app.patch("/api/devices/{device_id}/restore", response_model=schemas.DeviceOut)
def restore_from_repair(
    device_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """Reverses "Send to Repair": puts the device back into the Available pool."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "Available"
    device.assignedTo = None
    db.commit()
    db.refresh(device)
    return device


# --------------------------------------------------------------------------
# Devices - rental engine (Rent / Return) with hard state guards
# --------------------------------------------------------------------------
#
# Valid transitions:
#   Available -> (rent)   -> In Use
#   In Use    -> (return) -> Available
#
# Any other starting state is rejected with a 400 so the frontend can never
# push a device into an inconsistent state, even if a stale UI tries to.
#
# Concurrency note: the guard MUST be part of the same atomic UPDATE
# statement, not a separate SELECT-then-check-then-write. A naive
# "read device -> check device.status in Python -> write" sequence has a
# race window: if two requests for the *same* device both read the row
# before either one writes, both will see "Available" and both will think
# they're allowed to proceed, silently overwriting one another (the second
# writer wins, the first user gets back a 200 for a rental they don't
# actually have). Folding the guard into the UPDATE's WHERE clause makes the
# check-and-set a single atomic operation as far as the database is
# concerned: whichever request's UPDATE actually executes first "wins" and
# flips the status, so the second request's WHERE no longer matches (0 rows
# updated) and it correctly gets rejected instead of clobbering the first.

# Statuses from which a device can never be rented directly.
RENT_BLOCKED_STATUSES = {"Repair", "In Use"}


@app.post("/api/devices/{device_id}/rent", response_model=schemas.DeviceOut)
def rent_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # The renter is always the *authenticated* caller - never a
    # client-supplied email in the request body - so nobody can rent a
    # device on someone else's behalf by editing the JSON payload.
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    result = db.execute(
        update(models.Device)
        .where(
            models.Device.id == device_id,
            models.Device.status.notin_(RENT_BLOCKED_STATUSES),
        )
        .values(status="In Use", assignedTo=user.email)
    )
    db.commit()

    if result.rowcount == 0:
        # Someone else's request won the race (or the device was already in
        # a blocked state to begin with) - refresh to report its real status.
        db.refresh(device)
        raise HTTPException(
            status_code=409,
            detail=f"Device cannot be rented while its status is '{device.status}'",
        )

    db.refresh(device)
    return device


@app.post("/api/devices/{device_id}/return", response_model=schemas.DeviceOut)
def return_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # Ownership guard: a regular user may only return a device currently
    # assigned to *themselves* - admins can force-return any device (e.g.
    # an employee who left without returning it). Folded into the same
    # atomic WHERE as the status check, for the same race-condition reasons
    # documented above.
    conditions = [models.Device.id == device_id, models.Device.status == "In Use"]
    if user.role != "admin":
        conditions.append(models.Device.assignedTo == user.email)

    result = db.execute(
        update(models.Device).where(*conditions).values(status="Available", assignedTo=None)
    )
    db.commit()

    if result.rowcount == 0:
        db.refresh(device)
        if (
            device.status == "In Use"
            and user.role != "admin"
            and (device.assignedTo or "").lower() != user.email.lower()
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only return a device assigned to you",
            )
        raise HTTPException(
            status_code=409,
            detail=f"Device cannot be returned because its status is '{device.status}', not 'In Use'",
        )

    db.refresh(device)
    return device


@app.get("/api/rentals", response_model=List[schemas.DeviceOut])
def my_rentals(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # Always the caller's own rentals - previously this took an arbitrary
    # `email` query parameter, letting anyone enumerate any other user's
    # rented devices (IDOR). Nothing in the UI ever needed "someone else's"
    # rentals: admins already see every device's `assignedTo` via
    # GET /api/devices.
    return (
        db.query(models.Device)
        .filter(models.Device.assignedTo == user.email)
        .order_by(models.Device.id)
        .all()
    )


# --------------------------------------------------------------------------
# Inventory Auditor - "Zero-UI" proactive anomaly scan (see auditor.py)
# --------------------------------------------------------------------------
#
# Actionable tiles -> resolve_issue() ("Create service history" / Predictive
# Maintenance): a real physical defect described in `issue` gets turned into
# a repair ticket (status -> Repair, history stamped). Every other anomaly
# (bad dates, missing brand, brand typos, ...) is informational-only - there
# is no automated fix action for those.

# "Lemon" detection: if a device's `history` has been stamped 3+ times with
# a date from the current year, it's a repeat offender - flag it in the
# free-form `notes` field (NEVER `issue`, since `issue` is what drives the AI
# Health Check / "Create service history" - a lemon warning must not look
# like a fresh, actionable defect to the auditor) so admins see the warning
# immediately instead of having to read the whole history log to notice the
# pattern.
LEMON_THRESHOLD = 3
LEMON_WARNING = "\u26A0\uFE0F WARNING: Failure-prone device. Serviced 3 or more times this year."


@app.get("/api/auditor/run", response_model=schemas.AuditorReportResponse)
def run_auditor(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    devices = db.query(models.Device).order_by(models.Device.id).all()
    devices_data = [schemas.DeviceOut.model_validate(d).model_dump() for d in devices]

    try:
        result = run_audit(devices_data)
    except AuditorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - last-resort guard for an external API
        raise HTTPException(
            status_code=502, detail=f"The auditor is temporarily unavailable: {exc}"
        ) from exc

    return schemas.AuditorReportResponse(**result)


@app.post("/api/devices/{device_id}/resolve-issue", response_model=schemas.DeviceOut)
def resolve_issue(
    device_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """"Create service history": the interactive counterpart to the passive AI
    Health Check report. Takes one device flagged with an open `issue`, asks
    the model to turn that description into a professional repair-ticket
    history entry, then applies the resulting lifecycle transition: status
    -> "Repair", `issue` cleared, history appended with a dated entry.
    """
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # `history` is only a log of past actions, not an open issue - only a
    # non-empty `issue` field represents a current defect this action can
    # actually resolve. (Mirrors the "actionable" rule in auditor.py.)
    defect_text = (device.issue or "").strip()
    if not defect_text:
        raise HTTPException(
            status_code=400,
            detail="This device has no issue description to resolve",
        )

    try:
        generated_entry = resolve_device_issue(device.name, defect_text)
    except AuditorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - last-resort guard for an external API
        raise HTTPException(
            status_code=502, detail=f"The AI service is temporarily unavailable: {exc}"
        ) from exc

    if not generated_entry:
        generated_entry = f"Issue reported: {defect_text}. Device sent to service for repair."

    stamped_entry = f"[{date.today().isoformat()}] {generated_entry}"

    # The OpenRouter call above can take a second or more - plenty of time for a
    # concurrent request (another "Create service history" click, or a manual edit)
    # to change this same device. Two safeguards, both evaluated by the DB
    # at write time rather than relying on the `device` object read before
    # the AI call:
    #   1. WHERE issue == defect_text - only apply if nobody else already
    #      resolved/edited this exact issue in the meantime (0 rows updated
    #      means we lost the race, so we reject instead of overwriting).
    #   2. history is appended via a SQL CASE/concat expression against the
    #      row's current value, not the possibly-stale `device.history`
    #      captured earlier - so a concurrent history edit isn't clobbered.
    history_expr = case(
        (
            or_(models.Device.history.is_(None), models.Device.history == ""),
            literal(stamped_entry),
        ),
        else_=models.Device.history + literal("\n" + stamped_entry),
    )

    result = db.execute(
        update(models.Device)
        .where(models.Device.id == device_id, models.Device.issue == defect_text)
        .values(status="Repair", issue="", history=history_expr)
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail="This device's issue was already resolved or changed - please refresh and try again.",
        )

    db.refresh(device)

    # Lemon detection runs after the fact, against the *actual* stored
    # history text (not the possibly-stale value read before the AI call),
    # so it always reflects the real, current count. The warning goes into
    # `notes` (never `issue`) so it's just a visible admin note, not a new
    # "defect" the Inventory Auditor would pick back up.
    current_year = str(date.today().year)
    if (device.history or "").count(current_year) >= LEMON_THRESHOLD:
        db.execute(
            update(models.Device)
            .where(
                models.Device.id == device_id,
                or_(models.Device.notes.is_(None), models.Device.notes == ""),
            )
            .values(notes=LEMON_WARNING)
        )
        db.commit()
        db.refresh(device)

    return device


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
