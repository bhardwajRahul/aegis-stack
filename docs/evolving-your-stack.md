# Evolving Your Stack

**Your architecture isn't set in stone.** Build for today's requirements, adapt as they change, refactor when needed.

Most frameworks lock you into decisions made during `init`. Aegis Stack gives you the freedom to evolve your stack as your product evolves.

---

## The Friday Afternoon Dilemma

It's Friday afternoon. Product wants the MVP Monday. Do you:

**A) Over-engineer for "future scale"** *(workers, queues, caching, message buses...)*

**B) Ship the minimal viable stack** *(FastAPI + Flet)*

With Aegis Stack, you can confidently choose **B** - because adding components later is trivial.

```bash
# Friday 4 PM: Bootstrap it
uvx aegis-stack init mvp-api
cd mvp-api && uv sync && make serve

# Monday 9 AM: It's live 🎉
```

---

## Week 3: Your First Background Job

Product loves the MVP. Now they want automated daily reports.

**Before Aegis Stack:**

- Manually add APScheduler dependency
- Create scheduler infrastructure
- Configure Docker services
- Update docker-compose.yml
- Fight merge conflicts
- Cross fingers

**With Aegis Stack:**

```bash
aegis add scheduler --project-path ./mvp-api
```

**Added:**

- `app/entrypoints/scheduler.py` - Scheduler entrypoint
- `app/components/scheduler.py` - Job registration
- `tests/components/test_scheduler.py` - Component tests
- Docker service configuration
- Health check integration

**Updated:**

- `docker-compose.yml` - New scheduler service
- `pyproject.toml` - APScheduler dependency
- `.copier-answers.yml` - Component state

**Ran automatically:**

- `uv sync` - Installed dependencies
- `make fix` - Formatted code

### Your First Scheduled Job

Now add your daily report:

```python
# app/components/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

def register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register all scheduled jobs."""

    # Daily report at 9 AM
    scheduler.add_job(
        generate_daily_report,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_report",
        name="Generate Daily Report",
        replace_existing=True,
    )

async def generate_daily_report() -> None:
    """Generate and send daily report."""
    # Your logic here
    pass
```

Ship it:
```bash
git add . && git commit -m "Add daily reports"
docker compose up -d
```

---

## Month 2: Scaling Up

Traffic is growing. Some API endpoints are slow. Time for background processing.

```bash
aegis add worker --project-path ./mvp-api
```

**Added:**

- `app/components/worker/` - Worker queues (system, load-test)
- `app/services/load_test.py` - Load testing service
- Redis service (auto-included dependency)
- Worker health monitoring

**Updated:**

- `docker-compose.yml` - Redis + worker services
- `pyproject.toml` - arq + redis dependencies

### Move Work to Background

```python
# app/components/backend/api/reports.py

from fastapi import APIRouter
from arq import create_pool
from arq.connections import RedisSettings

router = APIRouter()

@router.post("/reports/generate")
async def generate_report_async(report_data: dict):
    """Queue report generation."""
    redis = await create_pool(RedisSettings())
    job = await redis.enqueue_job("generate_report", report_data)

    return {"job_id": str(job.job_id), "status": "queued"}
```

```python
# app/components/worker/queues/system.py

async def generate_report(ctx: dict, report_data: dict) -> dict:
    """Process report generation in background."""
    # Heavy lifting happens here
    report = await process_report(report_data)
    await send_report_email(report)
    return {"status": "complete", "report_id": report.id}
```

---

## Month 4: Adding User Authentication

Product wants to add user accounts. You need authentication.

**Before Aegis Stack:**

- Research auth libraries
- Set up database models
- Create migration system
- Build JWT token handling
- Write auth endpoints
- Add password hashing
- Configure environment variables
- Test everything manually

**With Aegis Stack:**

```bash
aegis add-service auth --project-path ./mvp-api
```

**Added:**

- `app/components/backend/api/auth/` - Auth API endpoints (login, register, etc.)
- `app/models/user.py` - User model with password hashing
- `app/services/auth/` - Authentication service layer
- `app/core/security.py` - JWT token handling
- `app/cli/auth.py` - User management CLI commands
- `alembic/` - Database migration infrastructure
- `tests/` - Comprehensive auth test suite (52 tests)
- Database component (auto-added as required dependency)

**Updated:**

- `pyproject.toml` - Auth dependencies (python-jose, passlib, python-multipart)
- `.env.example` - Auth configuration (JWT_SECRET, etc.)
- `docker-compose.yml` - No changes (database already there from worker)

### Post-Addition Setup

