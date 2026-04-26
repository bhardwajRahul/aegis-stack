# Load Testing Extra

Built-in performance testing capabilities for the worker component.

!!! info "Extra Component"
    Adds a dedicated `load_test` queue with 50 concurrent jobs for performance testing.

## What You Get

- **Dedicated load test queue** - Isolated from production workloads
- **Performance benchmarking** - CPU, I/O, and memory tests
- **CLI commands** - Quick testing interface
- **API endpoints** - Programmatic testing
- **Real-time dashboard** - SSE-based live completion tracking (all backends)

## Quick Usage

```bash
# CPU testing
full-stack load-test cpu --tasks 50

# I/O testing
full-stack load-test io --tasks 100

# Memory testing
full-stack load-test memory --tasks 200

# View results
full-stack load-test results <task_id>
```

### See It In Action

![Load Testing Demo](../../../images/load_tests.gif)

!!! note "About This Demo"
    This GIF shows CPU-intensive tasks being processed. Since CPU tasks don't run async by default, you'll notice the recommendation to increase worker count for better throughput.

    Had we run I/O or memory tests instead, they would demonstrate much faster async processing with fewer workers needed.

## Architecture

The load testing extra adds one additional queue:

| Queue | Concurrency | Purpose |
|-------|:-----------:|---------|
| **load_test** | 50 jobs | Performance testing and benchmarking |

!!! danger "Isolation Required"
    Never use the load_test queue for production tasks.

## Running Workers

=== "arq"

    ```bash
    # Standard arq command
    arq app.components.worker.queues.load_test.WorkerSettings

    # With Docker
    docker compose up worker-load-test
    ```

=== "Dramatiq"

    ```bash
    # Run both system and load_test queues together
    dramatiq app.components.worker.broker \
      app.components.worker.queues.system \
      app.components.worker.queues.load_test \
      --queues system load_test

    # With Docker
    docker compose up worker
    ```

    !!! info "Dramatiq queue isolation"
        Specify `--queues load_test` to run a worker that processes only load test tasks, keeping CPU-intensive benchmark work away from your system queue.

=== "TaskIQ"

    ```bash
    taskiq worker app.components.worker.queues.load_test:broker
    ```

## Orchestrator Pattern

Each backend uses an orchestrator to enqueue load test tasks in batches. A Redis lock prevents concurrent load tests (`aegis:load_test:lock` with 10-minute TTL).

=== "arq"

    The arq orchestrator enqueues tasks via the standard pool interface:

    ```python
    async def run_load_test(task_type: str, task_count: int) -> dict:
        """Enqueue load test tasks via arq pool."""
        pool, queue_name = await get_queue_pool("load_test")
        try:
            job_ids = []
            for _ in range(task_count):
                job = await pool.enqueue_job(
                    f"{task_type}_task", _queue_name=queue_name
                )
                job_ids.append(job.job_id)
            return {"status": "enqueued", "task_count": task_count, "job_ids": job_ids}
        finally:
            await pool.aclose()
    ```

=== "Dramatiq"

    Dramatiq uses a **fire-and-forget orchestrator actor**. The orchestrator enqueues all individual tasks and returns immediately — it does not wait for them to complete:

    ```python
    @dramatiq.actor(queue_name="load_test", store_results=True)
    async def run_load_test_orchestrator(task_type: str, task_count: int) -> dict:
        """Enqueue load test tasks and return immediately."""
        messages = []
        for _ in range(task_count):
            if task_type == "io":
                msg = await asyncio.to_thread(io_simulation_task.send)
            elif task_type == "cpu":
                msg = await asyncio.to_thread(cpu_intensive_task.send)
            messages.append(msg.message_id)

        return {
            "status": "enqueued",
            "task_count": task_count,
            "message_ids": messages,
        }
    ```

    Note the `asyncio.to_thread` wrapper — Dramatiq's `.send()` is a synchronous Redis LPUSH.

=== "TaskIQ"

    The TaskIQ orchestrator is itself a task that spawns individual tasks via `.kiq()` in batches:

    ```python
    @broker.task
    async def load_test_orchestrator(
        num_tasks: int = 100,
        task_type: str = "io",
        batch_size: int = 10,
    ) -> dict:
        """Enqueue load test tasks in batches."""
        task_func = _get_task_by_type(task_type)
        task_handles = []

        for batch_start in range(0, num_tasks, batch_size):
            batch_end = min(batch_start + batch_size, num_tasks)
            for _ in range(batch_end - batch_start):
                handle = await task_func.kiq()
                task_handles.append(handle)

        return {
            "status": "enqueued",
            "task_count": num_tasks,
            "task_ids": [str(h.task_id) for h in task_handles[:10]],
        }
    ```

    TaskIQ's `.kiq()` is already async, so no thread wrapping is needed.

The dashboard SSE stream shows real-time completion as individual tasks finish, regardless of which backend is used.

## Test Types

- **CPU**: Fibonacci calculations, computational work
- **I/O**: Simulated network delays, async operations
- **Memory**: Large data structures, allocation patterns

## Dashboard SSE Monitoring

All backends publish task lifecycle events to Redis Streams via `EventPublishMiddleware`. The dashboard subscribes to these events via Server-Sent Events (SSE) and displays real-time completion:

- Tasks enqueued shows immediately in the queue depth counter
- Completions decrement the counter in real time
- Failed tasks are highlighted separately
- The load test panel shows throughput and failure rate as results arrive

This works identically across arq, TaskIQ, and Dramatiq backends.

## Results

Tests return performance metrics and analysis:

```json
{
  "throughput": 22.03,
  "failure_rate_percent": 0.2,
  "performance_rating": "good",
  "recommendations": ["Consider increasing batch size"]
}
```

## Best Practices

- Start with 100 tasks and scale up
- Monitor resources during tests
- Use dedicated load_test queue only
- Document baseline performance
- Use the Redis lock to prevent concurrent tests in automated pipelines
