# Integration Patterns

How different parts of Aegis Stack connect and communicate.

!!! info "About This Guide"
    This page explains the **architectural patterns** used throughout Aegis Stack. The business logic layer pattern described here applies to all services—whether built-in Aegis Services (auth, ai) that you add via `--services` or custom business services you write yourself.

    For information about **which Aegis Services are available**, see **[Services Overview](services/index.md)**.

## Business Logic Layer

Aegis Stack uses a **service layer** to keep business logic separate from infrastructure components. Services are Python classes that orchestrate workflows and can be called from anywhere.

### What Goes Where

**Services** (`app/services/`):

- Database interactions, external API calls, file processing
- Complex business logic and data transformations
- Pure functions that can be unit tested
- Single files (`report_service.py`) or folders (`system/health.py`) for complex domains

**Components** (`app/components/`):

- API endpoints, scheduled jobs, background tasks, UI handlers
- Import services explicitly - no magic auto-discovery
- Keep thin - handle requests, call services, return responses

**Why explicit imports?** Makes dependencies clear, prevents surprises, easier testing.

### Service Structure Example

Services contain your business logic and can call other services:

```python
# app/services/user_service.py
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import User, UserCreate
from app.services.email_service import EmailService

class UserService:
    """Service for managing users."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()

    async def create_user(self, user_data: UserCreate) -> User:
        """Create user and send welcome email."""
        # Step 1: Create user in database
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password)
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Step 2: Send welcome email
        await self.email_service.send_welcome_email(user.id)

        return user
```

This service can be used from any component - API, CLI, Worker, or Scheduler.

## Component → Service Patterns

All components follow the same pattern: **import the service, call the method**. This keeps your business logic consistent whether triggered by HTTP request, CLI command, scheduled job, or background task.

### API → Service

Routes call service methods:

```python
# app/components/backend/api/users.py
from app.services.user_service import UserService
from app.core.db import db_session

@router.post("/users")
async def create_user_endpoint(data: UserCreate):
    with db_session() as session:
        user_service = UserService(session)
        user = await user_service.create_user(data)
    return user
```

### CLI → Service

Commands call the same service methods:

```python
# app/cli/users.py
from app.services.user_service import UserService
from app.core.db import db_session

@app.command()
async def create_user(email: str, name: str):
    """Create a new user."""
    with db_session() as session:
        user_service = UserService(session)
        data = UserCreate(email=email, full_name=name)
        user = await user_service.create_user(data)
    print(f"Created user: {user.email}")
```

### Worker → Service

Background tasks call service methods through thin wrappers:

```python
# app/components/worker/tasks/user_tasks.py
from typing import Any
from app.services.user_service import UserService
from app.core.db import db_session

async def create_user_task(ctx: dict[str, Any], user_data: dict) -> dict:
    """Create user as background job."""
    with db_session() as session:
        user_service = UserService(session)
        data = UserCreate(**user_data)
        user = await user_service.create_user(data)
    return {"user_id": user.id, "email": user.email}

# Register in WorkerSettings
class WorkerSettings:
    functions = [create_user_task]
```

### Scheduler → Service

Scheduled jobs call service methods directly:

```python
# app/components/scheduler.py
from app.services.cleanup_service import CleanupService
from app.core.db import db_session

async def cleanup_inactive_users():
    """Scheduled task to cleanup inactive users."""
    with db_session() as session:
        cleanup_service = CleanupService(session)
        await cleanup_service.deactivate_inactive_users(days=90)

scheduler.add_job(cleanup_inactive_users, 'cron', hour=2)
```

### Consistent Behavior

The workflow stays the same whether called from API, CLI, worker, or scheduler:

```python
# One service class
class AnalyticsService:
    async def track_event(self, event: str, **data) -> None:
        """Track analytics event."""
        ...

# Multiple entry points
✅ API: Track endpoint calls
✅ CLI: Track manual operations
✅ Worker: Track background job completion
✅ Scheduler: Track scheduled task execution
```

One service class. Multiple entry points. Consistent behavior.

## Cross-Component Patterns

Sometimes components need to communicate with each other, not just call services.

### Scheduler → Worker

Scheduler can trigger worker tasks for heavy operations:

```python
# app/components/scheduler.py
from app.components.worker.pools import get_queue_pool

async def schedule_daily_reports():
    """Scheduler triggers worker to generate reports."""
    pool, _ = await get_queue_pool("system")
    await pool.enqueue_job("generate_daily_report")
    await pool.aclose()

# Schedule daily at 2 AM
scheduler.add_job(schedule_daily_reports, 'cron', hour=2)
```

