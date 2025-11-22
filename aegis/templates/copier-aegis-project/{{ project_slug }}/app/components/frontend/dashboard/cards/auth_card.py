"""
Authentication Service Card

Modern card component specifically designed for authentication service monitoring.
Shows auth-specific metrics with a clean, functional layout.
"""

import flet as ft
from app.components.frontend.controls import LabelText, PrimaryText, ServiceCard
from app.components.frontend.controls.tech_badge import TechBadge
from app.services.system.models import ComponentStatus

from .card_container import CardContainer
from .card_utils import (
    get_status_colors,
)


class AuthCard:
    """
    A clean authentication service card with real metrics.

    Features:
    - Real authentication metrics from health checks
    - Clean 2-column layout
    - Highlighted metric containers
    - Responsive design
    """

    def __init__(self, component_data: ComponentStatus):
        """Initialize with authentication service data from health check."""
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _create_metric_container(
        self, label: str, value: str, color: str = ft.Colors.BLUE
    ) -> ft.Container:
        """Create a properly sized metric container."""
        return ft.Container(
            content=ft.Column(
                [
                    LabelText(label),
                    ft.Container(height=8),  # More spacing
                    PrimaryText(value),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.all(16),  # More padding
            bgcolor=ft.Colors.with_opacity(0.08, color),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, color)),
            height=80,  # Taller containers
            expand=True,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create technology badge for authentication service."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return TechBadge(
            title="JWT",
            subtitle="Authentication",
            badge_text="Auth",
            badge_color=ft.Colors.AMBER,
            primary_color=primary_color,
        )

    def _create_metrics_section(self) -> ft.Container:
        """Create the metrics section with a clean grid layout."""
        # Get real data from metadata
        user_count_display = self.metadata.get("user_count_display", "0")
        response_time = self.component_data.response_time_ms
        database_available = self.metadata.get("database_available", False)
        jwt_algorithm = self.metadata.get("jwt_algorithm", "HS256")
        token_expiry_display = self.metadata.get("token_expiry_display", "30 min")
        security_level = self.metadata.get("security_level", "standard")

        # Color code security level
        security_color = {
            "high": ft.Colors.GREEN,
            "standard": ft.Colors.BLUE,
            "basic": ft.Colors.ORANGE,
        }.get(security_level, ft.Colors.GREY)

        # Create metrics grid (3 rows x 2 columns)
        return ft.Container(
            content=ft.Column(
                [
                    # Row 1: User count and Response time
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Total Users", user_count_display, ft.Colors.PURPLE
                            ),
                            self._create_metric_container(
                                "Response Time",
                                f"{response_time:.1f}ms" if response_time else "N/A",
                                (
                                    ft.Colors.GREEN
                                    if response_time and response_time < 100
                                    else ft.Colors.ORANGE
                                ),
                            ),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),  # Vertical spacing
                    # Row 2: JWT Algorithm and Token Expiry
                    ft.Row(
                        [
                            self._create_metric_container(
                                "JWT Algorithm", jwt_algorithm, ft.Colors.BLUE
                            ),
                            self._create_metric_container(
                                "Token Expiry", token_expiry_display, ft.Colors.GREEN
                            ),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),  # Vertical spacing
                    # Row 3: Security Level and Database
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Security Level", security_level.title(), security_color
                            ),
                            self._create_metric_container(
                                "Database",
                                "Available" if database_available else "Unavailable",
                                (
                                    ft.Colors.GREEN
                                    if database_available
                                    else ft.Colors.RED
                                ),
                            ),
                        ],
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            expand=True,
            padding=ft.padding.all(16),
        )

    def build(self) -> ft.Container:
        """Build and return the complete authentication card."""
        # Get colors based on component status
        _, _, border_color = get_status_colors(self.component_data)

        # Use ServiceCard for consistent service card layout
        content = ServiceCard(
            left_content=self._create_technology_badge(),
            right_content=self._create_metrics_section(),
        )

        return CardContainer(
            content=content,
            border_color=border_color,
            component_data=self.component_data,
            component_name="auth",
        )
