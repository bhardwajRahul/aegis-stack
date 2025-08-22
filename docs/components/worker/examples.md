# Worker Examples

Essential patterns for the worker component.

## Basic Task Implementation

```python
# app/components/worker/tasks/system_tasks.py
from app.core.log import logger

async def cleanup_old_logs(ctx, days_old: int = 30) -> dict:
    """Clean up log files older than specified days."""
    try:
        logger.info(f"Starting log cleanup: {days_old} days")
        
        # Your business logic
        cleaned_files = await remove_old_logs(days_old)
        space_freed = calculate_space_freed(cleaned_files)
        
        return {
            "status": "completed",
            "files_cleaned": len(cleaned_files),
            "space_freed_mb": space_freed
        }
        
    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")
        raise  # Let arq handle retries
```

## Task Registration

Tasks are registered directly in `WorkerSettings.functions` - no central registry needed:

```python
# app/components/worker/queues/system.py
from app.components.worker.tasks.system_tasks import cleanup_old_logs

class WorkerSettings:
    functions = [cleanup_old_logs]  # Direct import pattern
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    queue_name = "arq:queue:system"
    max_jobs = 15
```

## Enqueuing Tasks

### From Application Code

```python
# From your application code
from app.components.worker.pools import get_queue_pool

async def enqueue_cleanup():
    """Enqueue a system task."""
    pool, queue_name = await get_queue_pool("system")
    try:
        job = await pool.enqueue_job(
            "cleanup_old_logs",
            days_old=7,
            _queue_name=queue_name
        )
        return job.job_id
    finally:
        await pool.aclose()
```

### From API Endpoints

```python
# app/components/backend/api/admin.py
from fastapi import APIRouter
from app.components.worker.pools import get_queue_pool

router = APIRouter()

@router.post("/admin/cleanup")
async def trigger_cleanup(days_old: int = 30):
    """Trigger cleanup via API."""
    pool, queue_name = await get_queue_pool("system")
    try:
        job = await pool.enqueue_job("cleanup_old_logs", days_old=days_old)
        return {"job_id": job.job_id, "status": "enqueued"}
    finally:
        await pool.aclose()
```

### From Scheduled Tasks

```python
# app/components/scheduler.py
from app.components.worker.pools import get_queue_pool

async def schedule_daily_cleanup():
    """Schedule daily cleanup task."""
    pool, queue_name = await get_queue_pool("system")
    try:
        await pool.enqueue_job("cleanup_old_logs", days_old=1)
    finally:
        await pool.aclose()
```

## Error Handling Examples

### Task with Retry Logic

```python
async def resilient_task(ctx, max_retries: int = 3) -> dict:
    """Task with built-in retry handling."""
    current_try = ctx.get('job_try', 1)
    
    try:
        # Your risky operation
        result = await perform_risky_operation()
        return {"status": "completed", "result": result}
        
    except TemporaryError as e:
        if current_try < max_retries:
            logger.warning(f"Temporary error on try {current_try}: {e}")
            raise  # Let arq retry
        else:
            logger.error(f"Permanent failure after {current_try} tries: {e}")
            return {"status": "failed", "error": str(e), "permanent": True}
            
    except PermanentError as e:
        logger.error(f"Permanent error: {e}")
        return {"status": "failed", "error": str(e), "permanent": True}
```

### Task Progress Tracking

```python
async def long_running_task(ctx, items: list[str]) -> dict:
    """Task with progress updates."""
    total_items = len(items)
    processed = 0
    
    for item in items:
        # Process item
        await process_item(item)
        processed += 1
        
        # Update progress every 10 items
        if processed % 10 == 0:
            progress = (processed / total_items) * 100
            logger.info(f"Progress: {progress:.1f}% ({processed}/{total_items})")
    
    return {
        "status": "completed",
        "items_processed": processed,
        "total_items": total_items
    }
```

## Multiple Queue Examples

### System Queue Tasks

```python
# app/components/worker/tasks/system_tasks.py
async def backup_database(ctx) -> dict:
    """Create database backup."""
    backup_file = await create_database_backup()
    return {"status": "completed", "backup_file": backup_file}

async def send_health_report(ctx) -> dict:
    """Send system health report."""
    report = await generate_health_report()
    await send_email_report(report)
    return {"status": "completed", "report_sent": True}
```

### Load Test Queue Tasks

```python
# app/components/worker/tasks/load_test_tasks.py
async def cpu_intensive_task(ctx, duration_seconds: int = 1) -> dict:
    """CPU-bound task for load testing."""
    import time
    start_time = time.time()
    
    # Simulate CPU work
    while time.time() - start_time < duration_seconds:
        _ = sum(i * i for i in range(1000))
    
    return {"status": "completed", "duration": duration_seconds}

async def io_intensive_task(ctx, delay_seconds: int = 1) -> dict:
    """I/O-bound task for load testing."""
    await asyncio.sleep(delay_seconds)
    return {"status": "completed", "delay": delay_seconds}
```

## Testing Worker Tasks

### Unit Testing

```python
# tests/worker/test_system_tasks.py
import pytest
from app.components.worker.tasks.system_tasks import cleanup_old_logs

@pytest.mark.asyncio
async def test_cleanup_old_logs():
    """Test log cleanup task."""
    # Mock context
    ctx = {"job_id": "test-job-123"}
    
    # Execute task
    result = await cleanup_old_logs(ctx, days_old=7)
    
    # Verify result
    assert result["status"] == "completed"
    assert "files_cleaned" in result
    assert isinstance(result["files_cleaned"], int)
```

### Integration Testing

```python
# tests/worker/test_integration.py
import pytest
from app.components.worker.pools import get_queue_pool

@pytest.mark.asyncio
async def test_task_enqueue_and_process():
    """Test full task lifecycle."""
    pool, queue_name = await get_queue_pool("system")
    
    try:
        # Enqueue job
        job = await pool.enqueue_job("cleanup_old_logs", days_old=1)
        assert job.job_id
        
        # Wait for processing (in test environment)
        result = await job.result(timeout=30)
        assert result["status"] == "completed"
        
    finally:
        await pool.aclose()
```

## Next Steps

- **[Configuration](configuration.md)** - Configure workers for your use case
- **[Load Testing](extras/load-testing.md)** - Test your implementation
- **[Back to Overview](index.md)** - Return to worker component overview