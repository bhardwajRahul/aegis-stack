# Worker Configuration

Comprehensive guide to configuring and scaling the worker component in your Aegis Stack application.

## Configuration Overview

??? note "Configuration Philosophy"
    Worker configuration follows the 12-Factor App methodology. Use environment variables for deployment-specific settings and keep defaults sensible for development.

## Worker Settings

Workers use arq's native `WorkerSettings` classes with direct task imports. Each queue has its own configuration:

### System Worker (`app/components/worker/queues/system.py`)

```python
from arq import RedisSettings
from app.components.worker.tasks.system import system_health_check

class WorkerSettings:
    functions = [system_health_check]
    queue_name = "arq:queue:system"
    max_jobs = 15
    job_timeout = 300
```

### Load Test Worker (`app/components/worker/queues/load_test.py`)

```python
from app.components.worker.tasks.load_test import light_cpu_task, light_io_task

class WorkerSettings:
    functions = [light_cpu_task, light_io_task]
    queue_name = "arq:queue:load_test"
    max_jobs = 30
    job_timeout = 600
```

### Global Configuration (`app/core/config.py`)

```python
class Settings(BaseSettings):
    # Redis settings for arq background tasks
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    
    # Shared arq worker settings
    WORKER_KEEP_RESULT_SECONDS: int = 3600
    WORKER_MAX_TRIES: int = 3
    
    # PURE ARQ - NO CONFIGURATION DICTIONARY NEEDED!
    # WorkerSettings classes access these values directly
    
    @property
    def redis_settings(self) -> RedisSettings:
        """Get Redis settings for arq workers."""
        return RedisSettings.from_dsn(
            self.REDIS_URL,
            database=self.REDIS_DB
        )
```

## Environment Variables

Configure worker behavior through environment variables:

```bash
# Docker environment (docker-compose.yml)
# WorkerSettings uses these environment variables through app.core.config
REDIS_URL=redis://redis:6379        # Redis connection for all workers
REDIS_DB=0                          # Redis database number
ENVIRONMENT=production              # Affects WorkerSettings logic
WORKER_KEEP_RESULT_SECONDS=3600     # Used by WorkerSettings.keep_result
WORKER_MAX_TRIES=3                  # Used by WorkerSettings.max_tries
```

### Local Development

```bash
# .env file for local development
REDIS_URL=redis://redis:6379        # Used by Docker containers
REDIS_URL_LOCAL=redis://localhost:6379  # Used by CLI commands running locally
REDIS_DB=0
WORKER_KEEP_RESULT_SECONDS=3600     # WorkerSettings will use this
WORKER_MAX_TRIES=3                  # WorkerSettings will use this  
ENVIRONMENT=development             # WorkerSettings can check this
APP_ENV=dev                         # Enables auto-reload in Docker
```

### CLI Command Configuration

When running CLI commands locally (outside Docker), the system automatically uses `REDIS_URL_LOCAL` if configured:

```bash
# Local CLI commands use this pattern:
# 1. Docker services connect to: redis://redis:6379
# 2. Local CLI commands connect to: redis://localhost:6379

# In your .env file:
REDIS_URL=redis://redis:6379        # For Docker containers
REDIS_URL_LOCAL=redis://localhost:6379  # For local CLI commands

# Example CLI usage (automatically uses REDIS_URL_LOCAL):
my-app load-test io
my-app health status
```

This dual-configuration approach allows:

- **Docker containers** to connect to the `redis` service  
- **Local CLI commands** to connect to `localhost` Redis without starting containers

### Production Settings

```bash
# Production environment variables
# These are used by WorkerSettings classes through app.core.config
ENVIRONMENT=production              # WorkerSettings can scale based on this
WORKER_KEEP_RESULT_SECONDS=1800     # WorkerSettings.keep_result
WORKER_MAX_TRIES=5                  # WorkerSettings.max_tries
REDIS_URL=redis://redis-prod:6379
REDIS_DB=1                          # Separate DB for production
REDIS_PASSWORD=your-secure-password
```

## Docker Integration

### docker-compose.yml Configuration

```yaml
services:
  worker:
    build: .
    command: ["worker"]
    environment:
      - ENVIRONMENT=production
      - WORKER_KEEP_RESULT_SECONDS=1800
      - WORKER_MAX_TRIES=5
      - REDIS_URL=redis://redis:6379
      - REDIS_DB=0
    depends_on:
      - redis
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
```

## Scaling Strategies

### Horizontal Scaling

Scale by running multiple worker containers:

```bash
# Scale to 3 worker instances
docker compose up --scale worker=3

# Or in docker-compose.yml
deploy:
  replicas: 3
```

### Vertical Scaling

Increase per-worker concurrency by modifying `WorkerSettings` classes:

```python
# app/components/worker/queues/system.py
class WorkerSettings:
    functions = [system_health_check]
    queue_name = "arq:queue:system"
    max_jobs = 30  # Increased from 15
    job_timeout = 300
    
# app/components/worker/queues/load_test.py
class WorkerSettings:
    functions = [light_cpu_task, light_io_task]
    queue_name = "arq:queue:load_test"
    max_jobs = 50  # Increased from 30
    job_timeout = 600
```

### Environment-Based Configuration

WorkerSettings classes can dynamically configure based on environment variables:

