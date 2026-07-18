"""SQLAlchemy ORM models.

The `Device` model mirrors the fields found in `hardware_data.json`
(id, name, brand, purchaseDate, status, issue, assignedTo, history).
`serialNumber` and `category` are additional optional columns used by the
Admin "Add New Device" form shown in the UI mock-ups; they are nullable so
records seeded from the JSON fixture (which doesn't carry them) remain valid.

`issue` describes a CURRENT, unresolved defect (e.g. "Battery swelling") -
it's what the Inventory Auditor's "Create service history" action reads and
clears. `history` is only a log of past actions already taken on the device.
`notes` is a free-form, admin-only field completely independent of the AI
Health Check - it is never read or written by the auditor prompt, except for
the automated "Lemon" warning (see LEMON_WARNING in main.py), which is
written there specifically so it doesn't get mixed up with `issue`.
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
    issue = Column(String, nullable=True)
    assignedTo = Column(String, nullable=True)
    history = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    # Extra fields used by the Admin "Add New Device" modal.
    serialNumber = Column(String, nullable=True)
    category = Column(String, nullable=True)


class User(Base):
    """Accounts table backing the closed-system login.

    Creating a row here (via POST /api/users) is the *only* way to gain
    access to the app — there is no self-service sign-up.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
