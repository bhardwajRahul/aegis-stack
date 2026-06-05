# Scheduler CLI Interface

**Part of the Generated Project CLI** - See [CLI Reference](../../cli-reference.md#component-clis) for complete overview.

!!! warning "Persistence Required"
    The scheduler CLI is only available when using database persistence for job storage.
    Memory-based scheduling (default) does not support CLI operations.

    Enable persistence with: `aegis init my-app --components scheduler,database`

The scheduler provides a `tasks` CLI for managing scheduled jobs when persistence is enabled.

## Quick Start

```bash
# List all scheduled jobs
my-app tasks list

# Run a job right now
my-app tasks trigger database_backup

# See a job's execution stats
my-app tasks stats database_backup

# See recent execution history
my-app tasks history
```

## Commands

### `tasks list`

List all scheduled jobs with their status and next run times.

```bash
my-app tasks list
```

Shows:

- **Job ID** - Unique identifier for the scheduled task
- **Name** - Human-readable job name
- **Status** - `Active` (scheduled) or `Paused`
- **Next Run** - When the job will execute next
- **Trigger** - The trigger type (`cron`, `interval`, `date`)

### `tasks trigger`

Run a scheduled job immediately, in the CLI process, and record the run to
execution history (so it also shows up in the dashboard History tab).

```bash
my-app tasks trigger JOB_ID [--force]
```

The command waits for the job to finish and reports the outcome. By default it
refuses to start if a previous run of the same job is still in progress; pass
`--force` (`-f`) to run anyway.

**Example:**
```bash
$ my-app tasks trigger database_backup
Running job: Daily Database Backup
Job completed successfully: Daily Database Backup
```

!!! note "Runs in the calling environment"
    `tasks trigger` runs the job **in the process you invoke it from** (unlike
    the dashboard's Run Now, which runs it in the backend). Jobs that shell out
    to system tools (the `database_backup` job calls `pg_dump`, which must be
    at least the server's major version) therefore depend on your environment.
    Run such jobs where a matching client lives -- inside the container:

    ```bash
    docker compose exec scheduler my-app tasks trigger database_backup
    ```

    Running from a host with an older/missing client fails with a clear error
    rather than a misleading success.

A failing job records the failure (with traceback) to history and exits
non-zero, so it composes with scripts and CI.

### `tasks stats`

Show aggregate execution statistics for a single job.

```bash
my-app tasks stats JOB_ID
```

**Example:**
```
$ my-app tasks stats database_backup
          Execution Stats: database_backup
┌──────────────────┬───────────────────────────────┐
│ Total runs       │ 3                             │
│ Succeeded        │ 2                             │
│ Failed           │ 1                             │
│ Success rate     │ 66.7%                         │
│ Average duration │ 142 ms                        │
│ Last run         │ success @ 2026-06-04 20:16:05 │
└──────────────────┴───────────────────────────────┘
```

Stats are computed from the retained execution history (up to ~100 runs per
job). A job with no recorded runs prints a short notice instead.

### `tasks history`

Show recent job execution history, newest first.

```bash
my-app tasks history [--job JOB_ID] [--limit N]
```

**Options:**

- `--job`, `-j JOB_ID` - Only show history for this job
- `--limit`, `-n N` - Maximum number of records to show (default: 20)

**Example:**
```
$ my-app tasks history --job database_backup --limit 5
                          Execution History
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Started             ┃ Name                  ┃ Status  ┃   Duration ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ 2026-06-04 20:16:05 │ Daily Database Backup │ success │      90 ms │
└─────────────────────┴───────────────────────┴─────────┴────────────┘

Total executions: 3
```

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
- **[Database Persistence](persistence.md)** - Job persistence setup