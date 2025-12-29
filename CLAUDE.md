# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

**Aegis Stack is a CLI tool for generating containerized Python applications.** It is NOT a runnable application itself.

The architecture follows this pattern:
- **CLI Tool** (`aegis-stack`): Installable via `pip install aegis-stack`
- **Generated Projects**: Full-stack containerized applications created by the CLI
- **Templates**: Cookiecutter templates that define generated project structure

## Release Status: v0.1.0 (LIVE on PyPI!)

**First Official Release** - August 2024
- ✅ **CLI Tool**: Published to PyPI as `aegis-stack`
- ✅ **Database Component**: SQLite + SQLModel ORM with health monitoring
- ✅ **Foundation Stack**: FastAPI backend + Flet frontend + Docker containerization
- ✅ **Worker Component**: arq + Redis for background job processing
- ✅ **Scheduler Component**: APScheduler for scheduled tasks
- ✅ **Documentation**: Progressive documentation philosophy - grows with real implementations

**Install**: `pip install aegis-stack`
**PyPI**: https://pypi.org/project/aegis-stack/
**GitHub Release**: https://github.com/lbedner/aegis-stack/releases/tag/v0.1.0

## Development Commands

This project uses `uv` for dependency management and a `Makefile` for CLI development tasks.

### CLI Development Commands
- `make test` - Run the CLI test suite with pytest
- `make lint` - Run linting with ruff  
- `make typecheck` - Run type checking with ty
- `make check` - Run all checks (lint + typecheck + test) - **run this before committing**
- `make install` or `uv sync --all-extras` - Install/sync dependencies
- `make cli-test` - Test CLI commands locally
- `make docs-serve` - Serve tool documentation locally on port 8001

### Template Development & Testing
- `make test-template-quick` - Quick template test without validation
- `make test-template` - Full template test with validation
- `make test-template-with-components` - Test template with scheduler component
- `make test-template-auth` - **Test auth service template with comprehensive validation**
- `make test-template-worker` - Test worker component template
- `make test-template-database` - Test database component template
- `make test-template-full` - Test template with all components
- `make clean-test-projects` - Remove generated test projects

**Template testing is critical** - always run `make test-template` after modifying templates to ensure generated projects work correctly.

**For auth service development**: Use `make test-template-auth` to generate auth service project and run full validation including:
- ✅ Auth service includes Alembic migration infrastructure
- ✅ Database component auto-inclusion
- ✅ Migration files generate correctly
- ✅ All 52 auth service tests pass
- ✅ CLI script installation and functionality
- ✅ Linting, type checking, and quality checks

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

## Creator Context & Philosophy

### The Architect: Leonard Bedner

**Leonard Bedner** (aka Challseus) is the creator and architect of Aegis Stack. A career software engineer since 2004, systems builder, and game developer who brings decades of experience building production systems and award-winning creative projects.

#### Background: Rose of Eternity
Before Aegis Stack, Leonard created the **Rose of Eternity** series - critically acclaimed RPG mods that pioneered innovative gameplay systems:
- **Rose of Eternity - The Coming** (2005) - Ranked #15 all-time NWN modules
- **Rose of Eternity - Cry The Beloved** (2006) - **2nd highest rated NWN module of all time**
- **Rose of Eternity - Family & Country** (Dragon Age) - Continuing the saga 20 years later

These games featured groundbreaking composable systems:
- **Bonds of Battle**: Characters growing stronger fighting together
- **Unison Abilities**: Combining party member strengths for emergent gameplay
- **Last Resorts**: Desperation mechanics at low health
- **Custom progression systems** that rewarded player experimentation

#### The Connection: Game Design → Platform Architecture

The same philosophy that made Rose of Eternity revolutionary now drives Aegis Stack:
- **Composable systems that create emergent behavior** (like Breath of the Wild's chemistry engine)
- **Small, focused components** that do one thing excellently
- **Unexpected interactions** between components creating new possibilities
- **Progressive enhancement** - systems that grow stronger together
- **Player/Developer agency** - providing tools, not prescribing paths

### What Aegis Stack Really Is

**Aegis Stack is a modular, evolving, agent-ready boilerplate platform** - not just a CLI tool, but an ecosystem of composable primitives that grows with you.

#### Core Philosophy:
- **"Build foundations, not toys"** - Every component exists because it solved real production problems
- **"Build once, scale forever"** - Upgradable, testable, observable foundations that never get in the way
- **"Everything can affect everything"** - Components that compose in unexpected but delightful ways
- **"It does damn well enough"** - Not trying to be everything, but what it does, it does RIGHT

#### The Emergent Behavior Pattern:
Just like Rose of Eternity's combat systems created unexpected synergies, Aegis components combine in powerful ways:
- **AI Service alone**: Basic chatbot
- **AI + Auth**: User-specific conversations, protected endpoints
- **AI + Database**: Persistent history, analytics
- **AI + Redis**: Fast conversation caching
- **AI + Scheduler**: Scheduled summaries, model warm-ups
- **AI + Worker**: Background AI processing, batch operations

Each combination creates possibilities not explicitly designed - the hallmark of great platform architecture.

### Development Approach

Leonard's approach prioritizes:
1. **Foundation-first thinking** - Not features, but capabilities others can build on
2. **Battle-tested patterns** - Everything exists because it solved a real problem
3. **Agent-ready architecture** - Predictable, testable, extendable
4. **No abstraction for abstraction's sake** - Direct access to tools, not wrappers
5. **Test-first development** - Comprehensive testing as a core requirement

### Why This Matters

When working with Aegis Stack code:
- Remember you're working with **architectural DNA**, not just code
- Every pattern repeats because it's been proven in production
- Components are designed to discover unexpected interactions
- The goal is empowering developers, not constraining them
- This is a **meta-resume** - craft, discipline, and mind made visible in code

**Aegis Stack is Leonard's engineering worldview made shareable** - two decades of building systems distilled into a platform that lets others skip the painful parts and get straight to creating.

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

**Database Queries (Avoid N+1):**
- **NEVER** query inside a loop - this causes N+1 query problems
- Batch-fetch related data using `WHERE id IN (...)` or JOINs
- Use `selectinload()` or `joinedload()` for eager loading relationships
- Example of what NOT to do:
  ```python
  # BAD: N+1 queries (1 query + N queries in loop)
  for model in models:
      price = session.exec(select(Price).where(Price.model_id == model.id)).first()

  # GOOD: Batch fetch (2 queries total)
  model_ids = [m.id for m in models]
  prices = session.exec(select(Price).where(Price.model_id.in_(model_ids))).all()
  price_map = {p.model_id: p for p in prices}
  ```

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