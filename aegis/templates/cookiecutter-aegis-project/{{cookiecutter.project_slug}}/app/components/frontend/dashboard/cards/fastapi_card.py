"""
Stunning FastAPI Component Card

Modern, visually striking card component that displays rich FastAPI metrics
and system performance data using shared utility functions.
"""

import flet as ft

from app.components.frontend.controls import LabelText, PrimaryText
from app.services.system.models import ComponentStatus

from .card_utils import (
    create_hover_handler,
    create_progress_indicator,
    create_standard_card_container,
    create_stats_row,
    create_tech_badge,
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
        """Create the FastAPI technology badge section."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return create_tech_badge(
            title="FastAPI",
            subtitle="Backend API",
            icon="🚀",
            badge_text="API",
            badge_color=ft.Colors.GREEN,
            primary_color=primary_color,
            width=None,  # Let flex handle the width
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

        return ft.Column(
            metrics_controls,
            spacing=12,
        )

    def _create_details_section(self) -> ft.Container:
        """Create the additional details section with real route data."""
        response_time = self.component_data.response_time_ms or 0.0
        metadata = self.component_data.metadata or {}
        
        # Get real route data from metadata
        routes_data = metadata.get("routes", [])
        total_routes = metadata.get("total_routes", 0)
        total_endpoints = metadata.get("total_endpoints", 0)
        method_counts = metadata.get("method_counts", {})
        route_groups = metadata.get("route_groups", {})
        has_docs = metadata.get("has_docs", False)
        has_health = metadata.get("has_health", False)
        
        details_content = [
            PrimaryText("API Overview"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            create_stats_row("Response Time", f"{response_time:.1f}ms"),
            create_stats_row(
                "Status",
                self.component_data.status.value.title(),
                get_status_colors(self.component_data)[0],
            ),
        ]
        
        # Add route statistics
        if total_routes > 0:
            details_content.extend([
                create_stats_row("Routes", str(total_routes)),
                create_stats_row("Endpoints", str(total_endpoints)),
            ])
            
            # Add method breakdown if available
            if method_counts:
                method_summary = ", ".join([
                    f"{count} {method}" 
                    for method, count in sorted(method_counts.items())
                ])
                details_content.append(create_stats_row("Methods", method_summary))
        else:
            details_content.append(create_stats_row("Routes", "No routes found"))
        
        # Add feature indicators
        features = []
        if has_docs:
            features.append("Docs")
        if has_health:
            features.append("Health")
        if features:
            details_content.append(create_stats_row("Features", ", ".join(features)))
        
        # Add route groups summary if available
        if route_groups and total_routes > 0:
            details_content.extend([
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                PrimaryText("Route Groups"),
            ])
            
            # Show top route groups (max 4)
            for group, count in sorted(
                route_groups.items(), key=lambda x: x[1], reverse=True
            )[:4]:
                group_display = group if group != "root" else "/"
                details_content.append(
                    create_stats_row(f"{group_display}", f"{count} routes")
                )
        
        # Add sample routes if available
        if routes_data and total_routes > 0:
            details_content.extend([
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                PrimaryText("Sample Routes"),
            ])
            
            # Show first few routes  
            for route in routes_data[:4]:  # Show max 4 routes
                if isinstance(route, dict):
                    # Handle dict format (fallback compatibility)
                    methods = route.get("methods", [])
                    path = route.get("path", "")
                else:
                    # Handle Pydantic model format (new standard)
                    methods = (
                        route.get("methods", []) if hasattr(route, 'get') 
                        else getattr(route, 'methods', [])
                    )
                    path = (
                        route.get("path", "") if hasattr(route, 'get') 
                        else getattr(route, 'path', "")
                    )
                
                # Format route display
                method_str = "|".join(m for m in methods if m != "HEAD")
                route_display = f"{method_str} {path}"
                
                details_content.append(LabelText(f"• {route_display}"))
            
            # Show "+X more" if there are additional routes
            if total_routes > 4:
                remaining = total_routes - 4
                details_content.append(LabelText(f"• +{remaining} more..."))
        
        # Handle fallback case (no route data available)
        elif not routes_data and metadata.get("fallback"):
            details_content.extend([
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                LabelText("Route introspection unavailable", color=ft.Colors.ORANGE),
                LabelText("Using fallback display", size=11),
            ])

        return ft.Column(details_content, spacing=6)

    def build(self) -> ft.Container:
        """Build the complete FastAPI card with simple 3-section responsive layout."""
        primary_color, background_color, border_color = get_status_colors(
            self.component_data
        )

        # Responsive 3-section layout with flex ratios prioritizing middle
        content = ft.Row(
            [
                # Left: Tech badge (flexible, can shrink to minimum)
                ft.Container(
                    content=self._create_tech_badge(),
                    expand=2,  # ~20% of space, can shrink
                    width=100,  # Minimum width to keep badge readable
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                # Middle: Metrics (PRIORITY - gets most space and protection)
                ft.Container(
                    content=self._create_metrics_section(),
                    expand=5,  # ~50% of space, PRIORITY SECTION
                    padding=ft.padding.all(16),
                    width=300,  # Minimum width to keep metrics functional
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                # Right: Details (flexible, shrinks most aggressively)
                ft.Container(
                    content=self._create_details_section(),
                    expand=3,  # ~30% of space, can shrink aggressively
                    padding=ft.padding.all(16),
                    width=150,  # Minimum width to prevent complete disappearance
                ),
            ]
        )

        self._card_container = create_standard_card_container(
            content=content,
            primary_color=primary_color,
            border_color=border_color,
            width=None,  # Let ResponsiveRow handle the width
            hover_handler=create_hover_handler(
                None
            ),  # Will set after container creation
        )

        # Hover effects disabled

        return self._card_container
