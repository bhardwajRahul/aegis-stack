# Scheduler CLI Interface

**Part of the Generated Project CLI** - See [CLI Reference](../../cli-reference.md#component-clis) for complete overview.

!!! warning "Persistence Required"
    The scheduler CLI is only available when using database persistence for job storage.
    Memory-based scheduling (default) does not support CLI operations.

    Enable persistence with: `aegis init my-app --components scheduler,database`

The scheduler provides a `tasks` CLI for managing scheduled jobs when persistence is enabled.

## Quick Start

```bash
# Check if CLI is available
my-app --help

# List all scheduled jobs
my-app tasks list

# View scheduler statistics
my-app tasks stats

# View execution history
my-app tasks history
```

## Commands

### `tasks list`

List all scheduled jobs with their status and next run times.

```bash
my-app tasks list
```

**Example Output:**
```
Scheduled Jobs (1 total)
┌─────────────────────┬───────────────────────┬─────────┬──────────────────────────────┐
│ Job ID              │ Name                  │ Status  │ Next Run                     │
├─────────────────────┼───────────────────────┼─────────┼──────────────────────────────┤
│ daily_health_check  │ Daily Health Check    │ active  │ 2024-09-07 09:00:00          │
└─────────────────────┴───────────────────────┴─────────┴──────────────────────────────┘
```

Shows:

- **Job ID** - Unique identifier for the scheduled task
- **Name** - Human-readable job name
- **Status** - `active` (scheduled) or `paused`
- **Next Run** - When the job will execute next

### `tasks stats`

View overall scheduler statistics and metrics.

```bash
my-app tasks stats
```

**Example Output:**
```
Overall Scheduler Statistics
╭───────────────────────────────────────────────────────── Scheduler Statistics ──────────────────────────────────────────────────────────╮
│ Scheduler Overview                                                                                                                      │
│                                                                                                                                         │
│ Total Jobs: 1                                                                                                                           │
│ Active Jobs: 1                                                                                                                          │
│ Paused Jobs: 0                                                                                                                          │
│                                                                                                                                         │
│ Total Executions: 0                                                                                                                     │
│ Successful: 0                                                                                                                           │
│ Failed: 0                                                                                                                               │
│                                                                                                                                         │
│ Overall Success Rate: 0.0%                                                                                                              │
│ Avg Execution Time: 0.0ms                                                                                                               │
│                                                                                                                                         │
│ Scheduler Uptime: Unknown                                                                                                               │
│ Last Activity: No recent activity                                                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

**Job-Specific Statistics:**
```bash
my-app tasks stats --job-id JOB_ID
```

**Example:**
```bash
my-app tasks stats --job-id daily_health_check
```

### `tasks history`

View recent job execution history.

```bash
my-app tasks history [--limit N] [--job-id JOB_ID]
```

**Options:**

- `--limit N` - Limit results to N most recent executions (default: 10)
- `--job-id JOB_ID` - Filter to specific job only

**Examples:**
```bash
# Last 10 executions across all jobs
my-app tasks history

# Last 20 executions  
my-app tasks history --limit 20

# History for specific job
my-app tasks history --job-id daily_health_check

# Last 5 runs of specific job
my-app tasks history --job-id cleanup_temp_files --limit 5
```

### `tasks trigger`

Trigger manual execution of a scheduled job.

```bash
my-app tasks trigger JOB_ID [--wait] [--timeout SECONDS]
```

**Options:**

- `--wait` - Wait for job completion before returning
- `--timeout SECONDS` - Maximum wait time when using `--wait` (default: 30)

**Examples:**
```bash
# Trigger job and return immediately
my-app tasks trigger daily_health_check

# Trigger job and wait for completion
my-app tasks trigger daily_health_check --wait

# Trigger with custom timeout
my-app tasks trigger cleanup_temp_files --wait --timeout 60
```

!!! warning "Implementation Status"
    Manual job triggering is currently not implemented but is planned for future releases.
    The command will return an appropriate message indicating this limitation.

## CLI Availability

### Checking CLI Status

The tasks CLI is automatically available when your project includes both scheduler and database components:

```bash
# Check available commands
my-app --help
```

**Example Output:**
```
 Usage: my-app [OPTIONS] COMMAND [ARGS]...                                                                                                   
                                                                                                                                             
 full-stack management CLI                                                                                                                   
                                                                                                                                             

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                                   │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                            │
│ --help                        Show this message and exit.                                                                                 │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ health      System health monitoring commands                                                                                             │
│ load-test   Load testing commands for worker performance analysis                                                                         │
│ tasks       Scheduled task management commands                                                                                            │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

The `tasks` command appears when your project includes both scheduler and database components.

### Troubleshooting CLI Issues

**CLI command not found:**
```bash
# Verify components are included
ls app/components/
# Should show both 'scheduler' and database-related files

# Check project was created with database component
grep -r "include_database" . || echo "Database not included"
```

**"Persistence not available" errors:**

- Ensure database is running: `make serve` (starts all services)
- Check database connectivity: `my-app health detailed`
- Verify database tables exist (created automatically on first scheduler start)

## Integration with Development Workflow

### Development Commands
```bash
# Start all services (including database for CLI)
make serve

# Check scheduler health (includes CLI availability)
make health-detailed

# View scheduler logs while testing CLI
make logs-scheduler
```

### Production Usage
```bash
# In production, ensure database persistence is configured
export DATABASE_URL=sqlite:///data/app.db

# CLI works the same way in production containers
docker exec my-app-container my-app tasks list
```

## See Also

- **[CLI Reference](../../cli-reference.md)** - Complete CLI overview and all commands
- **[Scheduler Component](../scheduler.md)** - Main scheduler documentation
- **[Examples](examples.md)** - Real-world scheduling patterns
- **[Database Persistence](extras/persistence.md)** - Job persistence setup