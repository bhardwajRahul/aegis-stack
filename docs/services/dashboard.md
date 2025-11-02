# Services Dashboard Integration

Services appear in the health dashboard alongside components, providing real-time monitoring of your business-level capabilities like authentication and AI integrations.

!!! info "Services vs Components in Dashboard"
    **Components** (Backend, Database, Worker, Scheduler) - Infrastructure health
    **Services** (Auth, AI) - Business capability health and metrics

## Services Dashboard Cards

When you include services in your Aegis Stack project, they automatically appear in the health dashboard with dedicated monitoring cards showing service-specific metrics and configuration.

### Auth Service Card

The Auth service card displays authentication system health and configuration:

<img src="/aegis-stack/images/service-auth-card-light.png#only-light" alt="Auth Service Dashboard Card">
<img src="/aegis-stack/images/service-auth-card-dark.png#only-dark" alt="Auth Service Dashboard Card">

**Metrics Displayed:**

- **Total Users** - Number of registered users in the system
- **Response Time** - Average API response time for auth endpoints
- **JWT Algorithm** - Configured JWT signing algorithm (HS256, RS256, etc.)
- **Token Expiry** - JWT token lifetime configuration
- **Security Level** - Authentication security configuration (Standard, Enhanced)
- **Database** - Database connection status for user storage

!!! tip "Auth Service Monitoring"
    The Auth card shows real-time health of your authentication system, including user count, JWT configuration, and database connectivity - essential for security monitoring.

### AI Service Card

The AI service card displays AI integration health and provider configuration:

<img src="/aegis-stack/images/service-ai-card-light.png#only-light" alt="AI Service Dashboard Card">
<img src="/aegis-stack/images/service-ai-card-dark.png#only-dark" alt="AI Service Dashboard Card">

**Metrics Displayed:**

- **Provider** - Currently configured AI provider (OpenAI, Anthropic, Google, Groq, or Public)
- **Model** - AI model selection (auto-detection or specific model)
- **Conversations** - Number of active conversation sessions
- **Streaming** - Real-time streaming capability status
- **Configuration** - AI service configuration validation status
- **Response Time** - Average AI service API response time

!!! tip "AI Service Monitoring"
    The AI card provides visibility into your AI integration status, showing which provider is active, conversation count, and streaming availability.

## Health Status Indicators

Services use the same health status system as components:

| Status | Color | Meaning |
|--------|-------|---------|
| **✅ Healthy** | Green | Service fully operational |
| **⚠️ Warning** | Yellow | Service operational but with issues |
| **❌ Unhealthy** | Red | Service down or failing |
| **ℹ️ Info** | Blue | Service starting or informational status |

## Dashboard Layout

Services appear in the dashboard alongside components in a unified health monitoring interface:

```
┌─────────────────────────────────────────────┐
│          System Health Dashboard            │
├─────────────────────────────────────────────┤
│  Components (Infrastructure)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Backend  │ │ Database │ │  Worker  │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│                                             │
│  Services (Business Capabilities)           │
│  ┌──────────┐ ┌──────────┐                 │
│  │   Auth   │ │    AI    │                 │
│  └──────────┘ └──────────┘                 │
└─────────────────────────────────────────────┘
```

## CLI Health Commands

View service health status via CLI:

```bash
# View all health including services
your-app health

# Example output:
┌────────────────────────────────────────┐
│ System Health                          │
├────────────────────────────────────────┤
│ Components                             │
│   ✅ backend    - FastAPI healthy      │
│   ✅ database   - SQLite connected     │
│   ✅ worker     - arq processing       │
│                                        │
│ Services                               │
│   ✅ auth       - 0 users, HS256       │
│   ✅ ai         - Public provider      │
└────────────────────────────────────────┘
```

## Next Steps

- **[Services Overview](index.md)** - Return to services overview
- **[Auth Service](auth/index.md)** - Complete authentication documentation
- **[AI Service](ai/index.md)** - Complete AI service documentation
- **[Health Dashboard](../components/frontend/extras/dashboard.md)** - Component dashboard documentation
- **[CLI Reference](../cli-reference.md)** - Health command reference
