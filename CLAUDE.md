# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

**Aegis Stack is a CLI tool for generating containerized Python applications.** It is NOT a runnable application itself.

The architecture follows this pattern:
- **CLI Tool** (`aegis-stack`): Installable via `pip install aegis-stack`
- **Generated Projects**: Full-stack containerized applications created by the CLI
- **Templates**: Cookiecutter templates that define generated project structure

## Development Commands

This project uses `uv` for dependency management and a `Makefile` for CLI development tasks.

### CLI Development Commands
- `make test` - Run the CLI test suite with pytest
- `make lint` - Run linting with ruff  
- `make typecheck` - Run type checking with mypy
- `make check` - Run all checks (lint + typecheck + test) - **run this before committing**
- `make install` or `uv sync --all-extras` - Install/sync dependencies
- `make cli-test` - Test CLI commands locally
- `make docs-serve` - Serve tool documentation locally on port 8001

### Template Development & Testing
- `make test-template-quick` - Quick template test without validation
- `make test-template` - Full template test with validation
- `make test-template-with-components` - Test template with scheduler component
- `make clean-test-projects` - Remove generated test projects

**Template testing is critical** - always run `make test-template` after modifying templates to ensure generated projects work correctly.

## CRITICAL: Template Development Workflow

**NEVER edit generated test projects directly!** Always follow this workflow:

### ✅ Correct Template Development Process:
1. **Edit template files only** in `aegis/templates/cookiecutter-aegis-project/{{cookiecutter.project_slug}}/`
2. **Generate fresh test project**: `make test-template` or `aegis init test-project`  
3. **Run tests on generated project** to verify template changes work
4. **If tests fail**: Fix the **template files** (step 1), then regenerate (step 2)
5. **Delete test project** when done - it's just for validation
6. **Repeat** until all tests pass

### ❌ Wrong Approach (DO NOT DO):
- ❌ Editing files in generated test projects (`../test-basic-stack/`, etc.)
- ❌ Making changes to temporary test artifacts
- ❌ Assuming test project changes affect future `aegis init` projects

### Why This Matters:
- Only **template files** affect future `aegis init new-project` commands
- Generated test projects are **temporary validation artifacts** 
- Editing test projects wastes time and creates confusion about what's actually fixed
- Template changes must be validated by regenerating fresh projects

**Remember: Templates → Generate → Test → Fix Templates → Repeat**

## CLI Architecture

Aegis Stack is built around a CLI-first approach for project generation and management.

### CLI Commands

#### `aegis init PROJECT_NAME`
The main command for creating new Aegis Stack projects with customizable components.

**Key files:**
- `aegis/__main__.py` - Main CLI entry point and command definitions
- `aegis/templates/cookiecutter-aegis-project/` - Cookiecutter template structure
- `aegis/templates/cookiecutter-aegis-project/hooks/post_gen_project.py` - Template processing logic
- `aegis/templates/cookiecutter-aegis-project/cookiecutter.json` - Template configuration

**Options:**
- `--components COMPONENTS` - Comma-separated list of components (redis,worker,scheduler)
- `--output-dir PATH` - Custom output directory
- `--no-interactive` - Skip prompts
- `--force` - Overwrite existing directories
- `--yes, -y` - Auto-confirm prompts

#### `aegis components`
Shows project information and available components.

## Coding Standards

### Git and Version Control
**DO NOT perform git operations unless explicitly requested.** This includes:
- No `git add`, `git commit`, or `git push` commands
- No creating pull requests
- Wait for explicit user approval before committing changes

### Python Style Guidelines

**Type Hints (MANDATORY - Fortress-Level Type Safety):**
- **NEVER** write untyped functions - all functions MUST have complete type annotations
- Use `str | None` instead of `Optional[str]` (Union syntax preferred)
- **ALWAYS** include return type hints on functions (use `-> None` if no return value)
- **ALWAYS** type function parameters, including `ctx` parameters: `ctx: dict[str, Any]`
- Use `dict[str, Any]` instead of `Dict[str, Any]` (modern Python syntax)
- Prefer `list[str]` over `List[str]` (built-in generics)

