"""
Auth Service Detail Modal

Displays comprehensive auth service information including security configuration,
user statistics, and JWT settings.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    DisplayText,
    H2Text,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus


class MetricCard(ft.Container):
    """Reusable metric display card with icon, value, and label."""

    def __init__(self, label: str, value: str, icon: str, color: str) -> None:
        """
        Initialize metric card.

        Args:
            label: Metric label text
            value: Metric value to display
            icon: Flet icon constant
            color: Icon and accent color
        """
        super().__init__()

        self.content = ft.Column(
            [
                ft.Icon(icon, size=32, color=color),
                DisplayText(value),
                SecondaryText(
                    label,
                    size=Theme.Typography.BODY_SMALL,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.OUTLINE_VARIANT)
        self.border_radius = Theme.Components.CARD_RADIUS
        self.expand = True


class OverviewSection(ft.Container):
    """Overview section showing key auth service metrics."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize overview section.

        Args:
            metadata: Component metadata containing auth statistics
        """
        super().__init__()

        user_count_display = metadata.get("user_count_display", "0")
        security_level = metadata.get("security_level", "basic")
        token_expiry_display = metadata.get("token_expiry_display", "Unknown")

        # Security level color mapping
        security_colors = {
            "high": Theme.Colors.SUCCESS,
            "standard": Theme.Colors.INFO,
            "basic": Theme.Colors.WARNING,
        }
        security_color = security_colors.get(security_level, Theme.Colors.WARNING)

        self.content = ft.Column(
            [
                H2Text("Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard(
                            "Total Users",
                            user_count_display,
                            ft.Icons.PEOPLE,
                            Theme.Colors.PRIMARY,
                        ),
                        MetricCard(
                            "Security Level",
                            security_level.title(),
                            ft.Icons.SECURITY,
                            security_color,
                        ),
                        MetricCard(
                            "Token Expiry",
                            token_expiry_display,
                            ft.Icons.TIMER,
                            Theme.Colors.SUCCESS,
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class ConfigurationSection(ft.Container):
    """Configuration section showing JWT and security settings."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize configuration section.

        Args:
            metadata: Component metadata containing auth configuration
        """
        super().__init__()

        jwt_algorithm = metadata.get("jwt_algorithm", "Unknown")
        secret_key_configured = metadata.get("secret_key_configured", False)
        secret_key_length = metadata.get("secret_key_length", 0)
        database_available = metadata.get("database_available", False)
        token_expiry_display = metadata.get("token_expiry_display", "Unknown")

        # Secret key strength assessment
        if secret_key_length >= 64:
            key_strength = "Strong"
            key_strength_color = Theme.Colors.SUCCESS
        elif secret_key_length >= 32:
            key_strength = "Moderate"
            key_strength_color = Theme.Colors.WARNING
        else:
            key_strength = "Weak"
            key_strength_color = Theme.Colors.ERROR

        # Build configuration rows
        config_rows = []

        # JWT Algorithm row with badge
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "JWT Algorithm:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    ft.Container(
                        content=ft.Text(
                            jwt_algorithm,
                            size=Theme.Typography.BODY_SMALL,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                        ),
                        bgcolor=Theme.Colors.INFO,
                        border_radius=Theme.Components.BADGE_RADIUS,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Secret Key Status row
        secret_key_status = (
            "✅ Configured" if secret_key_configured else "❌ Not Configured"
        )
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Secret Key:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(secret_key_status),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Secret Key Strength row (only if configured)
        if secret_key_configured:
            config_rows.append(
                ft.Row(
                    [
                        SecondaryText(
                            "Key Strength:",
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            width=200,
                        ),
                        ft.Container(
                            content=ft.Text(
                                f"{key_strength} ({secret_key_length} chars)",
                                size=Theme.Typography.BODY_SMALL,
                                weight=Theme.Typography.WEIGHT_SEMIBOLD,
                                color=Theme.Colors.BADGE_TEXT,
                            ),
                            padding=ft.padding.symmetric(
                                horizontal=Theme.Spacing.SM,
                                vertical=Theme.Spacing.XS,
                            ),
                            bgcolor=key_strength_color,
                            border_radius=Theme.Components.BADGE_RADIUS,
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                )
            )

        # Database Status row
        database_status = "✅ Available" if database_available else "❌ Unavailable"
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Database:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(database_status),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Token Expiry row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Token Expiry:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(token_expiry_display),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        self.content = ft.Column(
            [
                H2Text("Configuration"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(config_rows, spacing=Theme.Spacing.SM),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class SecuritySection(ft.Container):
    """Security section showing security analysis and recommendations."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize security section.

        Args:
            metadata: Component metadata containing security information
        """
        super().__init__()

        security_level = metadata.get("security_level", "basic")
        configuration_issues = metadata.get("configuration_issues", [])

        # Security level descriptions
        security_descriptions = {
            "high": "Strong security configuration with robust encryption and key management.",
            "standard": "Adequate security for most applications. Consider upgrading to asymmetric algorithms (RS256/ES256) for enhanced security.",
            "basic": "Minimal security configuration. Strongly recommend improving secret key strength and considering stronger algorithms.",
        }

        security_description = security_descriptions.get(
            security_level, "Unknown security configuration."
        )

        # Security level color mapping
        security_colors = {
            "high": Theme.Colors.SUCCESS,
            "standard": Theme.Colors.INFO,
            "basic": Theme.Colors.WARNING,
        }
        security_color = security_colors.get(security_level, Theme.Colors.WARNING)

        security_rows = []

        # Security Level row with badge
        security_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Security Level:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    ft.Container(
                        content=ft.Text(
                            security_level.upper(),
                            size=Theme.Typography.BODY_SMALL,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                        ),
                        bgcolor=security_color,
                        border_radius=Theme.Components.BADGE_RADIUS,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Security description
        security_rows.append(
            ft.Container(
                content=BodyText(security_description),
                padding=ft.padding.only(left=200, top=Theme.Spacing.XS),
            )
        )

        # Configuration issues (if any)
        if configuration_issues:
            security_rows.append(ft.Container(height=Theme.Spacing.SM))
            security_rows.append(
                SecondaryText(
                    "Configuration Issues:",
                    weight=Theme.Typography.WEIGHT_SEMIBOLD,
                )
            )
            for issue in configuration_issues:
                security_rows.append(
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.WARNING_AMBER,
                                size=16,
                                color=Theme.Colors.WARNING,
                            ),
                            BodyText(issue),
                        ],
                        spacing=Theme.Spacing.SM,
                    )
                )

        self.content = ft.Column(
            [
                H2Text("Security"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(security_rows, spacing=Theme.Spacing.SM),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class StatisticsSection(ft.Container):
    """Statistics section showing detailed metrics and technical information."""

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize statistics section.

        Args:
            component_data: Complete component status information
        """
        super().__init__()

        status = component_data.status
        message = component_data.message
        response_time = component_data.response_time_ms or 0
        metadata = component_data.metadata or {}

        # Dependencies
        dependencies = metadata.get("dependencies", {})
        backend_dep = dependencies.get("backend", "Unknown")
        database_dep = dependencies.get("database", "Unknown")

        def stat_row(label: str, value: str) -> ft.Row:
            """Create a statistics row with label and value."""
            return ft.Row(
                [
                    SecondaryText(
                        f"{label}:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(value),
                ],
                spacing=Theme.Spacing.MD,
            )

        self.content = ft.Column(
            [
                H2Text("Statistics"),
                ft.Container(height=Theme.Spacing.SM),
                stat_row("Component Status", status.value.upper()),
                stat_row("Health Message", message),
                stat_row("Response Time", f"{response_time:.2f}ms"),
                ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                stat_row("Backend Dependency", backend_dep),
                stat_row("Database Dependency", database_dep),
            ],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD


class AuthDetailDialog(ft.AlertDialog):
    """
    Auth service detail modal dialog.

    Displays comprehensive auth service information including security configuration,
    user statistics, and JWT settings.
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize auth detail dialog.

        Args:
            component_data: Auth service ComponentStatus from health check
        """
        self.component_data = component_data
        metadata = component_data.metadata or {}

        # Determine status badge color
        status = component_data.status
        if status.value == "healthy":
            status_color = Theme.Colors.SUCCESS
        elif status.value == "info":
            status_color = Theme.Colors.INFO
        elif status.value == "warning":
            status_color = Theme.Colors.WARNING
        else:  # unhealthy
            status_color = Theme.Colors.ERROR

        # Build modal content
        title = ft.Row(
            [
                H2Text("🔐 Auth Service Details"),
                ft.Container(
                    content=ft.Text(
                        status.value.upper(),
                        size=Theme.Typography.BODY_SMALL,
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        color=Theme.Colors.BADGE_TEXT,
                    ),
                    padding=ft.padding.symmetric(
                        horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                    ),
                    bgcolor=status_color,
                    border_radius=Theme.Components.BADGE_RADIUS,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        content = ft.Container(
            content=ft.Column(
                [
                    OverviewSection(metadata),
                    ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                    ConfigurationSection(metadata),
                    ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                    SecuritySection(metadata),
                    ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                    StatisticsSection(component_data),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=900,
            height=700,
        )

        super().__init__(
            modal=False,
            title=title,
            content=content,
            actions=[
                ft.TextButton("Close", on_click=self._close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _close(self, e: ft.ControlEvent) -> None:
        """Close the modal dialog."""
        self.open = False
        e.page.update()
