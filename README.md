# Aegis Stack 🛡️

**Build production-ready Python applications with your chosen components.**

[![CI](https://github.com/lbedner/aegis-stack/workflows/CI/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/ci.yml)
[![Documentation](https://github.com/lbedner/aegis-stack/workflows/Deploy%20Documentation/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/docs.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Aegis Stack is a CLI-driven framework for creating custom Python applications. Select exactly the components you need - no bloat, no unused dependencies.

## Quick Start

```bash
# Install
pip install aegis-stack

# Create a simple API
aegis init my-api

# Create with background processing  
aegis init task-processor --components scheduler,worker

# Start building
cd my-project && uv sync && source .venv/bin/activate && make run-local
```

## Available Components

| Component | Purpose | Status |
|-----------|---------|--------|
| **Core** (FastAPI + Flet) | Web API + Frontend | ✅ **Always Included** |
| **Database** | SQLite + SQLModel ORM | ✅ **Available** |
| **Scheduler** | Background tasks, cron jobs | ✅ **Available** |
| **Worker** | Async task queues (arq + Redis) | 🧪 **Experimental** |
| **Cache** | Redis caching and sessions | 🚧 **Coming Soon** |

## See It In Action

### System Health Dashboard

![System Health Dashboard](docs/images/dashboard-light.png#only-light)
![System Health Dashboard](docs/images/dashboard-dark.png#only-dark)

Real-time monitoring with component status, health percentages, and cross-platform deployment (web, desktop, mobile).

### CLI Health Monitoring

![CLI Health Check](docs/images/cli_health_check.png)

Rich terminal output showing detailed component status, health metrics, and system diagnostics.

## Learn More

- **[📖 CLI Reference](docs/cli-reference.md)** - Complete command reference
- **[🏗️ Components](docs/components/index.md)** - Deep dive into available components  
- **[🧠 Philosophy](docs/philosophy.md)** - Architecture and design principles

## For The Veterans

![Ron Swanson](docs/images/ron-swanson.gif)

No magic. No reinventing the wheel. Just the tools you already know, pre-configured and ready to compose.

Aegis Stack respects your expertise. We maintain existing standards - FastAPI for APIs, SQLModel for databases, arq for workers. No custom abstractions or proprietary patterns to learn. Pick your components, get a production-ready foundation, and build your way.

The framework gets out of your way so you can get started.