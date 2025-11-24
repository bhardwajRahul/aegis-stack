# Overseer

## Why This Exists

**Nothing is more annoying than the shrug.**

![Druski Shrug](../images/druski-shrug.gif)

Something's broken in production. You ask what happened. You get a shrug. You ask when it started. Another shrug. You ask where the logs are. Shrug. You ask how we can fix it. The biggest fucking shrug you've ever seen.

If something is wrong, I want to know **where**, **when**, **how**, **why**, and **how can we reconcile it**. Christ! Is that too much to ask?

**It shouldn't be so fucking hard to know what happened, when, where.**

You work with Datadog until management decides to migrate to New Relic. Or you're a solo dev who just wants to see if your background jobs are running without paying enterprise prices. Overseer solves this: centralized monitoring that you own, built into every Aegis Stack project from day one.

## What It Is

**Overseer is a read-only health monitoring dashboard** built into your Aegis Stack application. It provides real-time visibility into component and service health through a web UI and CLI commands.

![Overseer Dashboard](../images/overseer-dashboard-1-dark.png)

The dashboard displays:

- **Component Cards**: Backend, Database, Worker, Scheduler health
- **Service Cards**: Auth, AI, Comms health (when included)
- **Header**: Overall health summary and theme toggle
- **Auto-refresh**: Polls health endpoint every 30 seconds

## Current Capabilities

- Component health monitoring (Backend, Database, Worker, Scheduler)
- Service health monitoring (Auth, AI, Comms)
- System metrics (CPU, memory, disk usage)
- Status hierarchy (Healthy, Warning, Unhealthy, Info)
- Web dashboard with auto-refresh (30-second polling)
- CLI health commands via your generated app

## How It Works

```mermaid
sequenceDiagram
    participant C as Components/Services
    participant R as Health Registry
    participant E as /health/ Endpoint
    participant D as Dashboard UI

    Note over C,R: Startup: Registration Phase
    C->>R: register_health_check("backend", check_func)
    C->>R: register_health_check("database", check_func)
    C->>R: register_service_health_check("auth", check_func)

    Note over E,D: Runtime: Monitoring Phase
    D->>E: GET /health/ (every 30s)
    E->>R: Run all registered checks
    R->>C: Execute health check functions
    C->>R: Return ComponentStatus
    R->>E: Aggregate into SystemStatus
    E->>D: Return health data
    D->>D: Render component/service cards
```

**The Flow:**

1. **Registration**: During app startup, components and services register their health check functions with the health registry
2. **Aggregation**: The `/health/` endpoint runs all registered checks and aggregates results into a hierarchical status tree
3. **Polling**: The dashboard polls the health endpoint every 30 seconds
4. **Display**: Component and service cards render with real-time status, metrics, and details

## Component & Service Cards

Each card shows real-time health status, component-specific metrics, and configuration details. Click any card to open a detailed modal with diagnostics, performance data, and system information.

## Health Status Indicators

Each card displays a status indicator using the Overseer status hierarchy:

| Status | Color | Visual | Meaning |
|--------|-------|--------|---------|
| **✅ Healthy** | Green | Solid green border | Component/service fully operational |
| **ℹ️ Info** | Blue | Solid blue border | Informational status, not a problem |
| **⚠️ Warning** | Yellow | Orange border | Operational but with issues |
| **❌ Unhealthy** | Red | Red border | Component/service down or failing |

**Status Propagation**: Parent components inherit the worst child status:

- Any child **Unhealthy** → Parent **Unhealthy**
- Any child **Warning** (no unhealthy) → Parent **Warning**
- Any child **Info** (no unhealthy/warning) → Parent **Info**
- All children **Healthy** → Parent **Healthy**

## Theme Support

The dashboard automatically adapts to light and dark themes:

- **Light Mode**: White cards, dark text, subtle shadows
- **Dark Mode**: Dark cards, light text, enhanced contrast
- **Toggle**: Click the theme icon in the header to switch

Images and status colors adjust automatically to maintain visibility in both themes.

## CLI Health Access

The same health data is accessible via CLI:

```bash
# View system health
your-app health

# Example output:
┌────────────────────────────────────────┐
│ System Health                          │
├────────────────────────────────────────┤
│ Components                             │
│   ✅ backend    - FastAPI healthy      │
│   ✅ database   - SQLite connected     │
│   ✅ worker     - arq processing       │
│   ✅ scheduler  - 3 jobs scheduled     │
│                                        │
│ Services                               │
│   ✅ auth       - 42 users, HS256      │
│   ✅ ai         - Anthropic/Claude     │
└────────────────────────────────────────┘
```

## What's Coming

Overseer is evolving into a full operational control plane. Want to know where this is headed and why I'm so confident it'll work?

**[Read the full story →](story.md)** - How Overseer evolved from solving production problems at iHeartMedia (2022-2024) to becoming the built-in control plane for Aegis Stack.

## Next Steps

- **[The Overseer Story](story.md)** - Evolution from Streamlit to Aegis Stack, roadmap, and vision
- **[Integration Guide](integration.md)** - Add health checks to custom components/services
