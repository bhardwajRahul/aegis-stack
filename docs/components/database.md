# Database Component

!!! example "Musings: On ORMs and Alternatives (September 2025)"
    I'm well aware of the... disdain... people have for ORMs. SQLModel is the default because it works great for 80% of use cases and integrates beautifully with FastAPI/Pydantic.

    That said, I already have a sub-component feature in the works for folks who prefer raw SQL via driver cursors or SQLAlchemy Core. Choose your own adventure.

Database component with [SQLModel](https://sqlmodel.tiangolo.com/) ORM supporting SQLite and PostgreSQL. PostgreSQL can be self-hosted in a container or run on [Neon](https://neon.tech) serverless Postgres.

Use `aegis init my-project --components database` to include this component. Pick the engine (and, for PostgreSQL, the host) in the interactive prompt, or pass it non-interactively:

```bash
aegis init my-project --components "database[sqlite]"   # file-based (default)
aegis init my-project --components "database[postgres]"  # local postgres container
aegis init my-project --components "database[neon]"      # Neon serverless Postgres
```

Neon is not a separate engine: `database[neon]` is the **postgres** engine hosted on Neon, so every model, migration, and query is identical to a self-hosted postgres stack.

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

=== "Neon"

    **Serverless Postgres • No DB container in production • Cloud-hosted**

    ```bash
    # App runtime uses the POOLED endpoint (note the -pooler host)
    DATABASE_URL=postgresql://user:pass@ep-xxxx-pooler.region.aws.neon.tech/dbname
    # Migrations use the DIRECT (unpooled) endpoint
    DATABASE_URL_UNPOOLED=postgresql://user:pass@ep-xxxx.region.aws.neon.tech/dbname
    ```

    **Perfect for:**

    - Serverless and autoscaling deployments
    - Per-PR / preview database branches
    - Teams that would rather not operate a database server

    **How it works:**

    - Neon is the **postgres** engine, hosted on Neon's cloud. Models,
      migrations, and SQLModel code are identical to a self-hosted postgres stack.
    - **Development** runs the same local `postgres:16` container as a plain
      postgres stack (zero credentials, fully offline).
    - **Production** runs no database container at all: the app points
      `DATABASE_URL` at Neon's pooled endpoint, injected as a secret.
    - Runtime uses the **pooled** endpoint; migrations use the **direct**
      (unpooled) endpoint, because Neon's pooler (PgBouncer in transaction mode)
      is unsafe for DDL and session-level features.
    - No extra Python dependencies: the standard `asyncpg` and `psycopg2` drivers
      connect over TCP. There is no Neon-specific Python driver.

    **Requirements:**

    - A Neon account and project (free tier available)
    - `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (direct) set as
      production secrets

## Choosing a Database

### Cross-Container Considerations

**SQLite limitation**: File-based databases can't be shared across containers. If multiple services need database access (e.g., API + Scheduler), you need PostgreSQL.

**PostgreSQL advantage**: Network-based access allows any container to connect, making it ideal for microservice architectures.

### Hosting PostgreSQL: container or Neon

Both `database[postgres]` and `database[neon]` use the same engine; they differ only in where production runs:

- **Container** (`database[postgres]`): a `postgres:16` service runs in your Docker Compose stack in every environment (`make serve`, `make serve-prod`, and `aegis deploy`). You operate and back up the database.
- **Neon** (`database[neon]`): development still runs the local container, but production has no database service, the app connects to Neon's cloud via `DATABASE_URL`, and Neon handles autoscaling, scale-to-zero, and branching.

The generated connection code detects a Neon host (`*.neon.tech`) at runtime and applies Neon's pooler-safe connection settings only then, so one codebase runs against the local container in development and Neon in production.

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
- On Neon, migrations run over the direct (unpooled) `DATABASE_URL_UNPOOLED` endpoint automatically; the pooled endpoint is reserved for app runtime

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

- **[SQLModel Documentation](https://sqlmodel.tiangolo.com/)** - Complete ORM capabilities
- **[Component Overview](./index.md)** - Understanding Aegis Stack's component architecture
