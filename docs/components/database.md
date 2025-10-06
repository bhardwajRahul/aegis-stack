# Database Component

!!! example "Musings: On ORMs and Alternatives"
    I'm well aware of the... disdain... people have for ORMs. SQLModel is the default because it works great for 80% of use cases and integrates beautifully with FastAPI/Pydantic.

    That said, I already have a sub-component feature in the works for folks who prefer raw SQL via driver cursors or SQLAlchemy Core. Choose your own adventure.

SQLite database with [SQLModel](https://sqlmodel.tiangolo.com/) ORM for type-safe data operations.

Use `aegis init my-project --components database` to include this component.

## What You Get

- **SQLite Database** - File-based database at `data/app.db`
- **SQLModel ORM** - Type-safe database operations with Pydantic integration
- **Session Management** - Context managers for transaction handling
- **Health Check Integration** - Database connectivity monitoring
- **Test Infrastructure** - Transaction rollback for test isolation

## Quick Start

### See It Work

```bash
# Generate project with database
aegis init my-project --components database
cd my-project

# Setup and start
cp .env.example .env
make serve  # Starts backend with database

# Check database health
curl http://localhost:8000/health/detailed
```

**What just happened?**

1. SQLite database created at `data/app.db`
2. Database connection verified via health check
3. Session management ready for your models

## Adding Your First Model

### 1. Create Your Model
```python
# app/models/shield.py
from sqlmodel import SQLModel, Field

class Shield(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    defense_rating: int = Field(default=10)
    material: str = "iron"
    enchantment: str | None = None
```

### 2. Use It
```python
# In your API endpoint
from app.core.db import db_session
from app.models.shield import Shield

@router.post("/shields")
async def forge_shield(shield_data: ShieldCreate):
    with db_session() as session:
        shield = Shield(**shield_data.dict())
        session.add(shield)
        # Automatically committed
    return {"id": shield.id, "name": shield.name}
```

That's it! The database handles persistence automatically.

## Configuration

Configure the database through environment variables:

```bash
# .env
DATABASE_URL=sqlite:///data/app.db      # Database location
DATABASE_ENGINE_ECHO=false              # SQL logging
```

### Connection Settings
```python
# app/core/config.py (auto-generated)
DATABASE_CONNECT_ARGS = {
    "check_same_thread": False,  # Allow multi-threading
    "foreign_keys": 1,            # Enable foreign key constraints
}
```

## Development Workflow

### Docker (Recommended)
```bash
make serve           # Start everything
make health-detailed # See database status
```

### Direct Access
```bash
# Access SQLite database directly
sqlite3 data/app.db
.tables              # List tables
.schema              # Show schemas
```

## Common Patterns

### Session Management
```python
from app.core.db import db_session

# Auto-commit on success, rollback on error
with db_session() as session:
    shield = Shield(name="Dragon Scale Shield")
    session.add(shield)
    # Automatically committed when context exits
```

## Testing

The component includes test fixtures for database testing:

- In-memory test databases
- Transaction rollback patterns
- Isolated test environments

```python
# tests/conftest.py provides:
@pytest.fixture
def db_session():
    # Provides isolated test database session
    # Automatically rolls back after each test
```

## Monitoring

```bash
# Quick health check
make health-detailed

# Direct database inspection
sqlite3 data/app.db ".tables"
```

The health system tracks:

- ✅ Database connectivity
- ✅ File existence and permissions
- ✅ Table count and metadata
- ✅ Database file size

## Next Steps

- **[SQLModel Documentation](https://sqlmodel.tiangolo.com/)** - Complete ORM capabilities
- **[Component Overview](./index.md)** - Understanding Aegis Stack's component architecture