"""Stunning marketing-grade dashboard with professional component cards."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import flet as ft

from app.services.system import get_system_status

from .dashboard.cards import (
    DatabaseCard,
    FastAPICard,
    RedisCard,
    SchedulerCard,
    WorkerCard,
)
from .dashboard.cards.card_utils import create_health_status_indicator
from .theme import ThemeManager

# Use simple filenames - Flet should auto-resolve from assets_dir
DEFAULT_LOGO_PATH = "aegis-manifesto.png"
DEFAULT_DARK_LOGO_PATH = "aegis-manifesto-dark.png"

# Load both light and dark logos as base64
def get_logo_base64(dark_mode: bool = False) -> str:
    """Get the logo as base64 for light or dark mode."""
    try:
        import base64
        from pathlib import Path
        filename = "aegis-manifesto-dark.png" if dark_mode else "aegis-manifesto.png"
        logo_path = Path(__file__).parent.parent.parent.parent / "assets" / filename
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        # Fallback to tiny red pixel if file read fails
        return (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHg"
            "gJ/PchI7wAAAABJRU5ErkJggg=="
        )


def create_frontend_app() -> Callable[[ft.Page], Awaitable[None]]:
    """Returns the Flet target function - simple system health dashboard."""

    async def flet_main(page: ft.Page) -> None:
        page.title = "Aegis Stack - System Dashboard"
        page.padding = ft.padding.only(
            left=20, right=20, top=20, bottom=20
        )  # Proper left padding
        page.scroll = ft.ScrollMode.AUTO

        # Simple theme setup
        theme_manager = ThemeManager(page)
        await theme_manager.initialize_themes()

        # Aegis Stack logo - bigger size and theme-aware loading
        logo_image = ft.Image(
            src_base64=get_logo_base64(theme_manager.is_dark_mode),  
            width=300,  # Bigger logo
            height=90,  # Bigger logo
            fit=ft.ImageFit.CONTAIN,
            error_content=ft.Text(
                "AEGIS STACK",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.ON_SURFACE,
            ),
        )

        # Theme toggle button
        theme_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE,
            tooltip="Switch to Dark Mode",
            icon_size=24,
        )

        async def update_logo() -> None:
            """Update logo based on current theme."""
            # Update the base64 source for the current theme
            logo_image.src_base64 = get_logo_base64(theme_manager.is_dark_mode)
            logo_image.src = None  # Clear the src to use src_base64

        async def toggle_theme(_: Any) -> None:
            """Toggle theme and update button icon and logo."""
            await theme_manager.toggle_theme()
            if theme_manager.is_dark_mode:
                theme_button.icon = ft.Icons.LIGHT_MODE
                theme_button.tooltip = "Switch to Light Mode"
            else:
                theme_button.icon = ft.Icons.DARK_MODE
                theme_button.tooltip = "Switch to Dark Mode"

            # Update logo immediately after theme change
            await update_logo()
            logo_image.update()
            page.update()

        theme_button.on_click = toggle_theme

        # Set initial logo based on current theme after theme manager is ready
        await update_logo()

        # Health status indicator with circular progress - create before header
        health_status_indicator = create_health_status_indicator(
            0, 0
        )  # Start with loading state

        # Professional header with Aegis Stack logo positioned further left
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=logo_image,
                                margin=ft.margin.only(left=-20),  # Adjust for padding
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "System Health Dashboard",
                                    size=24,
                                    weight=ft.FontWeight.W_400,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                                margin=ft.margin.only(left=10),  # Logo spacing
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Container(
                        content=health_status_indicator,
                        margin=ft.margin.only(right=20),  # Space before theme button
                    ),
                    ft.Container(content=theme_button, padding=10),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            margin=ft.margin.only(bottom=20),
            padding=ft.padding.only(left=0, right=0),  # Remove any default padding
        )
        # Responsive grid container - force 2 columns always
        component_cards_container = ft.Container(
            content=ft.ResponsiveRow(
                controls=[],  # Will be populated with cards
                spacing=20,  # Space between cards
                run_spacing=20,  # Space between rows
            ),
            alignment=ft.alignment.center,
        )

        # Add everything to page with modern layout
        page.add(
            header,
            ft.Container(
                content=ft.Column(
                    [
                        ft.Divider(color=ft.Colors.OUTLINE_VARIANT),
                        ft.Text(
                            "System Components",
                            size=24,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_SURFACE,
                        ),
                        component_cards_container,
                    ],
                    spacing=20,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.top_center,
            ),
        )

        def create_component_card(
            component_name: str, component_data: Any
        ) -> ft.Container:
            """Create stunning marketing-grade component cards."""
            if not component_data:
                return ft.Container()

            # Map component names to their stunning card classes
            if component_name == "backend":
                return FastAPICard(component_data).build()
            elif component_name == "worker":
                return WorkerCard(component_data).build()
            elif component_name == "redis":
                return RedisCard(component_data).build()
            elif component_name == "database":
                return DatabaseCard(component_data).build()
            elif component_name == "scheduler":
                return SchedulerCard(component_data).build()
            else:
                # Fallback for unknown components - should not happen in practice
                return ft.Container(
                    content=ft.Text(f"Unknown component: {component_name}"),
                    padding=20,
                    bgcolor=ft.Colors.SURFACE,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=16,
                    width=800,
                    height=240,
                )

        async def refresh_dashboard() -> None:
            """Refresh the stunning marketing-grade dashboard."""
            try:
                status = await get_system_status()

                # Update health status indicator with correct component counting
                components = {}
                if (
                    "aegis" in status.components
                    and status.components["aegis"].sub_components
                ):
                    components = status.components["aegis"].sub_components
                
                total_components = len(components)
                healthy_components = (
                    len([c for c in components.values() if c.status.value == "healthy"])
                    if components
                    else 0
                )

                # Update health status indicator in the header
                new_health_indicator = create_health_status_indicator(
                    healthy_components, total_components
                )

                # Update header health indicator
                header_row = page.controls[0].content  # header container -> Row
                header_row.controls[1].content = new_health_indicator

                # Components already extracted above for health calculation

                # Clear existing cards and create stunning new ones in responsive grid
                component_cards_container.content.controls.clear()

                # Create cards for all available components with responsive sizing
                for component_name, component_data in components.items():
                    card = create_component_card(component_name, component_data)
                    if (
                        isinstance(card.content, ft.Text)
                        and "Unknown component" in card.content.value
                    ):
                        continue  # Skip unknown components
                    
                    # Add card with responsive column sizing (6 = 50% = 2 columns)
                    card.col = {"xs": 12, "sm": 12, "md": 6, "lg": 6, "xl": 6}
                    component_cards_container.content.controls.append(card)

                page.update()

            except Exception as e:
                # Show error indicator in header
                error_indicator = create_health_status_indicator(0, 1)
                header_row = page.controls[0].content
                header_row.controls[1].content = error_indicator
                page.update()

        async def auto_refresh() -> None:
            """Simple auto-refresh loop."""
            while True:
                await refresh_dashboard()
                await asyncio.sleep(30)

        # Initial load and start refresh
        await refresh_dashboard()
        asyncio.create_task(auto_refresh())

    return flet_main