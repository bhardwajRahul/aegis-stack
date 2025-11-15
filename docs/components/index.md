# Components Overview

Components are the **infrastructure building blocks** of your Aegis Stack application. Each component provides a specific capability like API serving, background tasks, or data persistence.

!!! info "Components vs Services"
    **Components** = Infrastructure capabilities (database, workers, scheduling)
    **Services** = Business functionality (auth, payments, AI integrations)

    See **[Services Overview](../services/index.md)** for business-level features.

## Evolving Your Stack

**Your choices aren't permanent.** Start with what you need today, add components as requirements evolve, remove what you don't use anymore.

### Start Lean, Grow As Needed

```bash
# Monday: Ship MVP with just FastAPI + Flet
aegis init my-api

# Week 3: Product needs scheduled reports
aegis add scheduler --project-path ./my-api

# Month 2: Scale demands async workers
aegis add worker --project-path ./my-api

# Month 6: Scheduler not needed anymore
aegis remove scheduler --project-path ./my-api
```

Most frameworks lock you in at `init`. Aegis Stack doesn't. See the complete guide: **[Evolving Your Stack](../evolving-your-stack.md)**

## Component Architecture

```mermaid
graph TB
    subgraph "Always Included"
        API[FastAPI Backend<br/>REST API + Health]
        Frontend[Flet Frontend<br/>Cross-platform UI]
        CLI[CLI Commands<br/>Management Interface]
    end
    
    subgraph "Optional Infrastructure"
        Scheduler[Scheduler<br/>APScheduler Jobs]
        Database[Database<br/>SQLite + SQLModel]
        Worker[Worker Queues<br/>arq + Redis]
        Cache[Cache Layer<br/>Redis Sessions]
    end
    
    API --> Frontend
    API --> CLI
    
    Scheduler -.->|persistence| Database
    Worker -.->|requires| Cache
    Scheduler -.->|backup job| Database
    
    style API fill:#e8f5e8
    style Frontend fill:#fff3e0  
    style CLI fill:#e1f5fe
    style Scheduler fill:#f3e5f5
    style Database fill:#f3e5f5
    style Worker fill:#e8f5e8
```

## Component Deployment

Understanding how components deploy and scale is crucial for architectural decisions:

```mermaid
graph TB
    subgraph "Development"
        A1[All Components<br/>Single Container + Volumes]
    end
    
    subgraph "Production Scaling"
        B1[Web Service<br/>Backend + Frontend]
        B2[Scheduler Service<br/>Background Jobs]
        B3[Worker Pool<br/>Task Processing]
        B4[Infrastructure<br/>Redis + Database]
    end
    
    A1 --> B1
    A1 --> B2
    A1 --> B3
    A1 --> B4
    
    style A1 fill:#e1f5fe
    style B1 fill:#e8f5e8
    style B2 fill:#fff3e0
    style B3 fill:#f3e5f5
```

**Development:** All components run in a single container with shared volumes for simplicity.

**Production:** Components can be deployed as independent services, each scaling based on demand.

## Available Components

| Component | Purpose | Implementation | Status |
|-----------|---------|----------------|--------|
| **Core** (Backend + Frontend + CLI) | API + UI + Management | FastAPI + Flet + Typer | ✅ Always included |
| **Database** | Data persistence, ORM | SQLite + SQLModel | ✅ Available |
| **Scheduler** | Background tasks, cron jobs | APScheduler | ✅ Available |
| **Worker** | Async task queues | arq + Redis | 🧪 Experimental |
| **Cache** | Session storage, performance | Redis | 🚧 Coming soon |

!!! tip "Component Composition"
    Components can be combined to enable different capabilities. For detailed patterns on how components integrate with services and each other, see the **[Integration Patterns Reference](../integration-patterns.md)**.

---

**Next:** Choose your first component combination and see the integration in action:

- **[Database Component](./database.md)** - SQLite persistence with SQLModel ORM  
- **[Scheduler Component](./scheduler.md)** - Background tasks and cron jobs
- **[Worker Component](./worker/index.md)** - Async task processing and queues