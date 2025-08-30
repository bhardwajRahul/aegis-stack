# Load Testing Extra

Built-in performance testing capabilities for the worker component.

!!! info "Extra Component"
    Adds a dedicated `load_test` queue with 30 concurrent workers for performance testing.

## What You Get

- **Dedicated load test queue** - Isolated from production workloads
- **Performance benchmarking** - CPU, I/O, and memory tests  
- **CLI commands** - Quick testing interface
- **API endpoints** - Programmatic testing

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

## Architecture

The load testing extra adds one additional queue:

| Queue | Concurrency | Purpose |
|-------|:-----------:|---------|
| **load_test** | 30 jobs | Performance testing and benchmarking |

!!! danger "Isolation Required"
    Never use the load_test queue for production tasks.

## Running Workers

```bash
# Standard arq command
arq app.components.worker.queues.load_test.WorkerSettings

# With Docker
docker compose up worker-load-test
```

## Test Types

- **CPU**: Fibonacci calculations, computational work
- **I/O**: Simulated network delays, async operations  
- **Memory**: Large data structures, allocation patterns

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