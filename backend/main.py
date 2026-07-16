"""FastAPI application exposing the Hardware Management REST API.

This is a *closed system*: there is no self-service sign-up. The only way to
obtain a login is for an admin to create an account via `POST /api/users`
(surfaced in the Admin Panel's "Users" tab). Login performs a real lookup +
bcrypt hash comparison against the `users` table — no more mock fallback.

There is still no JWT/session infra (the "token" returned by login is a
placeholder string) and Admin-only endpoints aren't enforced server-side —
access to the Admin Panel is gated at the UI level based on the logged-in
user's role. That's an acceptable trade-off for this MVP's scope, but would
need to be hardened (real tokens + server-side role checks) before shipping
to production.
"""

from datetime import date
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
import security
from database import get_db
from seed import run_seed

app = FastAPI(title="Hardware Management API", version="1.0.0")

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


@app.on_event("startup")
def on_startup() -> None:
    # Creates tables (if needed) and loads hardware_data.json + demo admin
    # the very first time the API starts, so `uvicorn main:app` alone is
    # enough to get a working, populated backend.
    run_seed()


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
        token=f"mock-token-{email}",
    )


# --------------------------------------------------------------------------
# Users - accounts management (Admin "Manage Accounts")
# --------------------------------------------------------------------------


@app.get("/api/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id).all()


@app.post("/api/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()

    if not email.endswith("@booksy.com"):
        raise HTTPException(
            status_code=400, detail="Invalid domain. Please use @booksy.com"
        )

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    user = models.User(
        email=email,
        hashed_password=security.hash_password(payload.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------
# Devices - read
# --------------------------------------------------------------------------


@app.get("/api/devices", response_model=List[schemas.DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).order_by(models.Device.id).all()


@app.get("/api/devices/{device_id}", response_model=schemas.DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# --------------------------------------------------------------------------
# Devices - admin CRUD
# --------------------------------------------------------------------------


@app.post("/api/devices", response_model=schemas.DeviceOut, status_code=201)
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db)):
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
    device_id: int, payload: schemas.DeviceUpdate, db: Session = Depends(get_db)
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
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()
    return None


@app.patch("/api/devices/{device_id}/repair", response_model=schemas.DeviceOut)
def send_to_repair(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "Repair"
    db.commit()
    db.refresh(device)
    return device


@app.patch("/api/devices/{device_id}/restore", response_model=schemas.DeviceOut)
def restore_from_repair(device_id: int, db: Session = Depends(get_db)):
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

# Statuses from which a device can never be rented directly.
RENT_BLOCKED_STATUSES = {"Repair", "In Use"}


@app.post("/api/devices/{device_id}/rent", response_model=schemas.DeviceOut)
def rent_device(
    device_id: int, payload: schemas.RentRequest, db: Session = Depends(get_db)
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # Guard: can't rent hardware that's being repaired or already checked out.
    if device.status in RENT_BLOCKED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Device cannot be rented while its status is '{device.status}'",
        )

    device.status = "In Use"
    device.assignedTo = payload.email.lower()
    db.commit()
    db.refresh(device)
    return device


@app.post("/api/devices/{device_id}/return", response_model=schemas.DeviceOut)
def return_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # Guard: only a device that's actually checked out can be returned.
    if device.status != "In Use":
        raise HTTPException(
            status_code=400,
            detail=f"Device cannot be returned because its status is '{device.status}', not 'In Use'",
        )

    device.status = "Available"
    device.assignedTo = None
    db.commit()
    db.refresh(device)
    return device


@app.get("/api/rentals", response_model=List[schemas.DeviceOut])
def my_rentals(email: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Device)
        .filter(models.Device.assignedTo == email.lower())
        .order_by(models.Device.id)
        .all()
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
