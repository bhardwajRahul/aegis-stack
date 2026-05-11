<img src="docs/images/aegis_stack_wordmark.svg" alt="Aegis Stack" width="500">

[![CI](https://github.com/lbedner/aegis-stack/workflows/CI/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/ci.yml)
[![Documentation](https://github.com/lbedner/aegis-stack/workflows/Deploy%20Documentation/badge.svg)](https://github.com/lbedner/aegis-stack/actions/workflows/docs.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)
<br>
[![Monthly Downloads](https://img.shields.io/pypi/dm/aegis-stack)](https://pypi.org/project/aegis-stack/)
[![Total Downloads](https://static.pepy.tech/badge/aegis-stack)](https://pepy.tech/project/aegis-stack)
<br>
[![Commits per Month](https://img.shields.io/github/commit-activity/m/lbedner/aegis-stack)](https://github.com/lbedner/aegis-stack/commits)
[![Total Commits](https://img.shields.io/github/commit-activity/t/lbedner/aegis-stack)](https://github.com/lbedner/aegis-stack/commits)
[![Last Commit](https://img.shields.io/github/last-commit/lbedner/aegis-stack)](https://github.com/lbedner/aegis-stack/commits)

You need to ship reliable software, but management only gave you 2 weeks.

No time for health checks, proper testing, or clean architecture. Just enough time for duct tape and hope.

**What if you could go from idea to working prototype in the time it takes to grab coffee?**

![Aegis Stack Quick Start Demo](docs/images/aegis-demo.gif)

**Ship FastAPI apps that grow with you.**

Aegis Stack scaffolds complete FastAPI applications with auth, payments, workers, AI, and a built-in control plane. Add what you need, remove what you don't, update when the framework improves.

## Quick Start

```bash
uvx aegis-stack init my-api && cd my-api && make serve
```

<details>
<summary><strong>More examples</strong></summary>

```bash
# Add user authentication out of the box
uvx aegis-stack init user-app --services auth

# Add background processing + scheduling
uvx aegis-stack init task-processor --components scheduler,worker

# Everything wired up at init
uvx aegis-stack init full-app --services auth,payment,comms --components worker,scheduler
```

</details>

> **CLI in 9 languages:** English, German, Spanish, French, Japanese, Korean, Russian, Simplified Chinese, Traditional Chinese. Use `aegis --lang <code>` or set `AEGIS_LANG`.

**Installation alternatives:** See the [Installation Guide](https://lbedner.github.io/aegis-stack/installation/) for `uv tool install`, `pip install`, and development setup.

## Customizing Your Stack

**Components** are infrastructure pieces (database, workers, scheduler, cache). **Services** are business capabilities (auth, AI, payments, comms).

**Don't worry about what you pick today.** Add anything later with a single command, remove what you outgrow, no rework required.

### Components

| Component | What you get | |
|---|---|---|
| **[Backend](https://lbedner.github.io/aegis-stack/components/webserver/)** | FastAPI + lifecycle hooks | ![Always](https://img.shields.io/badge/-always_on-2ea043) |
| **[CLI](https://lbedner.github.io/aegis-stack/cli-reference/)** | Typer, first-class system interface | ![Always](https://img.shields.io/badge/-always_on-2ea043) |
| **[Frontend](https://lbedner.github.io/aegis-stack/components/frontend/)** | Flet, ships with the Overseer system dashboard | ![Always](https://img.shields.io/badge/-always_on-2ea043) |
| **[Cache](https://lbedner.github.io/aegis-stack/components/)** | Redis for caching, sessions, pub/sub | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Database](https://lbedner.github.io/aegis-stack/components/database/)** | Postgres or SQLite + SQLModel ORM | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Inference](https://lbedner.github.io/aegis-stack/components/)** | Local AI models via Ollama | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Ingress](https://lbedner.github.io/aegis-stack/components/ingress/)** | Traefik v3 reverse proxy with TLS | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Observability](https://lbedner.github.io/aegis-stack/components/observability/)** | Pydantic Logfire tracing + metrics + logging | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Scheduler](https://lbedner.github.io/aegis-stack/components/scheduler/)** | APScheduler with persistent jobs | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Worker](https://lbedner.github.io/aegis-stack/components/worker/)** | Pluggable Arq, Taskiq, or Dramatiq | ![Optional](https://img.shields.io/badge/-optional-blue) |

[Components Docs →](https://lbedner.github.io/aegis-stack/components/)

### Services

| Service | What you get | |
|---|---|---|
| **[AI](https://lbedner.github.io/aegis-stack/services/ai/)** | Conversational agents, RAG, model catalog, TTS and STT (PydanticAI / LangChain across 7 providers) | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Auth](https://lbedner.github.io/aegis-stack/services/auth/)** | Persistent sessions with refresh-token rotation, GitHub/Google sign-in, RBAC, multi-tenant Organizations | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Blog](https://lbedner.github.io/aegis-stack/services/blog/)** | Markdown publishing with drafts, tags, and an Overseer editor | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Comms](https://lbedner.github.io/aegis-stack/services/comms/)** | Transactional email (Resend) + SMS / voice (Twilio) | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Insights](https://lbedner.github.io/aegis-stack/services/insights/)** | Adoption metrics across GitHub, PyPI, Plausible, Reddit | ![Optional](https://img.shields.io/badge/-optional-blue) |
| **[Payments](https://lbedner.github.io/aegis-stack/services/payment/)** | Stripe checkout, subscriptions, refunds, disputes | ![Optional](https://img.shields.io/badge/-optional-blue) |

[Services Docs →](https://lbedner.github.io/aegis-stack/services/)

## CI/CD for Your Stack

Every generated project ships with GitHub Actions and developer tooling pre-wired, so the first push to GitHub runs checks automatically, and one command wires up continuous deployment to your server.

<table>
<thead>
<tr><th>Capability</th><th>What you get</th><th width="80">Status</th></tr>
</thead>
<tbody>
<tr><td><b>CI Workflow</b></td><td>Lint, type checking, and tests on every push and PR (parallel jobs, cached)</td><td><img src="https://img.shields.io/badge/-available-2ea043" alt="Available" width="64"></td></tr>
<tr><td><b>Code Scanning</b></td><td>CodeQL static analysis on every PR and on a weekly schedule</td><td><img src="https://img.shields.io/badge/-available-2ea043" alt="Available" width="64"></td></tr>
<tr><td><b>Pre-commit</b></td><td>Ruff, ruff-format, and type-check hooks (opt-in)</td><td><img src="https://img.shields.io/badge/-optional-blue" alt="Optional" width="64"></td></tr>
<tr><td><b>Continuous Deploy</b></td><td>Generates a dedicated SSH deploy key, installs it on your server, pushes secrets to GitHub, and scaffolds a deploy workflow (manual trigger by default)</td><td><img src="https://img.shields.io/badge/-optional-blue" alt="Optional" width="64"></td></tr>
</tbody>
</table>

## Deploying Your Stack

| Capability | What you get | |
|---|---|---|
| **[Deploy CLI](https://lbedner.github.io/aegis-stack/deployment/)** | One-command deploys to any VPS over SSH (rsync + Docker), no PaaS lock-in | ![Available](https://img.shields.io/badge/-available-2ea043) |
| **[Server Setup](https://lbedner.github.io/aegis-stack/deployment/#aegis-deploy-setup)** | `aegis deploy-setup` provisions Ubuntu, Debian, or Fedora boxes (Docker + firewall) | ![Available](https://img.shields.io/badge/-available-2ea043) |
| **[Backups & Rollback](https://lbedner.github.io/aegis-stack/deployment/#backup-and-rollback)** | `pg_dump` before every deploy, retention policy, automatic rollback on failed health checks | ![Available](https://img.shields.io/badge/-available-2ea043) |
| **[TLS / HTTPS](https://lbedner.github.io/aegis-stack/deployment/#tlshttps-with-lets-encrypt)** | Let's Encrypt via the Traefik ingress component, zero config when a domain is set | ![Optional](https://img.shields.io/badge/-optional-blue) |

[Deployment Docs →](https://lbedner.github.io/aegis-stack/deployment/)

Components compose into capabilities you didn't have to build:

```mermaid
graph LR
    Auth[Auth] --> A[User-specific AI conversations]
    AI[AI] --> A
    AI --> B[Persistent history &<br/>token analytics]
    DB[(Database)] --> B
    AI --> C[Background AI pipelines]
    Worker[Worker] --> C
    Scheduler[Scheduler] --> D[Persistent job scheduling]
    DB --> D
```

## Your Stack Grows With You

**Your choices aren't permanent.** Start with what you need today, add when requirements change, remove what you outgrow.

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
| **Others** | Locked at init | Manual deletion | High risk |
| **Aegis Stack** | One command | One command | Auto-handled |

<img src="docs/images/aegis-evolution-demo.gif" alt="Component Evolution Demo" width="480">

Most starters lock you in at `init`. Aegis Stack doesn't. See **[Evolving Your Stack](https://lbedner.github.io/aegis-stack/evolving-your-stack/)** for the complete guide.

## Overseer - Your Application's Control Plane

<img src="docs/images/overseer-demo.gif" alt="Overseer" width="480">

<sub>[Live Demo: sector-7g.dev/dashboard](https://sector-7g.dev/dashboard/)</sub>

**[Overseer](https://lbedner.github.io/aegis-stack/overseer/)** is the embedded control plane that ships with every Aegis Stack project.

- Live health of every component and service in one view
- Worker queues, scheduled jobs, recent runs
- Database schema, tables, and migration state
- AI token usage and conversation history
- Auth sessions and user activity
- No external tooling, no vendor integrations, no setup

## CLI - First-Class System Interface

<img src="docs/images/cli-demo.gif" alt="CLI Demo" width="480">

The Aegis CLI is a first-class interface to your running system. Not just a health check, but a full inspection layer.

- Component-aware commands for every running subsystem
- Inspect worker queues, scheduler runs, database state
- Query AI usage, auth sessions, service configuration
- Same data Overseer sees, terminal-native
- Built into every generated project, no extra installs

## Illiana - Optional System Operator

<img src="docs/images/illiana-demo.gif" alt="Illiana Demo" width="480">

When the AI service is enabled, Aegis exposes an additional interface: **Illiana**, a conversational operator over your running system.

- Ask questions in plain language about live system state
- Backed by live telemetry from Overseer and the CLI
- Optional RAG over your codebase for code-aware answers
- Opt-in: only available when the AI service is on
- Nothing in the stack depends on her being there

## Learn More

- **[Overseer](https://lbedner.github.io/aegis-stack/overseer/)** - Built-in system dashboard
- **[Deployment](https://lbedner.github.io/aegis-stack/deployment/)** - Deploy with backups, rollback, and health checks
- **[CLI Reference](https://lbedner.github.io/aegis-stack/cli-reference/)** - Complete command reference
- **[Evolving Your Stack](https://lbedner.github.io/aegis-stack/evolving-your-stack/)** - Add/remove components as needs change
- **[Technology Stack](https://lbedner.github.io/aegis-stack/technology/)** - Battle-tested technology choices
- **[About](https://lbedner.github.io/aegis-stack/about/)** - The philosophy and vision behind Aegis Stack

## For The Veterans

<img src="docs/images/ron-swanson.gif" alt="Ron Swanson" width="480">

No reinventing the wheel. Just the tools you already know, pre-configured and ready to compose.

Aegis Stack respects your expertise. No custom abstractions or proprietary patterns to learn. Pick your components, get a production-ready foundation, and build your way.

Aegis gets out of your way so you can get started.
