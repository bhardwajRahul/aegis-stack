# Service Layer

Learn how the auth service layer supports different application interfaces.

## Service Layer Architecture

The auth service provides a shared async service layer that supports multiple interfaces through a single UserService implementation:

### UserService Class

```python
# app/services/auth/user_service.py

class UserService:
    """Service for managing users with async database operations."""
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User
    async def get_user_by_email(self, email: str) -> User | None
    async def get_user_by_id(self, user_id: int) -> User | None
    async def update_user(self, user_id: int, **updates) -> User | None
    async def deactivate_user(self, user_id: int) -> User | None
    async def list_users(self) -> list[User]
    async def find_existing_emails_with_prefix(self, prefix: str, domain: str) -> list[str]
```

## Database Models

The auth service provides these core models:

```python
# app/models/user.py (already exists in your project)
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

class UserResponse(UserBase):
    """User response model (excludes sensitive data)."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None
```

## API Integration

The FastAPI routes use the async service layer:

```python
# app/components/backend/api/auth/router.py (actual code from your project)
from app.services.auth.user_service import UserService

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Register a new user."""
    user_service = UserService(db)

    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await user_service.create_user(user_data)
    return UserResponse.model_validate(user)

@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    """Login and get access token."""
    user_service = UserService(db)
    user = await user_service.get_user_by_email(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

## CLI Integration

The CLI commands use the same async service layer with asyncio.run():

```python
# app/cli/auth.py (actual code from your project)
import asyncio
from app.services.auth.user_service import UserService
from app.core.db import get_async_session

@app.command()
def create_test_user(email: str | None = None, password: str | None = None, ...):
    """Create a test user for development and testing."""
    asyncio.run(_create_test_user(email, password, full_name, prefix, domain))

async def _create_test_user(email, password, full_name, prefix, domain):
    async with get_async_session() as session:
        user_service = UserService(session)

        if email is None:
            email = await find_next_available_email(user_service, prefix, domain)

        user_data = UserCreate(email=email, password=password, full_name=full_name)
        user = await user_service.create_user(user_data)

        # Display created user info...

@app.command()
def list_users():
    """List all users in the system."""
    asyncio.run(_list_users())

async def _list_users():
    async with get_async_session() as session:
        user_service = UserService(session)
        users = await user_service.list_users()
        # Display users...
```

## Dashboard Integration

The frontend dashboard monitors auth service status:

```python
# app/components/frontend/dashboard/cards/auth_card.py (actual code from your project)
class AuthCard:
    """Authentication service monitoring card."""

    def __init__(self, component_data: ComponentStatus):
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _create_auth_metrics(self) -> ft.Column:
        """Create authentication-specific metrics display."""
        token_status = self.metadata.get("token_validation", "unknown")
        sessions_active = self.metadata.get("active_sessions", 0)
        security_status = self.metadata.get("security_features", "enabled")

        # Creates visual indicators for auth health...

    def _create_auth_overview(self) -> ft.Container:
        """Create the authentication service overview section."""
        total_users = self.metadata.get("total_users", 0)
        failed_logins = self.metadata.get("failed_logins_24h", 0)
        token_expiry = self.metadata.get("avg_token_lifetime", "24h")

        # Display auth statistics...
```

## Configuration

The auth service uses centralized configuration:

```python
# app/core/config.py
class Settings(BaseSettings):
    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
```

---

**Next Steps:**

- **[CLI Commands](cli.md)** - Use CLI commands to manage users
- **[Examples](examples.md)** - See working application examples
- **[API Reference](api.md)** - Complete endpoint documentation