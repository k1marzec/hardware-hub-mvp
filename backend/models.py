"""SQLAlchemy ORM models.

The `Device` model mirrors the fields found in `hardware_data.json`
(id, name, brand, purchaseDate, status, notes, assignedTo, history).
`serialNumber` and `category` are additional optional columns used by the
Admin "Add New Device" form shown in the UI mock-ups; they are nullable so
records seeded from the JSON fixture (which doesn't carry them) remain valid.
"""

from sqlalchemy import Column, Integer, String

from database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=True, default="")
    purchaseDate = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Available")
    notes = Column(String, nullable=True)
    assignedTo = Column(String, nullable=True)
    history = Column(String, nullable=True)

    # Extra fields used by the Admin "Add New Device" modal.
    serialNumber = Column(String, nullable=True)
    category = Column(String, nullable=True)


class User(Base):
    """Minimal user table used for the mock authentication flow."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Plaintext on purpose: this is a mock login for the MVP, not a real
    # security-hardened auth system.
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
