# CLI Reference

Complete reference for the Aegis Stack command-line interface.

## Global Options

These options work with all commands and must be specified **before** the command name.

**Usage:**
```bash
aegis [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

**Available Options:**

- `--verbose, -v` - Enable verbose output (show detailed file operations)
- `--help` - Show help message

**Examples:**
```bash
# Correct: Global flag before command
aegis --verbose init my-project
aegis --verbose add scheduler
aegis -v remove worker

# Incorrect: Global flag after command (will fail)
aegis init my-project --verbose  ❌
```

**What --verbose Shows:**
- Detailed file operation logs
- Template rendering details
- Component resolution steps
- Dependency installation progress

---

## Quick Start Commands

### aegis version

Show the Aegis Stack CLI version.

**Usage:**
```bash
aegis version
```

**Example Output:**
```
Aegis Stack CLI v0.2.1
```

### aegis components

List available components with their status and dependencies.

**Usage:**
```bash
aegis components
```

**Example Output:**
```
AVAILABLE COMPONENTS
========================================

Infrastructure Components
----------------------------------------
  scheduler     - APScheduler-based async task scheduling
  worker        - Pure arq worker with multiple queues (requires: redis)
  database      - SQLite database with SQLModel ORM
  redis         - Redis cache and message broker
```

### aegis services

List available services with their required components.

**Usage:**
```bash
aegis services
```

**Example Output:**
```
AVAILABLE SERVICES
========================================

Authentication Services
----------------------------------------
  auth         - User authentication and authorization with JWT tokens
               Requires components: backend, database

AI & Machine Learning Services
----------------------------------------
  ai           - AI chatbot with PydanticAI engine
               Requires components: backend
               Supports: OpenAI, Anthropic, Google, Groq, Mistral, Cohere
```

---

## Project Management Commands

### aegis init

Create a new Aegis Stack project with your chosen components and services.

**Usage:**
```bash
aegis init PROJECT_NAME [OPTIONS]
```

**Arguments:**

- `PROJECT_NAME` - Name of the new project to create (required)

**Options:**

- `--components, -c TEXT` - Comma-separated list of components
- `--services, -s TEXT` - Comma-separated list of services
- `--interactive / --no-interactive, -i / -ni` - Use interactive selection (default: interactive)
- `--force, -f` - Overwrite existing directory if it exists
- `--output-dir, -o PATH` - Directory to create the project in (default: current directory)
- `--yes, -y` - Skip confirmation prompt

**Examples:**
```bash
# Simple API project
aegis init my-api

# Background processing with scheduler
aegis init task-processor --components scheduler

# User authentication system
aegis init user-app --services auth --components database

# AI chatbot application
aegis init chatbot --services ai

# Full stack with auth and AI
aegis init full-app --services auth,ai --components database,scheduler

# Non-interactive with custom location
aegis init my-app --services auth --components database --no-interactive --output-dir /projects --yes
```

**Available Components:**

| Component | Status | Description |
|-----------|--------|-------------|
| `scheduler` | ✅ Available | APScheduler-based async task scheduling |
| `scheduler[sqlite]` | ✅ Available | Scheduler with SQLite persistence (auto-adds database) |
| `worker` | ✅ Available | arq worker with Redis for background processing (auto-adds redis) |
| `database` | ✅ Available | SQLite database with SQLModel ORM |
| `redis` | ✅ Available | Redis cache and message broker |
| `cache` | 🚧 Coming Soon | Redis-based async caching layer |

**Available Services:**

| Service | Status | Description | Required Components |
|---------|--------|-------------|---------------------|
| `auth` | ✅ Available | User authentication with JWT tokens | backend, database |
| `ai` | 🧪 Experimental | AI chatbot with 7 provider options | backend |
| `comms` | 🧪 Experimental | Email (Resend), SMS & voice (Twilio) | backend |

**Service Auto-Resolution:**

When you select services, required components are automatically added:

- `--services auth` → Auto-adds `database` component
- `--services ai` → No additional components (backend always included)
- `--services comms` → No additional components (backend always included)
- Backend and frontend components are **always included** in every project

**Component Dependencies:**

Some components require others and will be auto-added:

- `worker` → Auto-adds `redis`
- `scheduler[sqlite]` → Auto-adds `database`

**Examples with Auto-Resolution:**
```bash
# Auth service auto-adds database
aegis init user-app --services auth
# Result: backend + frontend + database + auth service

# Worker auto-adds redis
aegis init task-app --components worker
# Result: backend + frontend + redis + worker

# Scheduler with SQLite auto-adds database
aegis init cron-app --components "scheduler[sqlite]"
# Result: backend + frontend + database + scheduler
```

---

### aegis add

Add components to an existing Aegis Stack project.

**Usage:**
```bash
aegis add COMPONENTS [OPTIONS]
```

**Arguments:**

- `COMPONENTS` - Comma-separated list of components to add

**Options:**

- `--backend, -b TEXT` - Scheduler backend: 'memory' (default) or 'sqlite' (enables persistence)
- `--interactive, -i` - Use interactive component selection
- `--project-path, -p PATH` - Path to the Aegis Stack project (default: current directory)
- `--yes, -y` - Skip confirmation prompt

**Examples:**
```bash
# Add scheduler with memory backend
aegis add scheduler

