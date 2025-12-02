# Worker Component

!!! example "Musings: Why Worker is Experimental (August 2025)"
    I haven't used arq in production long enough to say I'm an expert, and it wouldn't feel right to claim otherwise - hence the experimental label. That said, I included it because:

    - The pedigree speaks volumes (Samuel Colvin built it)
    - It was quite easy, dare I say elegant, to set up as its own component

    At the end of the day, producer/queue/consumer/whatever you want to call it - I know that pattern. Implementing arq was as straightforward as it could be.

Async background task processing using standard [arq](https://arq-docs.helpmanual.io/) patterns.

!!! info "Adding Worker to Your Project"
    **New Project**: Use `aegis init my-project --components worker` to include this component.

    **Existing Project**: Add worker to an existing Aegis Stack project:
    ```bash
    aegis add worker
    ```
    Worker automatically includes Redis as a dependency. The command will:

    - Create worker component files (`app/components/worker/`)
    - Add worker queues (system, load-test)
    - Add worker health checks and dashboard card
    - Configure Docker services (Redis + workers)
    - Update dependencies (`arq`, `redis`)

## What You Get

- **Background task processing** - Runs any code without blocking your API (async tasks get the best performance)
- **System queue** - For maintenance and background operations (15 concurrent jobs, 300s timeout)
- **Auto-reload** - Built-in development mode with file watching
- **Optional extras** - Load testing queue and future media processing

## Quick Start

### See It Work

```bash
# Generate project with worker
aegis init my-project --components worker
cd my-project

# Setup and start everything
cp .env.example .env
make serve  # Starts Redis + workers + webserver

# In another terminal, trigger a background task
curl -X POST http://localhost:8000/api/v1/tasks/enqueue \
  -H "Content-Type: application/json" \
  -d '{"task_name": "io_simulation_task", "queue_type": "load_test"}'

# Check the result (replace {task_id} with actual ID from response)
curl http://localhost:8000/api/v1/tasks/result/{task_id}
```

**What just happened?**

1. Worker processed `io_simulation_task` in the background
2. Task ran asynchronously without blocking your API
3. Result was stored in Redis for retrieval

Try the dashboard at [http://localhost:8000/dashboard](http://localhost:8000/dashboard) to see health status including worker queues!

### Dashboard Monitoring

The Worker component provides comprehensive queue monitoring through the dashboard interface:

<img src="../../images/dashboard-light-worker.png#only-light" alt="Worker Queue Dashboard">
<img src="../../images/dashboard-dark-worker.png#only-dark" alt="Worker Queue Dashboard">

!!! info "Worker Dashboard Features"
    The Worker dashboard showcases queue monitoring:

    - **Row-based queue display** - Compact table format showing multiple queues at once
    - **Intelligent status messages** - Context-aware status reporting:
        - "worker offline" - When Redis connection is lost
        - "no tasks defined" - When queue exists but no functions are registered
        - "ready" - When worker is healthy and ready for tasks
    - **Real-time metrics** - Live updates of queue counts and job status
    - **Theme-aware design** - Optimized visibility in both light and dark modes

## arq CLI Commands

Aegis Stack uses **pure arq** - no custom wrappers or abstractions. Your existing arq knowledge transfers 100%!

### Start Worker

Start the worker to process background jobs:

```bash
arq my_project.components.worker.queues.system.WorkerSettings
```

**What it does:**
- Connects to Redis
- Registers all task functions
- Begins processing jobs from queues
- Runs until stopped with Ctrl+C

**Example output:**
```
16:30:45: Starting worker for 1 functions: process_data_task, send_email_task
16:30:45: redis_version=7.0.0 mem_usage=1.00M clients_connected=5
16:30:45:  j_complete=0 j_failed=0 j_retried=0 j_ongoing=0 queued=0
```

### Auto-Reload Worker

Start worker with auto-reload on code changes:

```bash
arq --watch my_project.components.worker.queues.system.WorkerSettings
```

**Best for:**
- Local development
- Testing task changes
- Rapid iteration

**Note:** Reloads on any `.py` file change in the project.

### Check Queue Status

View current queue status and job counts:

```bash
arq --check my_project.components.worker.queues.system.WorkerSettings
```

**Example output:**
```
j_complete=15 j_failed=0 j_retried=2 j_ongoing=1 queued=3
```

### Queue Management

Each task is registered to a specific queue. Check your `WorkerSettings` class:

```python
# app/components/worker/queues/system.py
class WorkerSettings:
    functions = [
        process_data_task,    # Default queue
        send_email_task,      # Email queue
    ]

    queue_name = "default"  # Default queue name
```

## Adding Your First Task

### 1. Create Your Task
```python
# app/components/worker/tasks/my_tasks.py
from typing import Any

async def send_welcome_email(ctx: dict[str, Any], user_id: int) -> dict:
    """Send welcome email to new user."""
    logger.info(f"Sending welcome email to user {user_id}")
    # Your email logic here
    return {"status": "sent", "user_id": user_id}
```

### 2. Register It
```python
# app/components/worker/queues/system.py
from app.components.worker.tasks.my_tasks import send_welcome_email

class WorkerSettings:
    functions = [
        system_health_check,
        cleanup_temp_files,
        send_welcome_email,  # Add here
    ]
```

### 3. Use It
```python
# In your API endpoint
@router.post("/users")
async def create_user(user_data: UserCreate):
    user = await save_user(user_data)
    
    # Queue the email task
    redis, _ = await get_queue_pool("system")
    await redis.enqueue_job("send_welcome_email", user.id)
    
    return {"message": "User created, welcome email queued"}
```

That's it! The worker will process it automatically.

## Development Workflow

**Option 1: Standard Development (Recommended)**

```bash
# Start all services including worker
make serve
```

Worker runs automatically as part of docker-compose stack.

**Option 2: Development with Auto-Reload**

```bash
# Terminal 1: Start backend and Redis
make serve

# Terminal 2: Run worker with auto-reload (watches for code changes)
arq --watch my_project.components.worker.queues.system.WorkerSettings
```

**Queue a task:**

```python
from app.components.worker.pools import get_queue_pool

# Get queue pool
pool, queue_name = await get_queue_pool("system")

# Enqueue job
job = await pool.enqueue_job("task_function_name", _queue_name=queue_name)

# Close pool
await pool.aclose()
```

**Monitor your workers:**

```bash
make logs-worker     # Watch workers live
make health-detailed # See queue metrics
```

### Testing Your Tasks

```bash
# Quick test via API
curl -X POST http://localhost:8000/api/v1/tasks/enqueue \
  -H "Content-Type: application/json" \
  -d '{"task_name": "io_simulation_task", "queue_type": "load_test"}'

# Or use burst mode for one-off testing
make worker-test
```

## Configuration

Worker behavior is configured in `app/core/config.py`:

```python
# Redis connection (DSN format)
REDIS_URL: str = "redis://localhost:6379"
REDIS_DB: int = 0

# Worker settings
WORKER_KEEP_RESULT_SECONDS: int = 3600
WORKER_MAX_TRIES: int = 3
```

See **[Configuration](configuration.md)** for complete details.

## API Reference

All task endpoints are available at `/api/v1/tasks/`:

```bash
# List all available tasks
curl http://localhost:8000/api/v1/tasks/

# Enqueue a task
curl -X POST http://localhost:8000/api/v1/tasks/enqueue \
  -H "Content-Type: application/json" \
  -d '{"task_name": "cpu_intensive_task", "queue_type": "load_test"}'

# Check task status
curl http://localhost:8000/api/v1/tasks/status/{task_id}

# Get task result
curl http://localhost:8000/api/v1/tasks/result/{task_id}

# Quick load tests
curl -X POST http://localhost:8000/api/v1/tasks/examples/load-test-small
curl -X POST http://localhost:8000/api/v1/tasks/examples/load-test-medium
curl -X POST http://localhost:8000/api/v1/tasks/examples/load-test-large
```

## Next Steps

- **[Examples](examples.md)** - Real-world task patterns
- **[Configuration](configuration.md)** - Scaling and custom queues
- **[Load Testing](extras/load-testing.md)** - Stress test your workers
