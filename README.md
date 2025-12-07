<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/aegis-manifesto-dark.png">
  <img src="docs/images/aegis-manifesto.png" alt="Aegis Stack" width="400">
</picture>

[![CI](https://github.com/lbedner/aegis-stack/workflows/CI/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/ci.yml)
[![Documentation](https://github.com/lbedner/aegis-stack/workflows/Deploy%20Documentation/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/docs.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Commits per Month](https://img.shields.io/github/commit-activity/m/lbedner/aegis-stack)](https://github.com/lbedner/aegis-stack/commits)
[![Total Commits](https://img.shields.io/github/commit-activity/t/lbedner/aegis-stack)](https://github.com/lbedner/aegis-stack/commits)
[![Monthly Downloads](https://img.shields.io/pypi/dm/aegis-stack)](https://pypi.org/project/aegis-stack/)
[![Total Downloads](https://static.pepy.tech/badge/aegis-stack)](https://pepy.tech/project/aegis-stack)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)

You need to ship reliable software, but management only gave you 2 weeks.

No time for health checks, proper testing, or clean architecture. Just enough time for duct tape and hope.

**What if you could go from idea to working prototype in the time it takes to grab coffee?**

![Aegis Stack Quick Start Demo](docs/images/aegis-demo.gif)

Aegis Stack is a CLI that scaffolds modular Python applications — start with an API, add Auth, Scheduler, Workers, or AI services when you need them.

## Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** - Required for the standard development workflow (`make serve`). Generated projects use Docker for consistent environments and service dependencies (Redis for workers, health monitoring, etc.).

## Quick Start

```bash
# Run instantly without installation
uvx aegis-stack init my-api

# Create with user authentication
uvx aegis-stack init user-app --services auth

# Create with background processing
uvx aegis-stack init task-processor --components scheduler,worker

# Start building
cd my-api && uv sync && cp .env.example .env && make serve
```

**Installation alternatives:** See the [Installation Guide](https://lbedner.github.io/aegis-stack/installation/) for `uv tool install`, `pip install`, and development setup.

## Your Stack Grows With You

**Your choices aren't permanent.** Start with what you need today, add components when requirements change, remove what you outgrow.

```bash
# Monday: Ship MVP
aegis init my-api

# Week 3: Add scheduled reports
aegis add scheduler --project-path ./my-api

# Month 2: Need async workers
aegis add worker --project-path ./my-api

# Month 6: Scheduler not needed
aegis remove scheduler --project-path ./my-api

# Stay current with template improvements
aegis update
```

| Starter | Add Later? | Remove Later? | Git Conflicts? |
|-----------|------------|---------------|----------------|
| **Others** | ❌ Locked at init | ❌ Manual deletion | ⚠️ High risk |
| **Aegis Stack** | ✅ One command | ✅ One command | ✅ Auto-handled |

![Component Evolution Demo](docs/images/aegis-evolution-demo.gif)

Most starters lock you in at `init`. Aegis Stack doesn't. See **[Evolving Your Stack](https://lbedner.github.io/aegis-stack/evolving-your-stack/)** for the complete guide.

## See It In Action

### Overseer - Built-In Health Monitoring

![Overseer](docs/images/overseer-demo.gif)

**[Overseer](https://lbedner.github.io/aegis-stack/overseer/)** is the read-only health monitoring dashboard built into every Aegis Stack project. It provides real-time visibility into all your components (Backend, Database, Worker, Scheduler) and services (Auth, AI, Comms) through a web UI and CLI commands.

No Datadog. No New Relic. No vendor lock-in. Just centralized monitoring you own from day one.

### CLI Health Monitoring

![CLI Health Check](docs/images/cli_health_check.png)

Rich terminal output showing detailed component status, health metrics, and system diagnostics.

## Available Components & Services

**Components** (infrastructure)

- **Core** - API + Frontend (always included)
- **Database** - ORM with health monitoring
- **Scheduler** - Background tasks, cron jobs
- **Worker** - Async task queues

**Services** (business logic)

- **Auth** - User authentication & JWT
- **AI** - Multi-provider AI chat
- **Comms** - Email, SMS, voice calls

[Components Docs →](https://lbedner.github.io/aegis-stack/components/) | [Services Docs →](https://lbedner.github.io/aegis-stack/services/)

## Learn More

- **[CLI Reference](https://lbedner.github.io/aegis-stack/cli-reference/)** - Complete command reference
- **[About](https://lbedner.github.io/aegis-stack/about/)** - The philosophy and vision behind Aegis Stack
- **[Evolving Your Stack](https://lbedner.github.io/aegis-stack/evolving-your-stack/)** - Add/remove components as needs change
- **[Technology Stack](https://lbedner.github.io/aegis-stack/technology/)** - Battle-tested technology choices

## For The Veterans

![Ron Swanson](docs/images/ron-swanson.gif)

No reinventing the wheel. Just the tools you already know, pre-configured and ready to compose.

Aegis Stack respects your expertise. We maintain existing standards - FastAPI for APIs, SQLModel for databases, arq for workers. No custom abstractions or proprietary patterns to learn. Pick your components, get a production-ready foundation, and build your way.

The tool gets out of your way so you can get started.