**Function Design:**
- Keep functions small and focused (max ~20 lines)
- Use descriptive names: `get_user_health_status()` not `get_data()`
- Return early for error conditions (guard clauses)
- Prefer pure functions when possible

**Error Handling:**
- Use specific exception types, not bare `except:`
- Raise meaningful exceptions with context
- Use `from None` to suppress chaining when appropriate
- Log errors at appropriate levels

### DRY Principle (Don't Repeat Yourself)
**Always look for existing code being used in multiple places.** Before writing new code, heavily weigh towards creating a single function imported to other places rather than duplicating logic.

### Scope Control: Stay Focused
**Keep changes minimal and targeted.** When fixing a specific issue:

1. **Identify the core problem** - Fix exactly what's broken, nothing more
2. **Avoid scope creep** - Don't add extensive test suites unless specifically requested
3. **Make minimal viable fixes** - Simple, working solutions over complex architectures
4. **Test the fix works** - Verify the original issue is resolved

### Code Quality Checks
**Always run `make check` after making coding changes.** This runs linting, type checking, and tests to ensure code quality and catch issues early.

```bash
make check  # Runs: lint + typecheck + test
```

## CRITICAL TERMINOLOGY REMINDERS
- **NEVER call components "services"** - Components are foundation capabilities (scheduler, database, cache)
- **NEVER use "scheduler_service"** - Always use "scheduler_component" or the actual instance name
- **Components are NOT microservices** - They are independent components that can run separately
- **Scheduler is a COMPONENT** - Never call it a service, microservice, or scheduler_service

### COMPONENT VS SERVICE BOUNDARIES

**Components (`app/components/`):**
- Foundation capabilities (scheduler, backend, frontend, database, cache)
- Own their infrastructure and job/route/UI definitions
- Examples:
  - `app/components/scheduler.py` - defines scheduled tasks AND scheduling infrastructure
  - `app/components/backend/api/` - defines API routes AND FastAPI setup
  - `app/components/frontend/` - defines UI components AND Flet setup

**Services (`app/services/`):**
- Business logic that components can call
- Should NOT directly define hooks, jobs, or routes
- Examples:
  - `app/services/report_service.py` - report generation logic
  - `app/services/email_service.py` - email sending logic  
  - `app/services/file_service.py` - file processing logic

**Key Pattern:**
- Components define WHEN/WHERE things happen (routes, scheduled jobs, UI components)
- Services define WHAT happens (business logic)
- Components call services, not vice versa
- Job definitions belong in scheduler component, not in services

## Specialized Documentation

For specific development contexts, see these specialized CLAUDE.md files:

### 🧪 Testing (`tests/CLAUDE.md`)
When working in `tests/` directory:
- Testing procedures and writing new tests
- Template testing workflow patterns
- CLI integration testing approaches
- Debugging test failures

### 📋 Templates (`aegis/templates/CLAUDE.md`) 
When working in `aegis/templates/` directory:
- Template development patterns and Cookiecutter usage
- Jinja2 template syntax and best practices
- Component conditional logic
- Post-generation hook patterns

### 📖 Documentation (`docs/CLAUDE.md`)
When working in `docs/` directory:
- Documentation standards and component documentation patterns
- MkDocs configuration and Mermaid diagram patterns
- Writing component guides and user documentation
- Documentation maintenance workflows

### ⚙️ CLI Core (`aegis/core/CLAUDE.md`)
When working in `aegis/core/` directory:
- CLI development patterns and command structure
- Component system architecture and dependency resolution
- Template generation logic and validation patterns
- Error handling and user experience design

### 👷 Worker Architecture (`aegis/templates/.../worker/CLAUDE.md`)
When working with worker components:
- arq worker patterns and queue management
- Task creation and registration patterns
- Native arq CLI usage and debugging
- Docker worker debugging commands

**Context Loading**: Claude loads ALL applicable CLAUDE.md files when working in a folder, providing context-specific guidance without duplication.