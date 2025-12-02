  # Changelog

  All notable changes to this project will be documented in this file.

  The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
  and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

  ## [0.3.0] - 2025-12-01

### Major Features

#### Dashboard V2 - Complete UI Overhaul
- Light and dark theme support with system preference detection
- Component modal system - detailed info panels for each component:
  - Scheduler modal: Job stats, task history, next run times, cron expressions
  - Worker modal: Queue depth, job history, worker health, Redis connection
  - Redis modal: Memory usage, connection stats, key counts
  - Database modal: Table stats, connection pool info, query metrics
  - Backend modal: Route inspection, middleware detection, request stats
  - AI modal: Provider status, model info, conversation history
  - Auth modal: User count, session stats, JWT configuration
  - Frontend modal: Component tree, render stats, routing info
- Modern card-based architecture with improved visual hierarchy
- Enhanced health check visualization

#### New CLI Features
- `aegis update` rollback support - automatically restore on failed updates
- `--template-path` flag - use local template directories for development
- `--verbose` flag - control output verbosity across all commands
- Improved error messages with actionable suggestions for generation failures

#### Comms Service (New Service Layer)
- Communication service foundation for inter-component messaging
- Event-driven architecture support
- Service discovery patterns

### Added

- Copier integration testing for template validation
- CI/CD parallelization for faster builds
- Commit badges in generated project READMEs
- Scheduler environment variable configuration
- Enhanced Overseer documentation

### Fixed

- `aegis update` now correctly targets HEAD instead of latest tag
- Template path handling with `git+file://` URL format for Copier
- Dashboard rendering edge cases with component state

---

## [0.2.1] - 2025-11-10

### Fixed

- Minor bug fixes and stability improvements
- Added verbosity flag foundation

---

## [0.2.0] - 2025-11-05

### Major Features

  #### Dynamic Component Management
  - **NEW**: `aegis add` command - Add components to existing projects post-generation
  - **NEW**: `aegis remove` command - Remove components from existing projects
  - **NEW**: `aegis update` command - Update projects with latest template changes
  - **NEW**: Copier template engine support with version tracking
  - Projects can now evolve after creation (Copier-based projects only)
  - Intelligent dependency resolution (e.g., worker auto-adds Redis, auth auto-adds database)
  - File-level component management without full project regeneration
  - Automatic dependency installation and code formatting after changes

  #### Services Architecture (Business Logic Layer)
  - **NEW**: Authentication Service (`--services auth`)
    - JWT-based authentication with access and refresh tokens
    - User registration, login, and profile management
    - Password hashing with bcrypt
    - Protected API routes with FastAPI dependency injection
    - Database migrations via Alembic
    - User management CLI commands (`create-user`, `list-users`, `delete-user`, etc.)
    - Comprehensive test suite with 52+ authentication tests
    - Automatically includes database component

  - **NEW**: AI Service (`--services ai`)
    - PydanticAI integration for type-safe AI interactions
    - Multi-provider support (OpenAI, Anthropic, Gemini, Groq)
    - Streaming chat responses with markdown rendering
    - Conversation memory and persistence to database
    - Interactive CLI chat interface with rich formatting
    - Health monitoring for AI provider connectivity
    - Environment variable configuration
    - API endpoints for chat operations

  #### Enhanced Scheduler Component
  - **NEW**: SQLite-backed persistence option (`--scheduler-backend sqlite`)
  - Automatic database backup jobs when scheduler + database combined
  - Task monitoring API endpoints
  - Interactive CLI for viewing and managing scheduled tasks
  - Enhanced health checks with task execution tracking
  - Job statistics and history

### Added

  #### CLI Commands
  - `aegis add` - Add components to existing projects
  - `aegis remove` - Remove components from projects
  - `aegis update` - Update projects with latest templates
  - `aegis services` - List available services
  - `aegis components` - Show detailed component information
  - `aegis version` - Display CLI version
  - Template engine selection via `--engine` flag (copier or cookiecutter)
  - Interactive service selection during project creation
  - Component backend selection (e.g., `--scheduler-backend sqlite`)

  #### Developer Experience
  - **uvx support** - Run without installation (`uvx aegis-stack init my-project`)
  - Enhanced dashboard with component and service health cards:
    - Auth service card (user count, health status, database connection)
    - AI service card (provider status, model info, conversation stats)
    - Scheduler card (job stats, task history, next run times)
    - Worker card (queue stats, job history, worker health)
    - FastAPI card (route inspection, middleware detection)
    - Database card (table stats, connection pool info)
    - Redis card (memory usage, connection statistics)
  - Load testing CLI with visual progress indicators
  - FastAPI middleware and route inspection utilities
  - Rich terminal formatting for AI chat (markdown, code blocks, tables)
  - Comprehensive CLI tools for component management

  #### Testing & Quality
  - Migrated from mypy to `ty` for faster type checking
  - Extensive test coverage for auth service (52+ tests)
  - Extensive test coverage for AI service
  - Template parity tests (Cookiecutter vs Copier output validation)
  - Component addition/removal integration tests
  - Auth integration tests (registration, login, JWT flows, protected routes)
  - AI conversation persistence tests
  - Middleware and route inspection tests
  - Extended test matrix for component combinations
  - Clean validation workflow for template testing

  #### Documentation
  - Complete auth service documentation (API reference, CLI commands, integration guide, examples)
  - Complete AI service documentation (provider setup, API reference, CLI commands, integration)
  - Services architecture guide and dashboard integration docs
  - "Evolving Your Stack" guide - post-generation component management philosophy
  - Scheduler persistence and CLI documentation
  - Enhanced installation guide (uvx, uv tool, pip methods)
  - Integration patterns documentation
  - Component-specific CLAUDE.md files for AI development context
  - Release process documentation with PyPI/TestPyPI workflow

  #### Infrastructure
  - GitHub Actions workflow for automated PyPI releases
  - TestPyPI pre-flight testing workflow
  - PyPI Trusted Publishing (OIDC, no API tokens)
  - Template versioning and compatibility tracking
  - Copier template infrastructure with `.copier-answers.yml`
  - Post-generation task system refactored
  - Component file management utilities
  - Service dependency resolver
  - Manual updater for Cookiecutter-based projects

