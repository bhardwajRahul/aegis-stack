# Authentication Service

The **Authentication Service** provides complete user management and JWT-based authentication for your Aegis Stack application.

!!! info "Ready-to-Use Authentication"
    Generate a project with auth service and start building immediately:

    ```bash
    aegis init my-app --services auth
    cd my-app
    uv sync && source .venv/bin/activate
    make server
    ```

    Authentication endpoints available at `/auth/*` with automatic database setup.

## What You Get

- **JWT-based authentication** - Industry-standard token authentication
- **User registration and login** - Complete user lifecycle management
- **Password hashing** - Secure bcrypt password storage
- **Protected routes** - Easy endpoint protection with decorators
- **User profile management** - Built-in user data handling
- **Database integration** - Automatic user table and model setup
- **Form data support** - OAuth2 password flow compatibility

## Architecture

```mermaid
graph TB
    subgraph "Authentication Service Stack"
        AuthService[🔐 Auth Service<br/>JWT + User Management]

        subgraph "API Endpoints"
            Register["POST /auth/register<br/>Create new user"]
            Login["POST /auth/token<br/>Get access token"]
            Profile["GET /auth/me<br/>Current user profile"]
        end

        subgraph "Required Components"
            Backend[⚡ Backend Component<br/>FastAPI Routes]
            Database[💾 Database Component<br/>SQLite + SQLModel]
        end

        subgraph "Security Layer"
            JWT[🔑 JWT Tokens<br/>python-jose]
            Passwords[🔒 Password Hashing<br/>passlib + bcrypt]
            OAuth2[📋 OAuth2 Flow<br/>FastAPI Security]
        end

        subgraph "Database Schema"
            Users["👥 users table<br/>id, email, hashed_password<br/>created_at, updated_at"]
        end
    end

    AuthService --> Register
    AuthService --> Login
    AuthService --> Profile

    Register --> Backend
    Login --> Backend
    Profile --> Backend

    Backend --> Database

    AuthService --> JWT
    AuthService --> Passwords
    AuthService --> OAuth2

    Database --> Users

    style AuthService fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    style Register fill:#f1f8e9,stroke:#388e3c,stroke-width:2px
    style Login fill:#f1f8e9,stroke:#388e3c,stroke-width:2px
    style Profile fill:#f1f8e9,stroke:#388e3c,stroke-width:2px
    style Backend fill:#e1f5fe,stroke:#1976d2,stroke-width:2px
    style Database fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style JWT fill:#fff8e1,stroke:#ffa000,stroke-width:2px
    style Passwords fill:#fff8e1,stroke:#ffa000,stroke-width:2px
    style OAuth2 fill:#fff8e1,stroke:#ffa000,stroke-width:2px
    style Users fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Auth API
    participant S as Auth Service
    participant D as Database
    participant J as JWT Utils

    Note over U,J: User Registration Flow
    U->>F: Fill registration form
    F->>A: POST /auth/register
    A->>S: UserService.get_user_by_email()
    S->>D: SELECT user WHERE email=?
    D-->>S: null (user doesn't exist)
    S-->>A: No existing user found
    A->>S: UserService.create_user()
    S->>J: hash_password()
    J-->>S: hashed_password
    S->>D: INSERT INTO users
    D-->>S: User created
    S-->>A: User object
    A-->>F: 201 Created + User data
    F-->>U: Registration successful

    Note over U,J: Login Flow
    U->>F: Enter email/password
    F->>A: POST /auth/token
    A->>S: UserService.get_user_by_email()
    S->>D: SELECT user WHERE email=?
    D-->>S: User record
    S-->>A: User object
    A->>J: verify_password()
    J-->>A: Password valid
    A->>J: create_access_token()
    J-->>A: JWT token
    A-->>F: 200 OK + Access token
    F-->>U: Login successful

    Note over U,J: Protected Route Access
    U->>F: Request protected resource
    F->>A: GET /auth/me (Authorization: Bearer TOKEN)
    A->>J: decode_token()
    J-->>A: User ID from token
    A->>S: UserService.get_user_by_id()
    S->>D: SELECT user WHERE id=?
    D-->>S: User record
    S-->>A: User object
    A-->>F: 200 OK + User profile
    F-->>U: Show user data
```

## API Endpoints

### Public Endpoints

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### POST /auth/token
Login and receive an access token.

**Request Body (Form Data):**
```
username=user@example.com&password=securepassword123
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Protected Endpoints

#### GET /auth/me
Get current user profile information.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Integration Examples

### Frontend Integration

```python
# app/components/frontend/auth/login.py
import flet as ft
import httpx

async def login_user(email: str, password: str) -> dict | None:
    """Login user and return token data."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/auth/token",
            data={"username": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()
    return None

def create_login_form() -> ft.Container:
    """Create login form UI."""
    email_field = ft.TextField(label="Email", width=300)
    password_field = ft.TextField(label="Password", password=True, width=300)

    async def on_login(e):
        token_data = await login_user(email_field.value, password_field.value)
        if token_data:
            # Store token and redirect
            await page.client_storage.set_async("auth_token", token_data["access_token"])
            page.go("/dashboard")

    return ft.Container(
        content=ft.Column([
            ft.Text("Login", size=24, weight=ft.FontWeight.BOLD),
            email_field,
            password_field,
            ft.ElevatedButton("Login", on_click=on_login),
        ]),
        padding=20
    )
```

### Backend Route Protection

```python
# app/components/backend/api/protected.py
from fastapi import APIRouter, Depends
from app.services.auth.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/protected", tags=["protected"])

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile - requires authentication."""
    return {
        "message": f"Hello {current_user.email}!",
        "user_id": current_user.id,
        "email": current_user.email
    }

