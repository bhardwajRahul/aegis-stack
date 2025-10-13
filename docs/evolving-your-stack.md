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
cd mvp-api && uv sync && make server

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

## Next Steps

- **[CLI Reference](cli-reference.md)** - Complete `aegis add` and `aegis remove` documentation
- **[Component Overview](components/index.md)** - Deep dive into available components
- **[Philosophy](philosophy.md)** - Why Aegis Stack works this way

---

**Build for today. Adapt for tomorrow. That's Aegis Stack.**
