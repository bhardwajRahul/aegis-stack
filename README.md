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

Aegis Stack is a system for creating and evolving modular Python applications over time, built on tools you already know.

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

## Overseer - Built-In System Visibility

![Overseer](docs/images/overseer-demo.gif)

**[Overseer](https://lbedner.github.io/aegis-stack/overseer/)** is the built-in system dashboard that ships with every Aegis Stack project.

It provides a live view of what your application is doing at runtime - across core components (Backend, Database, Workers, Scheduler) and services (Auth, AI, Comms) - through a web UI.

Overseer goes beyond simple health checks. You can inspect worker queues, scheduled jobs, database state, and AI usage, all in one place, without wiring up external tools.

No Datadog. No New Relic. No vendor lock-in.

Just a clear view of your system, included from day one.

## CLI - First-Class System Interface

![CLI Demo](docs/images/cli-demo.gif)

The Aegis CLI is a first-class interface to your running system.

It goes beyond simple health checks, exposing rich, component-specific commands for inspecting and understanding your application from the terminal.

Query worker queues, scheduler activity, database state, AI usage, and service configuration, all without leaving the CLI.

The same system intelligence that powers Overseer and Illiana is available here, optimized for terminal workflows.

## Illiana - Optional System Operator

![Illiana Demo](docs/images/illiana-demo.gif)

When the AI service is enabled, Aegis exposes an additional interface: **Illiana**.

Illiana is a conversational interface that answers questions about your running system using live telemetry and optional RAG over your codebase.

She is not required to use Aegis Stack, and nothing in the system depends on her being present. When enabled, she becomes another way, alongside the CLI and Overseer, to understand what your application is doing and why.

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

## Available Components & Services

**Components** (infrastructure)

- **Core** → FastAPI + Pydantic V2 + Uvicorn
- **Database** → Postgres / SQLite
- **Cache/Queue** → Redis
- **Scheduler** → APScheduler
- **Worker** → Arq / Taskiq

**Services** (business logic)

- **Auth** → JWT authentication
- **AI** → PydanticAI / LangChain
- **Comms** → Resend + Twilio

[Components Docs →](https://lbedner.github.io/aegis-stack/components/) | [Services Docs →](https://lbedner.github.io/aegis-stack/services/)

## Learn More

- **[CLI Reference](https://lbedner.github.io/aegis-stack/cli-reference/)** - Complete command reference
- **[About](https://lbedner.github.io/aegis-stack/about/)** - The philosophy and vision behind Aegis Stack
- **[Evolving Your Stack](https://lbedner.github.io/aegis-stack/evolving-your-stack/)** - Add/remove components as needs change
- **[Technology Stack](https://lbedner.github.io/aegis-stack/technology/)** - Battle-tested technology choices

## For The Veterans

![Ron Swanson](docs/images/ron-swanson.gif)

No reinventing the wheel. Just the tools you already know, pre-configured and ready to compose.

Aegis Stack respects your expertise. No custom abstractions or proprietary patterns to learn. Pick your components, get a production-ready foundation, and build your way.

Aegis gets out of your way so you can get started.