"""Authentication service utilities."""

from app.core.security import verify_token
from app.models.user import User
from app.services.auth.user_service import UserService
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession


async def get_current_user_from_token(token: str, db: AsyncSession) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    # Get user email from token
    email = payload.get("sub")
    if not isinstance(email, str) or email is None:
        raise credentials_exception

    # Get user from database
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    return user
