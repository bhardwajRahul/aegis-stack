"""Security utilities for authentication and authorization."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt


def _truncate_password(password: str) -> str:
    """Truncate password to 72 bytes for bcrypt compatibility.

    bcrypt has a 72-byte limit. We explicitly truncate here rather than
    rely on library defaults for clarity and consistency.
    """
    return password[:72]


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    truncated = _truncate_password(password)
    return bcrypt.hashpw(truncated.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    truncated = _truncate_password(plain_password)
    return bcrypt.checkpw(truncated.encode("utf-8"), hashed_password.encode("utf-8"))
