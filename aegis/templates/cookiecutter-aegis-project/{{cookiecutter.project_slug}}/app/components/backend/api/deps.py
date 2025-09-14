"""FastAPI dependencies for the backend API."""

from collections.abc import Generator

from app.core.db import SessionLocal
from sqlmodel import Session


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency that provides a database session.

    This dependency is used in FastAPI route functions to get access to
    the database. It automatically handles session lifecycle - creating,
    yielding, and closing the session properly.

    Usage:
        @router.get("/example")
        def example_endpoint(db: Session = Depends(get_db)):
            # Use db for database operations
            pass

    Yields:
        Session: SQLModel database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
