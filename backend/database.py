"""Database connection and session management."""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import (
    DATABASE_URL,
    DB_MAX_OVERFLOW,
    DB_POOL_PRE_PING,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=DB_POOL_PRE_PING,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for manual DB sessions (outside FastAPI routes)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
