"""Seeds the SQLite database from `hardware_data.json` and creates a demo
admin account.

Can be run standalone:

    python seed.py

or imported and called from `main.py` on application startup so the API is
always ready to use without a manual seeding step.
"""

import json
from pathlib import Path

import models
from database import Base, SessionLocal, engine

ADMIN_EMAIL = "demo@booksy.com"
ADMIN_PASSWORD = "demo123"

# Look for the fixture next to this file first (self-contained backend),
# falling back to the project root where the original file was provided.
DATA_FILE_CANDIDATES = [
    Path(__file__).parent / "hardware_data.json",
    Path(__file__).parent.parent / "hardware_data.json",
]


def _find_data_file() -> Path:
    for candidate in DATA_FILE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "hardware_data.json not found next to seed.py or in the project root."
    )


def seed_devices(db) -> int:
    """Loads devices from the JSON fixture if the table is currently empty."""
    if db.query(models.Device).first():
        return 0

    data_file = _find_data_file()
    with open(data_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    count = 0
    for item in items:
        device = models.Device(
            id=item.get("id"),
            name=item.get("name") or "Unknown Device",
            brand=item.get("brand") or "",
            purchaseDate=item.get("purchaseDate"),
            status=item.get("status") or "Available",
            notes=item.get("notes"),
            assignedTo=item.get("assignedTo"),
            history=item.get("history"),
        )
        db.add(device)
        count += 1

    db.commit()
    return count


def seed_admin(db) -> bool:
    """Creates the demo admin account (demo@booksy.com / demo123) if missing."""
    existing = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()
    if existing:
        return False

    admin = models.User(email=ADMIN_EMAIL, password=ADMIN_PASSWORD, role="admin")
    db.add(admin)
    db.commit()
    return True


def run_seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        devices_added = seed_devices(db)
        admin_created = seed_admin(db)
        print(f"[seed] Devices inserted: {devices_added}")
        print(
            "[seed] Admin account created (demo@booksy.com / demo123)."
            if admin_created
            else "[seed] Admin account already present."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
