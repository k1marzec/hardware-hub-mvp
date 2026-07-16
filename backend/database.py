"""Database engine/session configuration for the Hardware Management System.

Uses a local SQLite file (hardware.db) so the whole backend runs with zero
external dependencies - perfect for an MVP.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./hardware.db"

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