# Add scheduler with SQLite persistence
aegis add scheduler --backend sqlite
# or using bracket syntax
aegis add "scheduler[sqlite]"

# Add worker (auto-includes redis)
aegis add worker

# Add multiple components
aegis add database,scheduler

# Add to specific project
aegis add scheduler --project-path ../my-project

# Interactive mode
aegis add --interactive
```

**How It Works:**

1. Validates project was generated with Copier
2. Checks component dependencies (auto-adds required components)
3. Renders component templates with Jinja2
4. Copies files to project (skips existing files)
5. Updates `.copier-answers.yml` with new configuration
6. Regenerates shared files (docker-compose.yml, pyproject.toml)
7. Runs `uv sync` to install new dependencies
8. Runs `make fix` to format code

**Notes:**

- Components added incrementally without breaking existing code
- Shared files automatically regenerated with backups
- Changes are non-destructive (commit before running for easy rollback)
- Use `--verbose` flag to see detailed operation logs

---

### aegis add-service

Add services to an existing Aegis Stack project.

**Usage:**
```bash
aegis add-service SERVICES [OPTIONS]
```

**Arguments:**

- `SERVICES` - Comma-separated list of services to add

**Options:**

- `--interactive, -i` - Use interactive service selection
- `--project-path, -p PATH` - Path to the Aegis Stack project (default: current directory)
- `--yes, -y` - Skip confirmation prompt

**Examples:**
```bash
# Add auth service (auto-adds database if not present)
aegis add-service auth

# Add AI service
aegis add-service ai

# Add multiple services
aegis add-service auth,ai

# Interactive service selection
aegis add-service --interactive

# Non-interactive with auto-yes
aegis add-service auth --yes --project-path ../my-project
```

**Service Auto-Resolution:**

Services automatically add their required components if missing:

- `auth` → Requires `database` component (auto-added if missing)
- `ai` → Requires `backend` component (always present)

**Post-Addition Setup:**

After adding services, follow these steps:

**For Auth Service:**
```bash
make migrate                       # Apply auth database migrations
my-project auth create-test-users  # Create test users for development
my-project auth list-users         # Verify users created
```

**For AI Service:**

Configure provider in `.env`:
```env
AI_PROVIDER=public  # Options: public, openai, anthropic, google, groq, mistral, cohere

# For paid providers, add API key:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

Test the AI service:
```bash
my-project ai status               # Check configuration
my-project ai chat                 # Start interactive chat
my-project ai providers            # See all available providers
```

**Important Notes:**

- Only works with Copier-generated projects (default since v0.2.0)
- Requires git repository (for change tracking)
- Services require their dependencies - they will be auto-added
- Review changes with `git diff` before committing

See **Generated Project CLI** section below for full command reference.

---

### aegis remove

Remove components from an existing Aegis Stack project.

**Usage:**
```bash
aegis remove COMPONENTS [OPTIONS]
```

**Arguments:**

- `COMPONENTS` - Comma-separated list of components to remove

**Options:**

- `--interactive, -i` - Use interactive component selection
- `--project-path, -p PATH` - Path to the Aegis Stack project (default: current directory)
- `--yes, -y` - Skip confirmation prompt

**Examples:**
```bash
# Remove scheduler component
aegis remove scheduler

# Remove multiple components
aegis remove scheduler,worker

# Interactive mode
aegis remove --interactive
```

**How It Works:**

1. Validates project was generated with Copier
2. Checks component is currently enabled
3. Deletes component files and directories
4. Cleans up empty parent directories
5. Updates `.copier-answers.yml` to disable component
6. Regenerates shared files (docker-compose.yml, pyproject.toml)
7. Runs `uv sync` to clean up unused dependencies
8. Runs `make fix` to format code

**Important Warnings:**

- **THIS OPERATION DELETES FILES** - Commit your changes to git first
- Core components (backend, frontend) cannot be removed
- Removing scheduler with SQLite persistence leaves `data/scheduler.db` intact
- Shared template files are regenerated (backups created automatically)
- Redis is auto-removed when worker is removed (no standalone functionality)

---

### aegis update

Update an existing Copier-based project to the latest template version.

**Usage:**
```bash
aegis update [OPTIONS]
```

**Options:**

- `--project-path PATH` - Path to project to update (default: current directory)
- `--to-version TEXT` - Update to specific template version (default: latest)
- `--force, -f` - Accept all template changes automatically
- `--yes, -y` - Skip confirmation prompt
- `--dry-run` - Preview changes without applying them

**Examples:**
```bash
# Update current project to latest template
aegis update

# Update specific project
aegis update --project-path ../my-project

# Update to specific template version
aegis update --to-version 0.2.0

# Preview changes without applying
aegis update --dry-run

# Auto-accept all updates
aegis update --force --yes
```

