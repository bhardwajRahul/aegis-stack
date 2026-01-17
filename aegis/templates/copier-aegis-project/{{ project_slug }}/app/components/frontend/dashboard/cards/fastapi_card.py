"""
Stunning FastAPI Component Card

Modern, visually striking card component that displays rich FastAPI metrics
and system performance data using shared utility functions.
"""

import flet as ft
from app.components.frontend.controls import LabelText, PrimaryText
from app.components.frontend.controls.tech_badge import TechBadge
from app.services.system.models import ComponentStatus

from .card_container import CardContainer
from .card_utils import (
    create_progress_indicator,
    create_stats_row,
    get_status_colors,
)


class FastAPICard:
    """
    A visually stunning, wide component card for displaying FastAPI metrics.

    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, metrics, details)
    - Status-aware coloring and visual indicators
    - Progress bars for CPU, Memory, and Disk usage
    - Hover effects and proper elevation
    - ee-toolset color system integration
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the FastAPI card with component data.

        Args:
            component_data: ComponentStatus containing FastAPI health and metrics
        """
        self.component_data = component_data
        self._card_container: ft.Container | None = None

    # Removed _get_status_colors - now using shared utility function

    def _create_tech_badge(self) -> ft.Container:
        """Create the Backend API technology badge section."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return TechBadge(
            title="FastAPI",
            subtitle="Web Framework",
            primary_color=primary_color,
        )

    def _create_metrics_section(self) -> ft.Container:
        """Create the system metrics section with progress indicators."""
        sub_components = self.component_data.sub_components

        # Extract metrics from sub-components
        cpu_data = sub_components.get("cpu")
        memory_data = sub_components.get("memory")
        disk_data = sub_components.get("disk")

        metrics_controls = []

        if cpu_data and cpu_data.metadata:
            cpu_percent = cpu_data.metadata.get("percent_used", 0.0)
            cpu_color = (
                ft.Colors.GREEN
                if cpu_percent < 70
                else ft.Colors.ORANGE
                if cpu_percent < 85
                else ft.Colors.RED
            )
            metrics_controls.append(
                create_progress_indicator(
                    "CPU Usage",
                    cpu_percent,
                    f"{cpu_data.metadata.get('core_count', 'N/A')} cores",
                    cpu_color,
                )
            )

        if memory_data and memory_data.metadata:
            memory_percent = memory_data.metadata.get("percent_used", 0.0)
            total_gb = memory_data.metadata.get("total_gb", 0.0)
            available_gb = memory_data.metadata.get("available_gb", 0.0)
            used_gb = total_gb - available_gb  # Calculate used memory
            memory_color = (
                ft.Colors.GREEN
                if memory_percent < 70
                else ft.Colors.ORANGE
                if memory_percent < 85
                else ft.Colors.RED
            )
            metrics_controls.append(
                create_progress_indicator(
                    "Memory Usage",
                    memory_percent,
                    f"{used_gb:.1f}GB / {total_gb:.1f}GB",  # Used/total format
                    memory_color,
                )
            )

        if disk_data and disk_data.metadata:
            disk_percent = disk_data.metadata.get("percent_used", 0.0)
            total_gb = disk_data.metadata.get("total_gb", 0.0)
            free_gb = disk_data.metadata.get("free_gb", 0.0)
            disk_color = (
                ft.Colors.GREEN
                if disk_percent < 70
                else ft.Colors.ORANGE
                if disk_percent < 85
                else ft.Colors.RED
            )
            metrics_controls.append(
                create_progress_indicator(
                    "Disk Usage",
                    disk_percent,
                    f"{free_gb:.1f}GB / {total_gb:.1f}GB",
                    disk_color,
                )
            )

        # Add middleware section
        middleware_stack = self.component_data.metadata.get("middleware_stack", [])
        security_count = self.component_data.metadata.get("security_count", 0)

        if middleware_stack:
            # Add divider between system metrics and middleware
            if metrics_controls:
                metrics_controls.append(
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT)
                )

            # Add middleware pipeline header
            metrics_controls.append(PrimaryText("Middleware Pipeline"))

            # Security middleware summary
            if security_count > 0:
                metrics_controls.append(
                    create_stats_row(
                        "Security", f"{security_count} layers", ft.Colors.GREEN
                    )
                )

            # Middleware stack (in execution order, show first 5)
            for idx, middleware in enumerate(middleware_stack[:5]):
                mw_name = middleware.get("type", "Unknown")
                order_indicator = f"{idx + 1}."

                # Color coding for security middleware
                is_security = middleware.get("is_security", False)
                color = ft.Colors.GREEN if is_security else ft.Colors.GREY_600

                metrics_controls.append(
                    ft.Row(
                        [
                            LabelText(order_indicator, size=10, width=20),
                            LabelText(
                                mw_name,
                                color=color,
                                size=10,
                                weight=ft.FontWeight.W_500
                                if is_security
                                else ft.FontWeight.NORMAL,
                            ),
                        ],
                        spacing=5,
                        tight=True,
                    )
                )

            # Show "more" indicator if there are additional middleware
            if len(middleware_stack) > 5:
                metrics_controls.append(
                    LabelText(
                        f"+ {len(middleware_stack) - 5} more middleware",
                        size=10,
                        color=ft.Colors.GREY_500,
                        italic=True,
                    )
                )

        return ft.Column(
            metrics_controls,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

    def _create_details_section(self) -> ft.Container:
        """Create the additional details section with real route data."""
        metadata = self.component_data.metadata or {}

        # Get real route and middleware data from metadata
        routes_data = metadata.get("routes", [])
        total_routes = metadata.get("total_routes", 0)
        total_endpoints = metadata.get("total_endpoints", 0)
        method_counts = metadata.get("method_counts", {})
        route_groups = metadata.get("route_groups", {})
        has_docs = metadata.get("has_docs", False)
        total_middleware = metadata.get("total_middleware", 0)

        details_content = [
            PrimaryText("API Overview"),
            ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
            create_stats_row(
                "Status",
                self.component_data.status.value.title(),
                get_status_colors(self.component_data)[0],
            ),
        ]

        # Add route statistics
        if total_routes > 0:
            details_content.extend(
                [
                    create_stats_row("Routes", str(total_routes)),
                    create_stats_row("Endpoints", str(total_endpoints)),
                ]
            )

        # Add middleware count if available
        if total_middleware > 0:
            details_content.append(
                create_stats_row("Middleware", f"{total_middleware} layers")
            )

        if total_routes > 0:
            # Add method breakdown if available
            if method_counts:
                method_summary = ", ".join(
                    [
                        f"{count} {method}"
                        for method, count in sorted(method_counts.items())
                    ]
                )
                details_content.append(create_stats_row("Methods", method_summary))
        else:
            details_content.append(create_stats_row("Routes", "No routes found"))

        # Add docs feature indicator if available
        if has_docs:
            details_content.append(create_stats_row("Features", "Docs"))

        # Add route groups summary if available
        if route_groups and total_routes > 0:
            details_content.extend(
                [
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    PrimaryText("Route Groups"),
                ]
            )

            # Show top route groups (max 4)
            for group, count in sorted(
                route_groups.items(), key=lambda x: x[1], reverse=True
            )[:4]:
                group_display = group if group != "root" else "/"
                details_content.append(
                    create_stats_row(f"{group_display}", f"{count} routes")
                )

        # Handle fallback case (no route data available)
        elif not routes_data and metadata.get("fallback"):
            details_content.extend(
                [
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    LabelText(
                        "Route introspection unavailable", color=ft.Colors.ORANGE
                    ),
                    LabelText("Using fallback display", size=11),
                ]
            )

        return ft.Column(details_content, spacing=6, scroll=ft.ScrollMode.AUTO)

    def build(self) -> ft.Container:
        """Build the complete FastAPI card with simple 3-section responsive layout."""
        primary_color, background_color, border_color = get_status_colors(
            self.component_data
        )

        # Responsive 3-section layout with flex ratios prioritizing middle
        content = ft.Row(
            [
                # Left: Tech badge (fixed width)
                ft.Container(
                    content=self._create_tech_badge(),
                    width=200,  # Fixed width - honors TechBadge width
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT),
                # Middle: Metrics (PRIORITY - gets most space and protection)
                ft.Container(
                    content=self._create_metrics_section(),
                    expand=5,  # ~50% of space, PRIORITY SECTION
                    padding=ft.padding.all(16),
                    width=300,  # Minimum width to keep metrics functional
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT),
                # Right: Details (flexible, shrinks most aggressively)
                ft.Container(
                    content=self._create_details_section(),
                    expand=3,  # ~30% of space, can shrink aggressively
                    padding=ft.padding.all(16),
                    width=150,  # Minimum width to prevent complete disappearance
                ),
            ]
        )

        return CardContainer(
            content=content,
            border_color=border_color,
            component_data=self.component_data,
            component_name="backend",
        )
