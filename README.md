<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/aegis-manifesto-dark.png">
  <img src="docs/images/aegis-manifesto.png" alt="Aegis Stack" width="400">
</picture>

**Build production-ready Python applications with your chosen components and services.**

[![CI](https://github.com/lbedner/aegis-stack/workflows/CI/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/ci.yml)
[![Documentation](https://github.com/lbedner/aegis-stack/workflows/Deploy%20Documentation/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/docs.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Aegis Stack is a CLI-driven framework for creating custom Python applications. Select exactly the components you need - no bloat, no unused dependencies.

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

## Installation

**No installation needed** - just run it:

```bash
uvx aegis-stack init my-project
```

That's it. [`uvx`](https://docs.astral.sh/uv/) downloads, installs, and runs Aegis Stack in one command.

---

**Alternative methods:** [Installation Guide](docs/installation.md) covers `uv tool install` and `pip install` for specific workflows.

## 🌱 Your Stack Grows With You

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
```

| Framework | Add Later? | Remove Later? | Git Conflicts? |
|-----------|------------|---------------|----------------|
| **Others** | ❌ Locked at init | ❌ Manual deletion | ⚠️ High risk |
| **Aegis Stack** | ✅ One command | ✅ One command | ✅ Auto-handled |

Most frameworks lock you in at `init`. Aegis Stack doesn't. See **[Evolving Your Stack](docs/evolving-your-stack.md)** for the complete guide.

## Available Components & Services

### Infrastructure Components
| Component | Purpose | Status |
|-----------|---------|--------|
| **Core** (FastAPI + Flet) | Web API + Frontend | ✅ **Always Included** |
| **Database** | SQLite + SQLModel ORM | ✅ **Available** |
| **Scheduler** | Background tasks, cron jobs | ✅ **Available** |
| **Worker** | Async task queues (arq + Redis) | 🧪 **Experimental** |
| **Cache** | Redis caching and sessions | 🚧 **Coming Soon** |

### Business Services
| Service | Purpose | Status |
|---------|---------|--------|
| **Auth** | User authentication & JWT | ✅ **Available** |
| **AI** | Multi-provider AI chat | 🧪 **Experimental** |

## See It In Action

### System Health Dashboard

![System Health Dashboard](docs/images/dashboard-dark.png)

Real-time monitoring with component status, health percentages, and cross-platform deployment (web, desktop, mobile).

### CLI Health Monitoring

![CLI Health Check](docs/images/cli_health_check.png)

Rich terminal output showing detailed component status, health metrics, and system diagnostics.

## Learn More

- **[📖 CLI Reference](docs/cli-reference.md)** - Complete command reference
- **[🏗️ Components](docs/components/index.md)** - Deep dive into available components
- **[🔧 Services](docs/services/index.md)** - Business services (auth, AI)
- **[🧠 Philosophy](docs/philosophy.md)** - Architecture and design principles

## For The Veterans

![Ron Swanson](docs/images/ron-swanson.gif)

No magic. No reinventing the wheel. Just the tools you already know, pre-configured and ready to compose.

Aegis Stack respects your expertise. We maintain existing standards - FastAPI for APIs, SQLModel for databases, arq for workers. No custom abstractions or proprietary patterns to learn. Pick your components, get a production-ready foundation, and build your way.

The framework gets out of your way so you can get started.