```bash
# Apply auth migrations
make migrate

# Create test users
mvp-api auth create-test-users --count 5

# Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

### Using Auth in Your API

```python
# app/components/backend/api/reports.py

from fastapi import APIRouter, Depends
from app.components.backend.api.deps import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/reports/generate")
async def generate_report_async(
    report_data: dict,
    current_user: User = Depends(get_current_active_user)  # Protected!
):
    """Queue report generation (requires authentication)."""
    redis = await create_pool(RedisSettings())
    job = await redis.enqueue_job(
        "generate_report",
        report_data,
        user_id=current_user.id  # Track who requested it
    )

    return {"job_id": str(job.job_id), "status": "queued"}
```

---

## Month 5: Adding AI Chat

Product wants an AI chatbot for customer support.

```bash
aegis add-service ai --project-path ./mvp-api
```

**Added:**

- `app/services/ai/` - PydanticAI integration with multiple providers
- `app/components/backend/api/ai/` - AI API endpoints (chat, streaming)
- `app/cli/ai.py` - Interactive CLI chat interface with markdown rendering
- AI provider support (OpenAI, Anthropic, Google Gemini, Groq)
- Conversation persistence and memory management

**Updated:**

- `pyproject.toml` - PydanticAI dependencies
- `.env.example` - AI provider configuration

### Post-Addition Setup

```bash
# Configure AI provider
echo "AI_PROVIDER=openai" >> .env
echo "OPENAI_API_KEY=your-key-here" >> .env

# Test via CLI
mvp-api ai chat
# > How can I help you today?
# Hello! Can you explain webhooks?

# Test via API
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain webhooks", "stream": false}'
```

### Combining Services: AI + Auth

```python
# app/components/backend/api/ai/router.py

from fastapi import APIRouter, Depends
from app.components.backend.api.deps import get_current_active_user
from app.models.user import User
from app.services.ai import get_ai_response

router = APIRouter()

@router.post("/ai/chat")
async def chat(
    message: str,
    current_user: User = Depends(get_current_active_user)  # Require auth
):
    """User-specific AI chat with conversation history."""
    response = await get_ai_response(
        message=message,
        user_id=current_user.id  # Personalized context
    )

    return {"response": response, "user": current_user.email}
```

---

## Month 6: Refactoring

You've learned your system. Turns out scheduled jobs work better as worker tasks. Time to clean up.

```bash
aegis remove scheduler --project-path ./mvp-api
```

**Removed:**

- All scheduler component files
- Scheduler Docker service
- APScheduler dependency

**Updated:**

- `docker-compose.yml` - Scheduler service gone
- `pyproject.toml` - Dependency cleaned up

**Preserved:**

- All your business logic (you migrated it to workers)
- Database data (if scheduler was using SQLite)
- Git history (full rollback support)

### Migration Pattern

**Before removal**, move jobs to workers:

```python
# app/components/worker/queues/system.py

from arq import cron

# Daily report - now a worker cron job
async def generate_daily_report(ctx):
    """Generate and send daily report."""
    # Your logic here
    pass

class WorkerSettings:
    cron_jobs = [
        cron(generate_daily_report, hour=9, minute=0)  # Daily at 9 AM
    ]
```

Then remove scheduler:
```bash
git add . && git commit -m "Migrate to worker-based scheduling"
aegis remove scheduler --project-path ./mvp-api
git add . && git commit -m "Remove scheduler component"
```

---

## Template Updates: Stay Current

Your project isn't frozen at `init`. Aegis Stack templates evolve, and your projects can evolve with them.

### Version Tracking

Every generated project tracks its template version:

```yaml
# .copier-answers.yml
_commit: f359779a...  # Template snapshot you're on
_src_path: /path/to/aegis-stack
```

### Staying Updated

**Coming in v0.2.0:** Template update command

```bash
# Check for template updates
aegis update --dry-run

# Update to latest template
aegis update

# What gets updated:
# - Bug fixes in generated code
# - New best practices
# - Improved patterns
# - Enhanced tooling

# What stays yours:
# - Your business logic
# - Custom modifications
# - Database data
# - Git history
```

### Update Philosophy

- **Non-destructive**: Your custom code is preserved
- **Incremental**: Small, frequent updates over big migrations
- **Transparent**: See exactly what changes before applying
- **Reversible**: Git keeps full history for rollback

---

## Next Steps

- **[CLI Reference](cli-reference.md)** - Complete `aegis add` and `aegis remove` documentation
- **[Component Overview](components/index.md)** - Deep dive into available components

---

**Build for today. Adapt for tomorrow. That's Aegis Stack.**
