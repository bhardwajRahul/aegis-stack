"""
Authentication Service Card

Modern card component specifically designed for authentication service monitoring.
Shows auth-specific metrics like token validation, user sessions, and security status.
"""

import flet as ft
from app.components.frontend.controls import LabelText, PrimaryText
from app.services.system.models import ComponentStatus

from .card_utils import (
    create_hover_handler,
    create_responsive_3_section_layout,
    create_standard_card_container,
    create_stats_row,
    create_tech_badge,
    get_status_colors,
)


class AuthCard:
    """
    A visually stunning component card specifically for authentication service.

    Features:
    - Authentication-specific metrics and status
    - Token validation health
    - User session monitoring
    - Security indicators
    - Modern Material Design 3 styling
    """

    def __init__(self, component_data: ComponentStatus):
        """Initialize with authentication service data from health check."""
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _create_auth_metrics(self) -> ft.Column:
        """Create authentication-specific metrics display."""
        metrics_items = []

        # Token validation status
        token_status = self.metadata.get("token_validation", "unknown")
        token_color = ft.Colors.GREEN if token_status == "healthy" else ft.Colors.ORANGE

        metrics_items.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=8,
                            height=8,
                            bgcolor=token_color,
                            border_radius=4,
                        ),
                        ft.Column(
                            [
                                PrimaryText("Token Validation"),
                                LabelText(token_status.title(), size=12),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.with_opacity(0.03, token_color),
                border_radius=8,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, token_color)),
            )
        )

        # Session management
        sessions_active = self.metadata.get("active_sessions", 0)
        sessions_color = ft.Colors.BLUE

        metrics_items.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=8,
                            height=8,
                            bgcolor=sessions_color,
                            border_radius=4,
                        ),
                        ft.Column(
                            [
                                PrimaryText("Active Sessions"),
                                LabelText(str(sessions_active), size=12),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.with_opacity(0.03, sessions_color),
                border_radius=8,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, sessions_color)),
            )
        )

        # Security features
        security_status = self.metadata.get("security_features", "enabled")
        security_color = (
            ft.Colors.GREEN if security_status == "enabled" else ft.Colors.RED
        )

        metrics_items.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=8,
                            height=8,
                            bgcolor=security_color,
                            border_radius=4,
                        ),
                        ft.Column(
                            [
                                PrimaryText("Security"),
                                LabelText(security_status.title(), size=12),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.with_opacity(0.03, security_color),
                border_radius=8,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, security_color)),
            )
        )

        return ft.Column(metrics_items, spacing=8)

    def _create_auth_overview(self) -> ft.Container:
        """Create the authentication service overview section."""
        # Auth-specific statistics
        total_users = self.metadata.get("total_users", 0)
        failed_logins = self.metadata.get("failed_logins_24h", 0)
        token_expiry = self.metadata.get("avg_token_lifetime", "24h")

        stats_rows = [
            create_stats_row("Total Users", str(total_users)),
            create_stats_row("Failed Logins", str(failed_logins)),
            create_stats_row("Token Lifetime", str(token_expiry)),
        ]

        return ft.Container(
            content=ft.Column(
                [
                    PrimaryText("Authentication"),
                    ft.Container(height=8),  # Spacing
                    ft.Column(stats_rows, spacing=4),
                    ft.Container(height=12),  # Spacing
                    self._create_auth_metrics(),
                ]
            ),
            expand=True,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create technology badge for authentication service."""
        _, primary_color, _ = get_status_colors(self.component_data)

        return create_tech_badge(
            title="Auth",
            subtitle="JWT + OAuth",
            icon="🔐",
            badge_text="AUTH",
            badge_color=primary_color,
            primary_color=primary_color,
        )

    def _create_stats_section(self) -> ft.Container:
        """Create the right stats section with auth-specific metrics."""
        response_time = self.component_data.response_time_ms

        stats_items = []

        # Response time
        if response_time is not None:
            stats_items.append(
                ft.Container(
                    content=ft.Column(
                        [
                            LabelText("Response Time", size=12),
                            PrimaryText(f"{response_time:.1f}ms"),
                        ],
                        spacing=4,
                    ),
                    padding=ft.padding.all(12),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
                    border_radius=8,
                )
            )

        # Security level indicator
        security_level = self.metadata.get("security_level", "standard")
        security_color = {
            "high": ft.Colors.GREEN,
            "standard": ft.Colors.BLUE,
            "basic": ft.Colors.ORANGE,
        }.get(security_level, ft.Colors.GREY)

        stats_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        LabelText("Security Level", size=12),
                        ft.Text(
                            security_level.title(),
                            color=security_color,
                            size=16,
                            weight=ft.FontWeight.W_400,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.all(12),
                bgcolor=ft.Colors.with_opacity(0.05, security_color),
                border_radius=8,
            )
        )

        # OAuth providers status
        oauth_providers = self.metadata.get("oauth_providers", [])
        oauth_count = len(oauth_providers) if oauth_providers else 0

        stats_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        LabelText("OAuth Providers", size=12),
                        PrimaryText(str(oauth_count)),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.all(12),
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.PURPLE),
                border_radius=8,
            )
        )

        return ft.Container(
            content=ft.Column(stats_items, spacing=8),
            width=140,
        )

    def build(self) -> ft.Container:
        """Build and return the complete authentication card."""
        # Get colors based on component status
        background_color, primary_color, border_color = get_status_colors(
            self.component_data
        )

        # Use shared responsive 3-section layout
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_auth_overview(),
            right_content=self._create_stats_section(),
        )

        # Create the container
        card_container = create_standard_card_container(
            content=content,
            primary_color=primary_color,
            border_color=border_color,
            width=None,
            hover_handler=None,
        )

        # Create hover handler for the card
        hover_handler = create_hover_handler(card_container)

        # Update the hover handler on the container
        card_container.on_hover = hover_handler

        return card_container
