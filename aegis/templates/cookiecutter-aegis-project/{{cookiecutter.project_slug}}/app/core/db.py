# app/core/db.py
"""
Database configuration and session management.

This module provides SQLite database connectivity using SQLModel and SQLAlchemy.
Includes proper session management with transaction handling and foreign key support.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.core.config import settings

# Create SQLite engine with proper configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=settings.DATABASE_CONNECT_ARGS,
    echo=settings.DATABASE_ENGINE_ECHO,
)


# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable foreign key constraints in SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Configure session factory with SQLModel Session
SessionLocal = sessionmaker(
    class_=Session, bind=engine, autoflush=False, autocommit=False
)


@contextmanager
def db_session(autocommit: bool = True) -> Generator[Session, None, None]:
    """
    Database session context manager with automatic transaction handling.

    Args:
        autocommit: Whether to automatically commit the transaction on success

    Yields:
        Session: Database session instance

    Example:
        with db_session() as session:
            # Your database operations here
            result = session.query(MyModel).first()
    """
    db_session: Session = SessionLocal()
    try:
        yield db_session
        if autocommit:
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()