"""Database engine/session configuration for the Hardware Management System.

Uses a local SQLite file (hardware.db) so the whole backend runs with zero
external dependencies - perfect for an MVP.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Absolute path on purpose: guarantees the API always reads/writes the same
# hardware.db regardless of the process's current working directory (e.g.
# if uvicorn is launched from a different folder than backend/).
BASE_DIR = Path(__file__).resolve().parent
SQLALCHEMY_DATABASE_URL = f"sqlite:///{BASE_DIR / 'hardware.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Needed only for SQLite: allows the connection to be shared across the
    # threads FastAPI's request handlers may run on.
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