```python
# app/components/worker/queues/system.py
from app.core.config import settings
from arq import RedisSettings

class WorkerSettings:
    functions = [system_health_check]
    queue_name = "arq:queue:system"
    
    # Use environment values from settings
    keep_result = settings.WORKER_KEEP_RESULT_SECONDS
    max_tries = settings.WORKER_MAX_TRIES
    redis_settings = settings.redis_settings
    
    # Dynamic scaling based on environment
    max_jobs = 30 if settings.ENVIRONMENT == "production" else 15
    job_timeout = 300 if settings.ENVIRONMENT == "production" else 600
```

### Queue-Specific Scaling

Scale by modifying `WorkerSettings` classes directly:

```python
# app/components/worker/queues/system.py
from app.core.config import settings

class WorkerSettings:
    functions = [system_health_check]
    queue_name = "arq:queue:system"
    
    # Environment-based scaling
    max_jobs = 25 if settings.ENVIRONMENT == "production" else 15
    job_timeout = 300
    keep_result = 1800 if settings.ENVIRONMENT == "production" else 3600
    max_tries = 5 if settings.ENVIRONMENT == "production" else 3
    
    # Redis settings
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
```

## Redis Configuration

### Connection Settings

```python
# app/core/config.py
class Settings(BaseSettings):
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_MAX_CONNECTIONS: int = 100
    REDIS_CONNECTION_TIMEOUT: int = 5
    
    @property
    def redis_settings(self) -> RedisSettings:
        """Get Redis settings for arq."""
        return RedisSettings(
            host=self.REDIS_URL,
            database=self.REDIS_DB,
            password=self.REDIS_PASSWORD,
            max_connections=self.REDIS_MAX_CONNECTIONS,
            conn_timeout=self.REDIS_CONNECTION_TIMEOUT,
        )
```

### Redis Persistence

For production, configure Redis persistence:

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --save 900 1
    --save 300 10
    --save 60 10000
    --appendonly yes
  volumes:
    - redis-data:/data
    - ./redis.conf:/usr/local/etc/redis/redis.conf
```

## Performance Tuning

### Memory Management

Control memory usage through WorkerSettings properties:

```python
# app/components/worker/queues/system.py
class WorkerSettings:
    functions = [system_health_check]
    keep_result = 1800  # 30 minutes for production
    max_jobs = 15       # Limit concurrent jobs to manage memory
    
# app/components/worker/queues/load_test.py
class WorkerSettings:
    functions = [light_cpu_task, light_io_task]
    keep_result = 300   # Shorter retention for high-volume tests
    max_jobs = 50       # Higher concurrency for testing
```

### Timeout Configuration

Set timeouts based on task complexity in each `WorkerSettings` class:

```python
# app/components/worker/queues/system.py
class WorkerSettings:
    functions = [system_health_check, cleanup_temp_files]
    job_timeout = 60  # Quick system tasks
    
# app/components/worker/queues/media.py
class WorkerSettings:
    functions = [process_video, resize_images]
    job_timeout = 1800  # 30 minutes for large files
    max_jobs = 5  # Lower concurrency for resource-intensive tasks
    
# app/components/worker/queues/load_test.py
class WorkerSettings:
    functions = [light_cpu_task, light_io_task]
    job_timeout = 300  # 5 minutes for test runs
    max_jobs = 30
```

### Connection Pooling

```python
# Optimize Redis connection pooling
REDIS_MAX_CONNECTIONS = 50  # Per worker process
REDIS_CONNECTION_TIMEOUT = 5
REDIS_SOCKET_KEEPALIVE = True
REDIS_SOCKET_KEEPALIVE_OPTIONS = {
    1: 3,   # TCP_KEEPIDLE
    2: 3,   # TCP_KEEPINTVL
    3: 3,   # TCP_KEEPCNT
}
```

## Monitoring Configuration

### Health Check Settings

Health checks are built into each WorkerSettings configuration:

```python
# app/components/worker/queues/system.py
class WorkerSettings:
    functions = [system_health_check]  # This task provides health data
    
    # Health check behavior
    health_check_key = "worker:health:system"
    health_check_interval = 30  # seconds
    
    # arq built-in health monitoring
    keep_result = 3600  # Keep results for health queries
```

### Metrics Collection

Metrics are automatically collected by arq and available via Redis:

```python
# Check queue metrics with arq CLI
# arq app.components.worker.queues.system.WorkerSettings --check

# Or query Redis directly
# KEYS arq:queue:*
# HGETALL arq:queue:system
```

## Security Configuration

### Authentication

```python
# Redis authentication
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_USERNAME = os.getenv("REDIS_USERNAME")  # Redis 6.0+
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"
REDIS_SSL_CERT_REQS = "required" if REDIS_SSL else None
```

### Network Security

```yaml
# docker-compose.yml - Internal network only
services:
  worker:
    networks:
      - internal
    # No ports exposed
  
  redis:
    networks:
      - internal
    # Only expose for development
    ports:
      - "127.0.0.1:6379:6379"  # Localhost only

networks:
  internal:
    driver: bridge
    internal: true
```

## Advanced Configuration

### Custom Worker Classes

```python
# app/components/worker/custom.py
from arq import Worker

class CustomWorker(Worker):
    """Extended worker with custom behavior."""
    
    async def startup(self):
        """Initialize resources on worker startup."""
        await super().startup()
        # Custom initialization
        await init_database_pool()
        await setup_monitoring()
    
    async def shutdown(self):
        """Cleanup on worker shutdown."""
        # Custom cleanup
        await close_database_pool()
        await super().shutdown()
```

### Task Registration

See **[Examples](examples.md)** for complete task registration patterns.

## Next Steps

- **[Examples](examples.md)** - See configuration in action
- **[Load Testing](extras/load-testing.md)** - Test your configuration
- **[Back to Overview](index.md)** - Return to worker component overview