@router.post("/update-profile")
async def update_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update user profile - requires authentication."""
    # Update logic here
    return {"message": "Profile updated successfully"}
```

### Service Layer Usage

```python
# app/services/my_service.py
from app.services.auth.user_service import UserService
from app.components.backend.api.deps import get_db
from sqlmodel import Session

class MyBusinessService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)

    async def get_user_data(self, user_id: int) -> dict:
        """Get user-specific business data."""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        return {
            "user": user,
            "permissions": await self.get_user_permissions(user),
            "settings": await self.get_user_settings(user)
        }
```

## Configuration

### JWT Settings

Configure JWT behavior in your environment:

```bash
# .env
JWT_SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Password Requirements

```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)
```

## Database Schema

### User Model

```python
# app/models/user.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)

class User(UserBase, table=True):
    """User database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(UserBase):
    """User creation schema."""
    password: str

class UserResponse(UserBase):
    """User response schema (excludes password)."""
    id: int
    created_at: datetime
    updated_at: datetime
```

### Database Migrations

The auth service automatically creates the required database tables:

```python
# app/core/db.py
from sqlmodel import SQLModel, create_engine
from app.models.user import User  # Imports register the table

def create_db_and_tables():
    """Create database and all tables."""
    SQLModel.metadata.create_all(engine)
```

## Testing

### Auth Service Tests

```python
# tests/services/test_auth_service.py
import pytest
from app.services.auth.user_service import UserService
from app.models.user import UserCreate

@pytest.mark.asyncio
async def test_user_registration(db_session):
    """Test user registration flow."""
    user_service = UserService(db_session)

    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123"
    )

    user = user_service.create_user(user_data)

    assert user.email == "test@example.com"
    assert user.id is not None
    assert user.hashed_password != "testpassword123"  # Should be hashed

@pytest.mark.asyncio
async def test_duplicate_email_registration(db_session):
    """Test that duplicate emails are rejected."""
    user_service = UserService(db_session)

    user_data = UserCreate(
        email="duplicate@example.com",
        password="password123"
    )

    # First registration should succeed
    user1 = user_service.create_user(user_data)
    assert user1.id is not None

    # Second registration should fail
    with pytest.raises(ValueError, match="Email already registered"):
        user_service.create_user(user_data)
```

### API Endpoint Tests

```python
# tests/api/test_auth_endpoints.py
import pytest
from fastapi.testclient import TestClient

def test_user_registration(client: TestClient):
    """Test user registration endpoint."""
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "hashed_password" not in data  # Should not expose password

def test_user_login(client: TestClient, test_user):
    """Test user login endpoint."""
    response = client.post(
        "/auth/token",
        data={
            "username": test_user.email,
            "password": "testpassword"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_protected_endpoint(client: TestClient, auth_headers):
    """Test accessing protected endpoint with valid token."""
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "id" in data
```

## Security Best Practices

### Token Security
- **Short expiration** - Default 30-minute token lifetime
- **Secure storage** - Store tokens securely in frontend
- **HTTPS only** - Always use HTTPS in production
- **Rotation** - Implement token refresh for long-lived sessions

### Password Security
- **Strong hashing** - bcrypt with automatic salt generation
- **Minimum requirements** - Enforce password complexity
- **Rate limiting** - Prevent brute force attacks
- **Secure reset** - Implement secure password reset flow

### API Security
- **Input validation** - Validate all input data
- **Error handling** - Don't expose internal errors
- **CORS configuration** - Configure CORS appropriately
- **Request logging** - Log authentication attempts

## Troubleshooting

### Common Issues

**401 Unauthorized on /auth/me**
```bash
# Check token format
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/auth/me

# Verify token hasn't expired
# Check JWT_ACCESS_TOKEN_EXPIRE_MINUTES setting
```

**400 Bad Request on registration**
```python
# Check for duplicate email
# Verify password requirements
# Check request format (JSON vs form data)
```

**Database connection errors**
```bash
# Verify database file exists
ls -la data/app.db

# Check database permissions
# Verify SQLModel table creation
```

### Debug Commands

```bash
# Check auth service status
curl http://localhost:8000/auth/register -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"debug@test.com","password":"test123"}'

# Verify JWT token
python -c "
import jwt
token = 'YOUR_TOKEN_HERE'
print(jwt.decode(token, options={'verify_signature': False}))
"

# Check database tables
sqlite3 data/app.db '.tables'
sqlite3 data/app.db 'SELECT * FROM users;'
```

---

**Next Steps:**

- **[Services Overview](index.md)** - Complete services architecture
- **[Components Database](../components/database.md)** - Database component details
- **[CLI Reference](../cli-reference.md)** - Auth service CLI commands