"""User management service."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.security import get_password_hash
from app.models.user import User, UserCreate


class UserService:
    """Service for managing users."""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Hash the password
        hashed_password = get_password_hash(user_data.password)

        # Create user object
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            created_at=datetime.now(UTC),
        )

        # Save to database
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        statement = select(User).where(User.email == email)
        result = self.db.exec(statement)
        return result.first()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        return self.db.get(User, user_id)

    def update_user(self, user_id: int, **updates) -> User | None:
        """Update user data."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        for field, value in updates.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.updated_at = datetime.now(UTC)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def deactivate_user(self, user_id: int) -> User | None:
        """Deactivate a user account."""
        return self.update_user(user_id, is_active=False)
