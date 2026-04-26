# Frontend Component

Build user interfaces entirely in Python using [Flet](https://flet.dev/) - no JavaScript required.

!!! info "Always Included"
    The frontend component is automatically included in all Aegis Stack projects.

## What You Get

- **Python-only development** - Same language for frontend and backend
- **Direct service integration** - Call Python functions instead of REST APIs
- **Cross-platform foundation** - Web, desktop, and mobile from same code
- **[Overseer](../overseer/index.md)** - Built-in health monitoring dashboard

## Quick Start

### Basic Dashboard

```python
# app/components/frontend/main.py
import flet as ft
from app.services.health_service import get_system_health

def create_frontend_app():
    async def main(page: ft.Page):
        page.title = "Dashboard"
        page.theme_mode = ft.ThemeMode.SYSTEM
        
        health_view = ft.Text("Loading...")
        
        async def refresh_health(e):
            health = await get_system_health()  # Direct Python call
            status = "🟢 Healthy" if health.healthy else "🔴 Unhealthy"
            health_view.value = f"Status: {status}"
            page.update()
        
        page.add(
            ft.Text("System Dashboard", size=24),
            ft.ElevatedButton("Refresh", on_click=refresh_health),
            health_view
        )
    
    return main
```

### Mount on FastAPI

```python
# app/integrations/main.py
import flet.fastapi as flet_fastapi
from app.components.frontend.main import create_frontend_app

flet_app = flet_fastapi.app(create_frontend_app())
app.mount("/dashboard", flet_app)
# Access at http://localhost:8000/dashboard
```


## Key Advantages

| Traditional Stack | Aegis Stack |
|-------------------|-------------|
| Python + JavaScript | Python only |
| REST API calls | Direct function calls |
| Separate build processes | Single container |
| Multiple services | Single application |

## Next Steps

- **[Overseer](../overseer/index.md)** - Built-in health monitoring dashboard
- **[Flet Documentation](https://flet.dev/docs/)** - Complete UI framework reference