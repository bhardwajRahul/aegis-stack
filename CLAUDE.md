# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## ⚠️ CRITICAL: No Git Operations

**DO NOT perform git operations unless explicitly requested.** This includes:
- No `git add`, `git commit`, or `git push` commands
- No `git status`, `git diff`, or `git log` for preparation purposes
- No creating pull requests
- No staging files

**Wait for explicit user approval before ANY git operations.**

---

## Project Architecture

**Aegis Stack is a modular platform for building and evolving production-ready Python applications.**

What you get:
- **CLI Tool** (`aegis`): Create, modify, and update projects
- **Component System**: Add/remove building blocks (database, worker, scheduler, redis)
- **Service System**: Add/remove business capabilities (auth, AI, payment, analytics)
- **Living Projects**: Generated projects can pull updates, bug fixes, and new features via `aegis update`

Each generated project includes:
- Project-specific CLI
- FastAPI backend
- Full test suite
- Docker containerization

## Installation

**Current Version**: v0.5.1-rc2

```bash
pip install aegis-stack
```

**Links**:
- PyPI: https://pypi.org/project/aegis-stack/
- GitHub: https://github.com/lbedner/aegis-stack

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
- `make test-template-auth` - Test auth service template
- `make test-template-worker` - Test worker component template
- `make test-template-database` - Test database component template
- `make test-template-full` - Test template with all components
- `make clean-test-projects` - Remove generated test projects

**Template testing is critical** - always run `make test-template` after modifying templates to ensure generated projects work correctly.

## Code Navigation (LSP-First)

Use the Language Server (Pyright) for code navigation instead of grep/glob:

**Prefer LSP:**
- `LSP(findReferences)` - Find all usages of a symbol
- `LSP(goToDefinition)` - Jump to where something is defined
- `LSP(hover)` - Get type info and docstrings
- `LSP(documentSymbol)` - List all symbols in a file

**Use grep/glob when:**
- Searching for text patterns (not symbol names)
- Searching in non-Python files (yaml, md, json, jinja)
- LSP server not available

**Why LSP is better:**
- Semantic understanding - knows actual references, not text matches
- Type-aware - hover shows full type signatures

## Test Project Location

**When prototyping, check `my-app/` under the aegis-stack root first.**

The user often has a test project at `/Users/leonardbedner/Workspace/house_bedner/aegis-stack/my-app/` for iterating on changes before backporting to templates. When making fixes:
1. Look in `my-app/` first for the generated project code
2. Test changes there
3. Backport working changes to templates in `aegis/templates/`

## Template Development Workflow

### Two Approaches

**1. Template-First** (for known changes)
Edit templates directly, then generate to verify:
1. Edit template files in `aegis/templates/copier-aegis-project/{{ project_slug }}/`
2. Generate: `make test-template` or `aegis init test-project`
3. Verify it works
4. Clean up: `make clean-test-projects`

**2. Prototype-First** (for exploratory work)
Get it working in a real project, then backport:
1. Generate a test project: `aegis init test-project`
2. Make changes in the generated project until it works
3. **Backport** working changes to template files
4. Regenerate fresh to verify templates are correct
5. Clean up test project

### Key Principle
Template files are the source of truth. Any changes you want to persist across future `aegis init` commands **must** be backported to templates.

**Remember**: Generated projects are for validation/prototyping. Templates are what ships.

## Design Principles

### Core Philosophy
- **Composable systems** - Components combine in powerful, sometimes unexpected ways
- **Small, focused components** - Each does one thing excellently
- **No abstraction for abstraction's sake** - Direct access to tools, not wrappers
- **Test-first development** - Comprehensive testing as a core requirement

### Component Combinations
Components create emergent capabilities when combined:
- **AI + Auth**: User-specific conversations, protected endpoints
- **AI + Database**: Persistent history, analytics
- **AI + Worker**: Background AI processing, batch operations
- **Scheduler + Database**: Persistent job scheduling

### Development Approach
1. **Foundation-first** - Build capabilities others can build on
2. **Battle-tested patterns** - Everything exists because it solved a real problem
3. **Agent-ready architecture** - Predictable, testable, extendable

## Coding Standards

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

## Components vs Services (in Generated Projects)

When editing templates, understand where code belongs:

**Components** (`app/components/`): Infrastructure - scheduler, worker, database, backend, frontend
**Services** (`app/services/`): Business logic - auth, AI, payment, etc.

Components define WHEN/WHERE (routes, jobs). Services define WHAT (logic).