**How It Works:**

1. Validates project was generated with Copier
2. Checks current template version from `.copier-answers.yml`
3. Fetches latest template version (or specified version)
4. Compares current files with template updates
5. Shows diff of changes to be applied
6. Prompts for conflict resolution
7. Applies updates and creates backup files
8. Runs `uv sync` to update dependencies
9. Runs `make fix` to format updated code

**What Gets Updated:**

- ✅ Template infrastructure files
- ✅ Shared files (docker-compose.yml, pyproject.toml, Makefile)
- ✅ Component implementations (if unmodified)
- ✅ Test infrastructure
- ✅ Documentation templates

**What's Preserved:**

- ✅ Your custom business logic
- ✅ Your environment variables (.env)
- ✅ Your database migrations
- ✅ Your custom models and services
- ✅ Files you've modified (marked as conflicts)

**Important Notes:**

- **Always commit before updating**: `git add . && git commit -m "Pre-update checkpoint"`
- **Test after updating**: Run `make check` to verify everything works
- Use `--dry-run` first to preview changes

---

## Generated Project CLI

When you add services to a project, they install their own CLI commands as entry point scripts. These commands are available after running `uv sync` in your generated project.

**Script Installation:**

All generated projects get a CLI script matching the project name:
```bash
# If project is named "my-app"
my-app --help

# If project is named "chatbot"
chatbot --help
```

### Component CLIs

Components that add CLI capabilities to your generated projects:

**Scheduler** - `my-app tasks`

Manage scheduled tasks with persistent job tracking:

```bash
my-app tasks list       # List all scheduled jobs
my-app tasks stats      # View scheduler statistics
my-app tasks history    # View execution history
```

**→ [Complete Scheduler CLI Reference](components/scheduler/cli.md)**

**Worker** - Native `arq` CLI

Background task processing with Redis-backed queues:

```bash
arq my_project.components.worker.WorkerSettings  # Start worker
arq --watch my_project.components.worker.WorkerSettings  # Auto-reload
```

**→ [Complete Worker CLI Reference](components/worker/cli.md)**

### Service CLIs

Services that add CLI capabilities to your generated projects:

**Auth Service** - `my-app auth`

User management and testing utilities:

```bash
my-app auth create-test-user   # Create single test user
my-app auth create-test-users  # Create multiple test users
my-app auth list-users         # List all users
```

**→ [Complete Auth CLI Reference](services/auth/cli.md)**

**AI Service** - `my-app ai`

Multi-provider AI chat interface with conversation management:

```bash
my-app ai status               # Show configuration and validation
my-app ai providers            # List all 7 AI providers
my-app ai chat "Hello"         # Send single message
my-app ai chat                 # Interactive chat session
my-app ai conversations        # List user conversations
my-app ai history <id>         # View conversation history
```

**→ [Complete AI CLI Reference](services/ai/cli.md)**

---

## Project Structure

Projects created with `aegis init` follow this structure:

```
my-project/
├── app/
│   ├── components/
│   │   ├── backend/        # FastAPI backend
│   │   ├── frontend/       # Flet frontend
│   │   ├── scheduler.py    # APScheduler (if included)
│   │   ├── worker/         # arq worker queues (if included)
│   │   └── database.py     # Database setup (if included)
│   ├── core/              # Framework utilities
│   ├── services/          # Business logic
│   ├── cli/               # CLI commands (if services added)
│   └── integrations/      # App composition
├── tests/                 # Test suite
├── docs/                  # Documentation
├── data/                  # SQLite databases (if database included)
├── pyproject.toml         # Project configuration
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-service orchestration
├── Makefile              # Development commands
└── .env.example          # Environment template
```

---

## Development Workflow

After creating a project:

```bash
cd my-project
uv sync                    # Install dependencies and create virtual environment
source .venv/bin/activate  # Activate virtual environment (important!)
cp .env.example .env       # Configure environment (edit API keys, etc.)
make serve                 # Start development server
make test                  # Run test suite
make check                 # Run all quality checks (lint + typecheck + test)
```

### Evolving Your Project

```bash
# Add components as you need them
aegis add scheduler
aegis add worker

# Add services for new features
aegis add-service auth
aegis add-service ai

# Remove components you don't need
aegis remove scheduler

# Update to latest template version
aegis update

# Always commit before making changes
git add . && git commit -m "Add scheduler component"
```

### Best Practices

1. **Commit before evolving**: Always commit your work before adding/removing components
2. **Use verbose mode**: Add `--verbose` flag to see detailed operations
3. **Test after changes**: Run `make check` after adding/removing components
4. **Review diffs**: Use `git diff` to see what changed after operations
5. **Update regularly**: Keep your project in sync with latest template via `aegis update`

---

## Environment

The CLI respects these environment variables:

- Standard Python environment variables
- UV environment variables (for dependency management)
- Project-specific variables (when running generated CLI commands)
