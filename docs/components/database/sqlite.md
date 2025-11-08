# SQLite Implementation

**Part of the Database Component** - See [Database Component](../database.md) for overview and shared patterns.

File-based database with zero configuration - perfect for development and single-container deployments.

## Quick Start

```bash
# Generate project with database
aegis init my-project --components database
cd my-project

# Database works immediately
cp .env.example .env
make serve
```

**That's it.** SQLite database created at `data/app.db` with zero configuration.

## Configuration

```bash
# .env
DATABASE_URL=sqlite:///data/app.db
```

The database file is created automatically in the `data/` directory.

## Using SQLModel

```python
# Define your model
from sqlmodel import SQLModel, Field

class Shield(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    defense_rating: int = 10

# Use in your code
from app.core.db import db_session

with db_session() as session:
    shield = Shield(name="Dragon Scale", defense_rating=95)
    session.add(shield)
    # Auto-commits on exit
```

Works identically whether you use SQLite or PostgreSQL.

## Development Workflow

### Docker (Recommended)

```bash
make serve  # Start everything
```

### Direct Database Access

Access SQLite database directly for inspection and debugging:

```bash
# Open SQLite CLI
sqlite3 data/app.db

# Useful commands:
.tables              # List all tables
.schema              # Show all schemas
.schema shield       # Show specific table schema
SELECT * FROM shield;  # Query data
.quit                # Exit
```

## Container Considerations

**SQLite is file-based** - it can't be shared across containers.

### This Works

```yaml
# Single container with multiple services
services:
  app:
    # Backend + Scheduler in one container
    volumes:
      - ./data:/app/data  # ✅ Single container accessing SQLite
```

### This Doesn't Work

```yaml
# Multiple containers trying to share SQLite
services:
  api:
    volumes:
      - ./data:/app/data  # ❌ Container 1
  scheduler:
    volumes:
      - ./data:/app/data  # ❌ Container 2 - conflicts with Container 1
```

**If you need multi-container database access, use PostgreSQL instead.**

## See Also

- **[Database Component](../database.md)** - Overview and shared patterns
- **[PostgreSQL Implementation](postgresql.md)** - Multi-container database option
