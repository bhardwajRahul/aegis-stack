# Integration Patterns Reference

Quick reference for how different parts of Aegis Stack integrate with each other.

## Service Layer Architecture

Aegis Stack uses a service layer to keep business logic separate from infrastructure components. Services are Python classes that orchestrate workflows and can be called from anywhere.

### Service Structure

Services are defined in `app/services/` and contain your business logic:

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
        # Create user in database
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password)
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Send welcome email
        await self.email_service.send_welcome_email(user.id)

        return user
```

This service can be used from any component.

### Component Integration

#### API → Service

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

#### CLI → Service

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

#### Worker → Service

Background tasks call service methods:

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

#### Scheduler → Service

Scheduled jobs call service methods:

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

### Service Orchestration Pattern

Services orchestrate workflows by calling other services:

```python
# app/services/user_service.py
class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()
        self.analytics_service = AnalyticsService()

    async def create_user(self, user_data: UserCreate) -> User:
        """Create user with full workflow."""
        # Step 1: Save user
        user = await self._save_user(user_data)

        # Step 2: Send welcome email
        await self.email_service.send_welcome_email(user.id)

        # Step 3: Track event
        await self.analytics_service.track_event(
            "user_created",
            user_id=user.id
        )

        return user
```

The workflow stays consistent whether called from API, CLI, worker, or scheduler.

### Worker Task Wrapper Pattern

For background processing, create a thin wrapper around service methods:

```python
# app/components/worker/tasks/email_tasks.py
from typing import Any
from app.services.email_service import EmailService

async def send_email_task(ctx: dict[str, Any], user_id: int, template: str) -> dict:
    """Worker task wrapper for email service."""
    email_service = EmailService()
    result = await email_service.send_email(user_id, template)
    return {"sent": True, "message_id": result.id}

# Use from API:
@router.post("/users/{user_id}/send-email")
async def queue_email(user_id: int, template: str):
    pool, _ = await get_queue_pool("system")
    job = await pool.enqueue_job("send_email_task", user_id, template)
    await pool.aclose()
    return {"job_id": job.job_id}
```

### Scheduler + Worker Pattern

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
    """Fast cleanup - run directly."""
    with db_session() as session:
        cleanup = CleanupService(session)
        await cleanup.remove_temp_files()

scheduler.add_job(cleanup_temp_files, 'interval', hours=1)
```

### Testing Services

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

### Component Growth

As you add components, services work everywhere:

```python
# app/services/analytics_service.py
class AnalyticsService:
    async def track_event(self, event: str, **data) -> None:
        """Track analytics event."""
        ...

# Used across all components:
✅ API: Track endpoint calls
✅ CLI: Track manual operations
✅ Worker: Track background job completion
✅ Scheduler: Track scheduled task execution
✅ Frontend: Track via API calls
```

One service class. Multiple entry points. Consistent behavior.

## Backend Integration Patterns

**🔄 Auto-Discovered**: Drop files, no registration required

- **Middleware**: `app/components/backend/middleware/`
- **Startup Hooks**: `app/components/backend/startup/`
- **Shutdown Hooks**: `app/components/backend/shutdown/`

**📝 Manual Registration**: Explicit imports for clarity

- **API Routes**: Register in `app/components/backend/api/routing.py`
- **Services**: Import explicitly where needed

## Service Integration Patterns

Put your business logic in `app/services/` and import it explicitly where needed.

**Services** contain pure business logic functions. **Components** import and use them.

```python
# app/services/report_service.py
async def generate_monthly_report(user_id: int) -> Report:
    # Your business logic here
    pass

# app/components/backend/api/reports.py
from app.services.report_service import generate_monthly_report

@router.post("/reports")
async def create_report(user_id: int):
    return await generate_monthly_report(user_id)

# app/components/scheduler/main.py
from app.services.report_service import generate_monthly_report

scheduler.add_job(generate_monthly_report, args=[123])
```

**What Goes Where:**

**Services** (`app/services/`):

- Database interactions, external API calls, file processing
- Complex business logic and data transformations
- Pure functions that can be unit tested
- Single files (`report_service.py`) or folders (`system/health.py`) for complex domains

**Components** (`app/components/`):

- API endpoints, scheduled jobs, UI handlers
- Import services explicitly - no magic auto-discovery
- Keep thin - handle requests, call services, return responses

**Why explicit?** Makes dependencies clear, prevents surprises, easier testing.

## Component Communication

**Backend ↔ Services**: Direct imports
```python
from app.services.system import get_system_status
```

**CLI ↔ Backend**: HTTP API calls
```python
from app.services.system.models import HealthResponse
health_data = HealthResponse.model_validate(api_response.json())
```

**Frontend ↔ Backend**: Flet-FastAPI integration
```python
from app.services.system import get_system_status
# Direct function calls within same process
```

## Data Validation Boundaries

**Trust Zones**: Validate at entry points, trust internally

1. **API Endpoints**: Pydantic `response_model` validates outgoing data
2. **CLI Commands**: Pydantic models validate API responses
3. **Internal Code**: Direct model attribute access (no `.get()` patterns)

```python
# Entry point - validate hard
@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    # Internal code - trust the data
    status = await get_system_status()
    return HealthResponse(healthy=status.overall_healthy, ...)

# CLI - validate API response
health_data = HealthResponse.model_validate(response.json())
# Then trust: health_data.healthy (not health_data.get("healthy"))
```

## Scheduler Integration

**Job Registration**: Explicit in scheduler component

```python
# app/components/scheduler/main.py
from app.services.reports import generate_daily_report

scheduler.add_job(
    generate_daily_report,
    trigger="cron",
    hour=9, minute=0
)
```

**Service Functions**: Pure business logic
```python
# app/services/reports.py
async def generate_daily_report() -> None:
    # Pure business logic, no scheduler dependencies
```

## Configuration Access

**Global Settings**: Available everywhere

```python
from app.core.config import settings

# Use throughout application
database_url = settings.DATABASE_URL
api_timeout = settings.API_TIMEOUT
```

**Constants vs Config**:

- **Constants** (`app.core.constants`): Immutable values (API paths, timeouts)
- **Config** (`app.core.config`): Environment-dependent values (URLs, secrets)

## Container Boundaries

Each component manages its own concerns:

- **Backend Container**: Runs FastAPI + Flet, manages backend hooks
- **Scheduler Container**: Runs APScheduler, manages scheduled jobs
- **Shared**: Services, core utilities, configuration

**No Cross-Container Hooks**: Backend hooks don't affect scheduler, and vice versa.

## Key Principles

1. **Auto-discovery for infrastructure** (hooks) → convenience
2. **Explicit imports for business logic** (services, routes) → clarity
3. **Validate at boundaries** → security and reliability
4. **Trust internally** → clean, readable code
5. **Container isolation** → independent scaling
