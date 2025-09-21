# Authentication Service

The **Authentication Service** provides complete user management and JWT-based authentication for your Aegis Stack application.

!!! info "Ready-to-Use Authentication"
    Generate a project with auth service and start building immediately:

    ```bash
    aegis init my-app --services auth --components database
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

## Quick Start

### 1. Generate Project with Auth

```bash
# Create project with auth service
aegis init my-auth-app --services auth --components database

# Navigate and setup
cd my-auth-app
uv sync && source .venv/bin/activate

# Run the application
make server
```

### 2. Test Authentication

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secure123"}'

# Login and get token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=secure123"

# Access protected endpoint
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
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

### Password Security

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

## Next Steps

| Topic | Description |
|-------|-------------|
| **[API Reference](api.md)** | Complete endpoint documentation with schemas |
| **[Integration Guide](integration.md)** | Frontend/backend integration patterns |
| **[CLI Commands](cli.md)** | User management and utility commands |
| **[Examples](examples.md)** | Real-world usage patterns and implementations |

---

**Related Documentation:**

- **[Services Overview](../index.md)** - Complete services architecture
- **[Database Component](../../components/database.md)** - Database component details
- **[CLI Reference](../../cli-reference.md)** - Auth service CLI commands