### Changed

  - **Default template engine** is now Copier (Cookiecutter still fully supported via `--engine cookiecutter`)
  - Type checker migrated from mypy to `ty` for improved performance
  - Enhanced dashboard UI with modern card-based architecture
  - Improved component dependency resolution logic
  - Better error messages with actionable suggestions
  - Scheduler component refactored with service layer separation
  - Worker health check registration improved
  - Database health checks enhanced with connection pool monitoring
  - Restructured CLI command organization into separate modules
  - Dashboard rendering optimizations

### Fixed

  - Dashboard rendering bugs with component state management
  - Worker type annotations and kwargs handling
  - arq worker info retrieval issues
  - Scheduler component integration edge cases
  - Database card rendering and refactoring issues
  - Redis component card state updates
  - FastAPI middleware detection for edge cases
  - Template generation with various component combinations
  - Health check caching race conditions

### Security

  - JWT-based authentication with secure token handling
  - Password hashing with bcrypt (cost factor 12)
  - Protected API routes with dependency injection patterns
  - Secure user model implementation
  - API key handling for AI providers
  - Environment variable-based secrets management

### Performance

  - Faster type checking with `ty` replacing mypy
  - Optimized component dependency resolution
  - Improved dashboard rendering performance
  - Enhanced health check caching strategies
  - Reduced template generation time

### Statistics

  - 62 pull requests merged since v0.1.0
  - 456 files changed (72,387 insertions, 4,590 deletions)
  - 8 new CLI commands
  - 2 new services (auth, AI)
  - 13+ new documentation files
  - 100+ new test files
  - 10 weeks of development (Aug 28 - Nov 5, 2025)

### Highlights for Users

  1. **Your stack can now evolve** - Add/remove components after project creation
  2. **Authentication ready** - Production JWT auth with one command (`--services auth`)
  3. **AI-ready** - Multi-provider AI integration built-in (`--services ai`)
  4. **No installation needed** - Run with `uvx aegis-stack init my-project`
  5. **Scheduler persistence** - SQLite-backed job storage for reliability
  6. **Enhanced DX** - Rich CLI tools, better dashboard, comprehensive health monitoring

### Notes

  - Copier is now the default template engine, enabling `aegis add/remove/update` commands
  - Both Copier and Cookiecutter templates are fully supported
  - Auth service automatically includes Alembic for database migrations
  - AI service supports OpenAI, Anthropic, Gemini, and Groq providers
  - Scheduler persistence requires database component
  - Template version compatibility tracked in `.copier-answers.yml` (Copier projects)
  - Worker component still requires explicit Redis component specification

  ## [0.1.0] - 2025-08-27

  ### Added
  - Initial release of Aegis Stack CLI tool
  - Database component with SQLite/SQLModel ORM integration
  - FastAPI backend with health monitoring system
  - Flet frontend for web and desktop applications
  - Worker component with arq/Redis for background tasks
  - Scheduler component with APScheduler
  - Docker containerization support
  - Comprehensive testing infrastructure with pytest
  - Type checking with mypy and pydantic plugin
  - Auto-formatting with ruff
  - Project generation via `aegis init` command
  - Component dependency resolution system
  - Database health checks with detailed metrics
  - Transaction rollback testing fixtures
  - Template validation system

  ### Fixed
  - Database test isolation issues
  - Type checking for Pydantic models with mypy plugin
  - Template linting issues in generated projects

  ### Components
  - Backend (FastAPI) - Always included
  - Frontend (Flet) - Always included
  - Database (SQLite/SQLModel) - Optional
  - Worker (arq/Redis) - Optional
  - Scheduler (APScheduler) - Optional

[0.3.0]: https://github.com/lbedner/aegis-stack/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/lbedner/aegis-stack/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/lbedner/aegis-stack/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/lbedner/aegis-stack/releases/tag/v0.1.0