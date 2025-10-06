# Worker Component

!!! example "Musings: Why Worker is Experimental"
    I haven't used arq in production long enough to say I'm an expert, and it wouldn't feel right to claim otherwise - hence the experimental label. That said, I included it because:

    - The pedigree speaks volumes (Samuel Colvin built it)
    - It was quite easy, dare I say elegant, to set up as its own component

    At the end of the day, producer/queue/consumer/whatever you want to call it - I know that pattern. Implementing arq was as straightforward as it could be.

Async background task processing using standard [arq](https://arq-docs.helpmanual.io/) patterns.

!!! info "Adding Worker to Your Project"
    Use `aegis init my-project --components worker` to include this component.

## What You Get

- **Background task processing** - Runs any code without blocking your API (async tasks get the best performance)
- **System queue** - For maintenance and background operations (15 concurrent jobs, 300s timeout)
- **Auto-reload** - Built-in development mode with file watching
- **Optional extras** - Load testing queue and future media processing

??? note "arq CLI Reference"
    Aegis Stack uses **pure arq** - no custom wrappers or abstractions:

    ```bash
    # Standard arq CLI - all features work!
    arq app.components.worker.queues.system.WorkerSettings

    # With auto-reload for development
    arq app.components.worker.queues.system.WorkerSettings --watch app/

    # Health check
    arq app.components.worker.queues.system.WorkerSettings --check

    # Process all jobs and exit (perfect for testing!)
    arq app.components.worker.queues.system.WorkerSettings --burst
    ```

    Your existing arq knowledge transfers 100%. Google "arq [anything]" and it works!

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

```bash
make serve           # Start everything
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
