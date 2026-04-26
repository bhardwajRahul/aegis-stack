# Database Component

!!! example "Musings: On ORMs and Alternatives (September 2025)"
    I'm well aware of the... disdain... people have for ORMs. SQLModel is the default because it works great for 80% of use cases and integrates beautifully with FastAPI/Pydantic.

    That said, I already have a sub-component feature in the works for folks who prefer raw SQL via driver cursors or SQLAlchemy Core. Choose your own adventure.

Database component with [SQLModel](https://sqlmodel.tiangolo.com/) ORM supporting SQLite and PostgreSQL.

Use `aegis init my-project --components database` to include this component.

## Database Options

Choose your database based on your deployment needs:

=== "SQLite"

    **File-based • Zero configuration • Development-friendly**

    ```bash
    DATABASE_URL=sqlite:///data/app.db
    ```

    **Perfect for:**

    - Single-container deployments
    - Development and testing
    - Embedded applications
    - Simple deployment requirements

    **Features:**

    - No external dependencies
    - File-based simplicity
    - Zero configuration
    - Automatic directory creation

    **Limitations:**

    - Single-writer constraint
    - Cross-container access challenges
    - Limited concurrency

    **→ [Complete SQLite Implementation Guide](database/sqlite.md)**

=== "PostgreSQL"

    **Server-based • Production-ready • High concurrency**

    ```bash
    DATABASE_URL=postgresql://aegis:aegis@postgres:5432/aegis_db
    ```

    **Perfect for:**

    - Multi-container deployments
    - Production environments
    - High concurrency requirements
    - Advanced database features

    **Features:**

    - Client-server architecture
    - Connection pooling
    - Multi-container support
    - Advanced data types (JSONB, arrays)

    **Requirements:**

    - PostgreSQL service (via Docker Compose)
    - Network configuration
    - Credentials management

    **→ [Complete PostgreSQL Implementation Guide](database/postgresql.md)**

## Choosing a Database

### Cross-Container Considerations

**SQLite limitation**: File-based databases can't be shared across containers. If multiple services need database access (e.g., API + Scheduler), you need PostgreSQL.

**PostgreSQL advantage**: Network-based access allows any container to connect, making it ideal for microservice architectures.

## Common Patterns

### Adding Your First Model

**Step 1: Create Your Model**
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

**Step 2: Use It**
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

## Session Management

```python
from app.core.db import db_session

# Auto-commit on success, rollback on error
with db_session() as session:
    shield = Shield(name="Dragon Scale Shield")
    session.add(shield)
    # Automatically committed when context exits
```

## Migrations

Database schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/):

### Generate Migration

```bash
# After creating/modifying models
alembic revision --autogenerate -m "Add shields table"
```

### Apply Migrations

```bash
# Apply all pending migrations
make migrate

# Or use alembic directly
alembic upgrade head
```

### Migration Best Practices

- Generate migrations after model changes
- Review auto-generated migrations before applying
- Test migrations in development first
- Commit migrations to version control
- Migrations work identically for SQLite and PostgreSQL

## Testing

The component includes test fixtures for database testing:

```python
# tests/conftest.py provides:
@pytest.fixture
def db_session():
    # Provides isolated test database session
    # Automatically rolls back after each test
```

**Test Infrastructure:**

```bash
# Quick health check
make health-detailed
```

- In-memory test databases
- Transaction rollback patterns
- Isolated test environments
- Same patterns work for both SQLite and PostgreSQL

## Next Steps

- **[SQLite Implementation Guide](database/sqlite.md)** - File-based database setup and usage
- **[PostgreSQL Implementation Guide](database/postgresql.md)** - Server-based database setup and usage
- **[SQLModel Documentation](https://sqlmodel.tiangolo.com/)** - Complete ORM capabilities
- **[Component Overview](./index.md)** - Understanding Aegis Stack's component architecture
