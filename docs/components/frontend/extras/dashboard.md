# Health Dashboard Extra

Production-ready system monitoring interface that demonstrates Flet's capabilities for building enterprise-grade dashboards.

!!! info "Extra Component"
    The health dashboard extra adds a comprehensive monitoring interface to the core frontend component, showcasing real-time data integration and responsive UI patterns.

## What This Extra Adds

### System Health Dashboard

A complete monitoring interface that provides real-time visibility into your application's health and performance:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/aegis-stack/images/dashboard-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/aegis-stack/images/dashboard-light.png">
  <img alt="System Health Dashboard" src="/aegis-stack/images/dashboard-light.png">
</picture>

!!! success "Dashboard Features"
    The health dashboard showcases enterprise-grade UI patterns:
    
    - **Real-time status monitoring** with color-coded component health
    - **Responsive layout** that adapts to different screen sizes
    - **Interactive components** with hover states and click actions
    - **Professional design** with consistent theming and typography

### Dashboard Capabilities

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Real-time Updates** | WebSocket integration | Live data without page refresh |
| **Component Status** | Color-coded health indicators | Quick visual system assessment |
| **Responsive Design** | Flet's adaptive layouts | Works on desktop, tablet, mobile |
| **Theme Support** | Automatic light/dark modes | Matches user preferences |
| **Interactive Controls** | Buttons, toggles, dropdowns | Full user interaction capabilities |

## Dashboard Interface

### Status Overview

The dashboard provides a comprehensive view of system health:

```python
# Health status display
async def create_health_overview() -> ft.Container:
    """Create the main health status overview."""
    return ft.Container(
        content=ft.Column([
            ft.Text("System Health", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([
                create_status_card("API", "healthy", "✅"),
                create_status_card("Database", "warning", "⚠️"),
                create_status_card("Redis", "healthy", "✅"),
                create_status_card("Worker", "info", "ℹ️")
            ], wrap=True)
        ]),
        padding=20
    )
```

### Component Health Cards

Individual component status with detailed information:

```python
def create_status_card(name: str, status: str, icon: str) -> ft.Card:
    """Create a status card for a system component."""
    color_map = {
        "healthy": ft.colors.GREEN,
        "warning": ft.colors.ORANGE, 
        "unhealthy": ft.colors.RED,
        "info": ft.colors.BLUE
    }
    
    return ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(icon, size=20),
                    ft.Text(name, size=16, weight=ft.FontWeight.BOLD)
                ]),
                ft.Text(status.title(), color=color_map.get(status))
            ]),
            padding=15
        )
    )
```

### Real-time Data Integration

```python
async def refresh_dashboard_data(page: ft.Page):
    """Refresh all dashboard data from backend APIs."""
    # Fetch health data from your backend
    health_data = await get_system_health()
    
    # Update UI components
    for component_name, health_info in health_data.components.items():
        component_card = find_component_card(page, component_name)
        if component_card:
            update_status_card(component_card, health_info)
    
    # Trigger UI update
    page.update()
```

## Theme Support

The dashboard automatically adapts to light and dark themes:

```python
# Theme-aware styling
def get_theme_colors(page: ft.Page) -> dict:
    """Get colors based on current theme."""
    if page.theme_mode == ft.ThemeMode.DARK:
        return {
            "background": ft.colors.GREY_900,
            "surface": ft.colors.GREY_800,
            "text": ft.colors.WHITE
        }
    else:
        return {
            "background": ft.colors.WHITE,
            "surface": ft.colors.GREY_100,
            "text": ft.colors.BLACK
        }
```

## Integration Example

### Adding Dashboard to Your App

```python
# app/components/frontend/dashboard.py
import flet as ft
from app.services.health_service import get_system_health

async def create_dashboard_page(page: ft.Page):
    """Create the health dashboard page."""
    page.title = "System Health Dashboard"
    page.theme_mode = ft.ThemeMode.SYSTEM
    
    # Create dashboard layout
    dashboard = ft.Column([
        await create_health_overview(),
        ft.Divider(),
        await create_metrics_section(),
        ft.Divider(),
        await create_logs_section()
    ])
    
    # Add refresh button
    refresh_btn = ft.ElevatedButton(
        "Refresh",
        on_click=lambda e: refresh_dashboard_data(page)
    )
    
    page.add(
        ft.AppBar(title=ft.Text("Health Dashboard")),
        dashboard,
        ft.Container(
            content=refresh_btn,
            alignment=ft.alignment.center,
            padding=20
        )
    )

# Mount dashboard in your main app
def create_frontend_app():
    return create_dashboard_page
```

### Backend Health API Integration

```python
# Integration with health endpoints
async def get_dashboard_health_data() -> dict:
    """Fetch health data for dashboard display."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health/detailed")
        return response.json()
```

## Customization

### Adding Custom Metrics

```python
# Extend dashboard with custom metrics
async def create_custom_metrics_card() -> ft.Card:
    """Add custom business metrics to dashboard."""
    metrics = await get_business_metrics()
    
    return ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Business Metrics", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Text(f"Active Users: {metrics['active_users']}"),
                    ft.Text(f"Revenue: ${metrics['revenue']}")
                ])
            ]),
            padding=15
        )
    )
```

### Custom Status Indicators

```python
# Create custom status visualizations
def create_progress_indicator(name: str, value: float, max_value: float) -> ft.Row:
    """Create a progress bar for metrics."""
    percentage = (value / max_value) * 100
    
    return ft.Row([
        ft.Text(f"{name}:", width=100),
        ft.ProgressBar(value=value/max_value, width=200),
        ft.Text(f"{percentage:.1f}%")
    ])
```

## Performance Considerations

!!! tip "Dashboard Performance Tips"
    - **Lazy loading**: Load dashboard data only when visible
    - **Update throttling**: Limit refresh frequency to prevent UI flickering
    - **Efficient data fetching**: Use WebSocket connections for real-time updates
    - **Component memoization**: Cache expensive UI components

## Next Steps

- **[Frontend Component](../../frontend.md)** - Return to frontend overview
- **[Flet Documentation](https://flet.dev/docs/)** - Complete UI framework capabilities
- **[Backend Integration](../../webserver.md)** - API health endpoints