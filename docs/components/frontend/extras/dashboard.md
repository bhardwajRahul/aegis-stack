# Health Dashboard Extra

System health monitoring interface built with Flet.

!!! info "Extra Component"
    The health dashboard extra adds a monitoring interface to the frontend component, displaying component and service health status.

## What This Extra Adds

### System Health Dashboard

A monitoring interface that displays your application's component and service health:

<img src="/aegis-stack/images/dashboard-light.png#only-light" alt="System Health Dashboard">
<img src="/aegis-stack/images/dashboard-dark.png#only-dark" alt="System Health Dashboard">

!!! success "Current Dashboard Features"
    - **Component status cards** - Backend, Database, Worker, Scheduler health
    - **Service status cards** - Auth, AI service health (when included)
    - **Light/dark theme support** - Automatically adapts to theme
    - **Health status polling** - Fetches health data from `/health/detailed` endpoint

## What's Shown

**Component Cards** (when included in your project):
- **Backend** - API health status
- **Database** - Connection health
- **Worker** - Queue health for each worker queue (system, load_test, etc.)
- **Scheduler** - Scheduled job health

**Service Cards** (when included in your project):
- **Auth Service** - User counts, JWT status, security level
- **AI Service** - Provider info, conversation counts, model details

See **[Services Dashboard Documentation](../../../services/dashboard.md)** for service-specific card details.

## Next Steps

- **[Services Dashboard](../../../services/dashboard.md)** - Complete services dashboard documentation
- **[Frontend Component](../../frontend.md)** - Return to frontend overview
- **[Flet Documentation](https://flet.dev/docs/)** - Complete UI framework capabilities
- **[Backend Integration](../../webserver.md)** - API health endpoints