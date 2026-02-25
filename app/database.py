"""
Database configuration and session management for SakhiSetu.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

logger = logging.getLogger(__name__)

# Load database URL from env via config
def _get_database_url() -> str:
    try:
        from app.config import settings
        return settings.database_url
    except Exception:
        return "sqlite:///./sakhisetu.db"

DATABASE_URL = _get_database_url()

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Initialize database tables and run migrations."""
    from app.models import Scheme  # noqa: F401 - Registers Scheme with Base

    Base.metadata.create_all(bind=engine)
    migrate_db()
    logger.info("Database tables initialized successfully.")


def migrate_db() -> None:
    """Add new columns to schemes table if they don't exist (SQLite-safe)."""
    from sqlalchemy import text

    new_columns = [
        ("benefits", "TEXT"),
        ("category", "VARCHAR(100)"),
        ("source_url", "VARCHAR(1000)"),
        ("last_scraped_at", "DATETIME"),
    ]
    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE schemes ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                logger.info("Added column %s to schemes", col_name)
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    pass
                else:
                    logger.warning("Migration for %s: %s", col_name, e)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.exception("Database session error: %s", e)
        db.rollback()
        raise
    finally:
        db.close()
