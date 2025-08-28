  # Changelog

  All notable changes to this project will be documented in this file.

  The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
  and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

  [0.1.0]: https://github.com/lbedner/aegis-stack/releases/tag/v0.1.0