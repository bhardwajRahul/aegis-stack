"""User data models."""

from datetime import UTC, datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    """Base user model with shared fields."""

    email: EmailStr = Field(unique=True, index=True)
    full_name: str | None = None
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    """User database model."""

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(min_length=8)


class UserLogin(SQLModel):
    """User login model."""

    email: str
    password: str


class UserResponse(UserBase):
    """User response model (excludes sensitive data)."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None