Or execute lightweight tasks directly:

```python
# app/components/scheduler.py
from app.services.cleanup_service import CleanupService
from app.core.db import db_session

async def cleanup_temp_files():
    """Fast cleanup - run directly in scheduler."""
    with db_session() as session:
        cleanup = CleanupService(session)
        await cleanup.remove_temp_files()

scheduler.add_job(cleanup_temp_files, 'interval', hours=1)
```

**When to use Worker vs Direct:**
- **Direct**: Lightweight tasks (< 1 second), no retry needed
- **Worker**: Heavy tasks, need retry logic, want queue management

### API → Worker

Queue background tasks from API endpoints:

```python
# app/components/backend/api/reports.py
from app.components.worker.pools import get_queue_pool

@router.post("/reports/generate")
async def queue_report(user_id: int):
    """Queue report generation as background job."""
    pool, _ = await get_queue_pool("system")
    job = await pool.enqueue_job("generate_report", user_id)
    await pool.aclose()
    return {"job_id": job.job_id, "status": "queued"}
```

### Frontend ↔ Backend

Flet frontend runs in the same process as FastAPI backend, so it can call services directly:

```python
# app/components/frontend/pages/dashboard.py
from app.services.system import get_system_status

async def update_dashboard():
    """Update dashboard with system status."""
    status = await get_system_status()
    # Update Flet UI with status data
```

For generated projects, Frontend and Backend share the same container, making this direct access fast and simple.

## Container Boundaries

Each component runs in its own Docker container for independent scaling:

- **Backend Container**: Runs FastAPI + Flet (Frontend)
- **Scheduler Container**: Runs APScheduler for scheduled jobs
- **Worker Container**: Runs arq for background task processing

**What's Shared:**

- Services (`app/services/`)
- Core utilities (`app/core/`)
- Configuration (`app/core/config`)
- Database sessions

**What's Isolated:**

- Component-specific hooks and startup logic
- Resource allocation (CPU, memory)
- Scaling decisions (can scale workers independently)

**Important**: Backend startup hooks don't affect scheduler, and vice versa. Each container manages its own lifecycle.

## Data Validation Boundaries

**Trust Zones**: Validate at entry points, trust internally.

### Validate Hard at Entry Points

API endpoints, CLI commands, and worker tasks validate incoming data:

```python
# Entry point - validate with Pydantic
@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    # Internal code - trust the data
    status = await get_system_status()
    return HealthResponse(healthy=status.overall_healthy, ...)
```

### Trust Internally

Once validated, internal code trusts the data:

```python
# CLI - validate API response
health_data = HealthResponse.model_validate(response.json())

# Then trust: direct attribute access
print(f"System healthy: {health_data.healthy}")  # Not .get("healthy")
```

**Validation Layers:**
1. **API Endpoints**: Pydantic `response_model` validates outgoing data
2. **CLI Commands**: Pydantic models validate API responses
3. **Internal Code**: Direct model attribute access (no `.get()` patterns)

## Testing Services

Services can be tested directly without running components:

```python
# tests/services/test_user_service.py
async def test_create_user(db_session):
    """Test user creation workflow."""
    user_service = UserService(db_session)

    data = UserCreate(email="test@example.com", full_name="Test User")
    user = await user_service.create_user(data)

    assert user.email == "test@example.com"
    assert user.id is not None
```

No API server needed. No worker process needed. Just call the service.

This is why the service layer is powerful - it's testable in isolation.

## Configuration Access

**Global Settings**: Available everywhere via explicit import.

```python
from app.core.config import settings

# Use throughout application
database_url = settings.DATABASE_URL
api_timeout = settings.API_TIMEOUT
```

**Constants vs Config**:

- **Constants** (`app.core.constants`): Immutable values (API paths, default timeouts)
- **Config** (`app.core.config`): Environment-dependent values (URLs, secrets, feature flags)

## Key Principles

1. **Services are the integration point** - business logic lives here, components call it
2. **Explicit imports for clarity** - no magic auto-discovery for services or routes
3. **Validate at boundaries** - security and reliability at entry points
4. **Trust internally** - clean, readable code once validated
5. **Container isolation** - independent scaling and lifecycle management
6. **One pattern, many entry points** - same service logic works everywhere

---

## Next Steps

- **[Services Overview](services/index.md)** - Explore built-in Aegis Services (auth, ai) you can add to your project
- **[Components Overview](components/index.md)** - Infrastructure layer components
- **[Evolving Your Stack](evolving-your-stack.md)** - How to grow your architecture over time
