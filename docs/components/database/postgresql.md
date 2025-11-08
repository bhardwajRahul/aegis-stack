# PostgreSQL Implementation

**Part of the Database Component** - See [Database Component](../database.md) for overview and shared patterns.

!!! danger "Not Yet Available"
    PostgreSQL support is in active development and not yet released.

    **Expected:** Early 2026

    For now, use [SQLite](sqlite.md) which works great for most use cases.

Server-based database for multi-container deployments and higher concurrency.

## Quick Start

```bash
# Generate project with PostgreSQL
aegis init my-project --components database[postgresql]
cd my-project

# PostgreSQL automatically configured in docker-compose.yml
docker compose up -d
```

Database initialized and ready to use.

## Configuration

```bash
# .env
DATABASE_URL=postgresql://aegis:aegis@postgres:5432/aegis_db
```

PostgreSQL service automatically added to `docker-compose.yml` when you select it.

## Using SQLModel

```python
# Exact same code as SQLite
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

**Your code works identically** whether you use SQLite or PostgreSQL.

## Development Workflow

### Docker (Recommended)

```bash
make serve  # Start everything including PostgreSQL
```

### Direct Database Access

Access PostgreSQL directly for inspection and debugging:

```bash
# Connect to PostgreSQL CLI
docker compose exec postgres psql -U aegis -d aegis_db

# Useful commands:
\dt                  # List all tables
\d shield            # Describe table structure
SELECT * FROM shield;  # Query data
\q                   # Exit
```

## Container Considerations

**PostgreSQL is network-based** - any container can connect.

### Multi-Container Support

```yaml
# All services can access PostgreSQL
services:
  postgres:
    image: postgres:16-alpine

  api:
    environment:
      DATABASE_URL: postgresql://aegis:aegis@postgres:5432/aegis_db  # ✅

  scheduler:
    environment:
      DATABASE_URL: postgresql://aegis:aegis@postgres:5432/aegis_db  # ✅

  worker:
    environment:
      DATABASE_URL: postgresql://aegis:aegis@postgres:5432/aegis_db  # ✅
```

**This is the key difference** - PostgreSQL enables true microservice architectures.

## See Also

- **[Database Component](../database.md)** - Overview and shared patterns
- **[SQLite Implementation](sqlite.md)** - File-based database option
