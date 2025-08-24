# Database Component

The database component provides SQLite database integration with SQLModel ORM for Aegis Stack applications.

## Overview

The database component includes:

- **SQLite Database**: Lightweight, file-based database perfect for development and small-to-medium applications
- **SQLModel ORM**: Type-safe database operations with Pydantic integration
- **SQLAlchemy Core**: Robust database engine with connection management
- **Session Management**: Context managers for transaction handling
- **Foreign Key Support**: Automatic foreign key constraint enforcement

## Installation

Add the database component when creating a new project:

```bash
aegis init my-app --components database
```

Or include it with other components:

```bash
aegis init my-app --components worker,scheduler,database
```

## Configuration

The database component adds the following settings to `app/core/config.py`:

```python
# Database settings (SQLite)
DATABASE_URL: str = "sqlite:///data/app.db"
DATABASE_ENGINE_ECHO: bool = False
DATABASE_CONNECT_ARGS: dict[str, Any] = {"check_same_thread": False}
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `DATABASE_URL` | `str` | `"sqlite:///data/app.db"` | SQLite database file path |
| `DATABASE_ENGINE_ECHO` | `bool` | `False` | Enable SQL query logging |
| `DATABASE_CONNECT_ARGS` | `dict[str, Any]` | `{"check_same_thread": False}` | SQLite connection arguments |

### Environment Overrides

All database settings can be overridden via environment variables:

```bash
# .env file
DATABASE_URL=sqlite:///custom/path/app.db
DATABASE_ENGINE_ECHO=true
```

## Usage

### Basic Database Operations

```python
from app.core.db import db_session
from sqlmodel import SQLModel, Field, select

# Define a model
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str

# Use the database
with db_session() as session:
    # Create
    user = User(name="John Doe", email="john@example.com")
    session.add(user)
    session.commit()  # Auto-committed by context manager
    
    # Read
    users = session.exec(select(User)).all()
    
    # Update
    user.name = "Jane Doe"
    session.add(user)
    
    # Delete
    session.delete(user)
```

### Session Management

The database component provides a convenient context manager:

```python
from app.core.db import db_session

# Auto-commit on success
with db_session() as session:
    user = User(name="Alice")
    session.add(user)
    # Automatically committed

# Manual transaction control
with db_session(autocommit=False) as session:
    try:
        # Multiple operations
        user1 = User(name="Bob")
        user2 = User(name="Carol")
        session.add_all([user1, user2])
        session.commit()  # Manual commit
    except Exception:
        # Automatically rolled back by context manager
        raise
```

### Model Definition Best Practices

```python
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    # Use proper type hints
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    posts: list["Post"] = Relationship(back_populates="author")

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    content: str
    author_id: int = Field(foreign_key="user.id")
    
    # Back-reference
    author: User = Relationship(back_populates="posts")
```

## Database Initialization

Create tables and initial data:

```python
from app.core.db import engine
from sqlmodel import SQLModel

# In your application startup
def create_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)

# With initial data
def initialize_database():
    """Initialize database with default data."""
    create_tables()
    
    with db_session() as session:
        # Check if data exists
        existing_users = session.exec(select(User)).first()
        if not existing_users:
            # Create initial data
            admin = User(
                name="Admin User",
                email="admin@example.com"
            )
            session.add(admin)
```

## Health Checks

The database component integrates with the health monitoring system:

```python
from app.core.db import db_session
from sqlmodel import text

async def check_database_health():
    """Check database connectivity."""
    try:
        with db_session() as session:
            # Simple connectivity test
            result = session.exec(text("SELECT 1")).first()
            return result == 1
    except Exception:
        return False
```

## Data Directory

The default database location is `data/app.db`. Ensure this directory exists:

```bash
# In your project root
mkdir -p data
```

For production, consider using an absolute path:

```bash
# .env
DATABASE_URL=sqlite:////var/lib/myapp/database.db
```

## Migrations

For schema changes, consider using Alembic:

```bash
# Install Alembic
uv add alembic

# Initialize migrations
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Add user table"

# Apply migrations
alembic upgrade head
```

## Testing

The database component works well with pytest fixtures:

```python
import pytest
import tempfile
from pathlib import Path
from app.core.config import settings
from app.core.db import engine
from sqlmodel import SQLModel

@pytest.fixture
def test_db():
    """Create temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db") as temp_file:
        # Override database URL for testing
        original_url = settings.DATABASE_URL
        settings.DATABASE_URL = f"sqlite:///{temp_file.name}"
        
        # Create tables
        SQLModel.metadata.create_all(engine)
        
        yield
        
        # Cleanup
        settings.DATABASE_URL = original_url
        SQLModel.metadata.drop_all(engine)
```

## Common Patterns

### Repository Pattern

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from sqlmodel import select

T = TypeVar("T", bound=SQLModel)

class Repository(Generic[T], ABC):
    def __init__(self, model: type[T]):
        self.model = model
    
    def get_all(self, session: Session) -> list[T]:
        return session.exec(select(self.model)).all()
    
    def get_by_id(self, session: Session, id: int) -> T | None:
        return session.get(self.model, id)
    
    def create(self, session: Session, obj: T) -> T:
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

# Usage
user_repo = Repository(User)
with db_session() as session:
    users = user_repo.get_all(session)
```

### Service Layer

```python
class UserService:
    def __init__(self):
        self.repo = Repository(User)
    
    def create_user(self, name: str, email: str) -> User:
        with db_session() as session:
            user = User(name=name, email=email)
            return self.repo.create(session, user)
    
    def get_user_by_email(self, email: str) -> User | None:
        with db_session() as session:
            return session.exec(
                select(User).where(User.email == email)
            ).first()
```

## Troubleshooting

### Common Issues

1. **Database locked error**: Ensure `check_same_thread=False` in connection args
2. **Foreign key violations**: Foreign keys are enabled by default
3. **File permissions**: Ensure write access to the database directory
4. **Connection timeouts**: Check file system performance

### Debugging

Enable SQL logging for debugging:

```bash
# .env
DATABASE_ENGINE_ECHO=true
```

Or programmatically:

```python
from app.core.config import settings
settings.DATABASE_ENGINE_ECHO = True
```

## Production Considerations

### Performance

- Use connection pooling for high-traffic applications
- Consider read replicas for read-heavy workloads
- Implement proper indexing strategies
- Monitor database file size and performance

### Backup

```bash
# Simple backup
cp data/app.db data/backup-$(date +%Y%m%d).db

# Using SQLite command
sqlite3 data/app.db ".backup data/backup.db"
```

### Security

- Restrict file system access to database files
- Use environment variables for sensitive configuration
- Consider encryption at rest for sensitive data
- Implement proper authentication and authorization

## Dependencies

The database component automatically installs:

- `sqlmodel>=0.0.14` - Type-safe ORM with Pydantic integration
- `sqlalchemy>=2.0.0` - Database toolkit and ORM
- `aiosqlite>=0.19.0` - Async SQLite driver

These dependencies are only included when the database component is selected during project generation.