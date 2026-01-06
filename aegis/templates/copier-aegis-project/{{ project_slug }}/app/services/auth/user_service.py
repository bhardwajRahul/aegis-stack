"""User management service."""

from datetime import UTC, datetime

from app.core.security import get_password_hash
from app.models.user import User, UserCreate
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


class UserService:
    """Service for managing users with async database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user asynchronously."""
        # Hash the password
        hashed_password = get_password_hash(user_data.password)

        # Create user object
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )

        # Save to database
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address asynchronously."""
        statement = select(User).where(User.email == email)
        result = await self.db.exec(statement)
        return result.first()

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID asynchronously."""
        return await self.db.get(User, user_id)

    async def update_user(self, user_id: int, **updates) -> User | None:
        """Update user data asynchronously."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        for field, value in updates.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def deactivate_user(self, user_id: int) -> User | None:
        """Deactivate a user account asynchronously."""
        return await self.update_user(user_id, is_active=False)

    async def list_users(self) -> list[User]:
        """List all users in the system asynchronously."""
        statement = select(User).order_by(User.created_at.desc())
        result = await self.db.exec(statement)
        return list(result.all())

    async def find_existing_emails_with_prefix(
        self, prefix: str, domain: str
    ) -> list[str]:
        """Find existing emails that match the pattern prefix{number}@domain async."""
        pattern = f"{prefix}%@{domain}"
        statement = select(User.email).where(User.email.like(pattern))
        result = await self.db.exec(statement)
        return list(result.all())
