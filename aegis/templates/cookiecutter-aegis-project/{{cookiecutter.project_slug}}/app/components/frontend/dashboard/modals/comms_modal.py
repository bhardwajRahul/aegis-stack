"""
Communications Service Detail Modal

Displays comprehensive comms service information including provider configuration,
channel status, and message capabilities.
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
    """Overview section showing key comms service metrics."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize overview section.

        Args:
            metadata: Component metadata containing comms statistics
        """
        super().__init__()

        channels_configured = metadata.get("channels_configured", 0)
        channels_total = metadata.get("channels_total", 3)
        capabilities = metadata.get("capabilities", [])

        # Determine overall status color
        if channels_configured == channels_total:
            status_color = Theme.Colors.SUCCESS
            status_text = "Fully Configured"
        elif channels_configured > 0:
            status_color = Theme.Colors.WARNING
            status_text = "Partially Configured"
        else:
            status_color = Theme.Colors.ERROR
            status_text = "Not Configured"

        self.content = ft.Column(
            [
                H2Text("Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard(
                            "Channels",
                            f"{channels_configured}/{channels_total}",
                            ft.Icons.HUB,
                            status_color,
                        ),
                        MetricCard(
                            "Status",
                            status_text,
                            ft.Icons.CHECK_CIRCLE
                            if channels_configured > 0
                            else ft.Icons.ERROR,
                            status_color,
                        ),
                        MetricCard(
                            "Capabilities",
                            ", ".join(capabilities) if capabilities else "None",
                            ft.Icons.SEND,
                            Theme.Colors.PRIMARY,
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class ProvidersSection(ft.Container):
    """Providers section showing email, SMS, and voice configuration."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize providers section.

        Args:
            metadata: Component metadata containing provider configuration
        """
        super().__init__()

        email_configured = metadata.get("email_configured", False)
        email_provider = metadata.get("email_provider")
        email_from = metadata.get("email_from")
        sms_configured = metadata.get("sms_configured", False)
        sms_provider = metadata.get("sms_provider")
        voice_configured = metadata.get("voice_configured", False)
        voice_provider = metadata.get("voice_provider")

        provider_rows = []

        # Email Provider row
        provider_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Email Provider:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    ft.Container(
                        content=ft.Text(
                            email_provider.title()
                            if email_provider
                            else "Not Configured",
                            size=Theme.Typography.BODY_SMALL,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                        ),
                        bgcolor=Theme.Colors.SUCCESS
                        if email_configured
                        else Theme.Colors.WARNING,
                        border_radius=Theme.Components.BADGE_RADIUS,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Email From address (if configured)
        if email_from:
            provider_rows.append(
                ft.Row(
                    [
                        SecondaryText(
                            "From Address:",
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            width=200,
                        ),
                        BodyText(email_from),
                    ],
                    spacing=Theme.Spacing.MD,
                )
            )

        # SMS Provider row
        provider_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "SMS Provider:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    ft.Container(
                        content=ft.Text(
                            sms_provider.title() if sms_provider else "Not Configured",
                            size=Theme.Typography.BODY_SMALL,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                        ),
                        bgcolor=Theme.Colors.SUCCESS
                        if sms_configured
                        else Theme.Colors.WARNING,
                        border_radius=Theme.Components.BADGE_RADIUS,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Voice Provider row
        provider_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Voice Provider:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    ft.Container(
                        content=ft.Text(
                            voice_provider.title()
                            if voice_provider
                            else "Not Configured",
                            size=Theme.Typography.BODY_SMALL,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                        ),
                        bgcolor=Theme.Colors.SUCCESS
                        if voice_configured
                        else Theme.Colors.WARNING,
                        border_radius=Theme.Components.BADGE_RADIUS,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        self.content = ft.Column(
            [
                H2Text("Providers"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(provider_rows, spacing=Theme.Spacing.SM),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class ConfigurationSection(ft.Container):
    """Configuration section showing warnings and setup guidance."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize configuration section.

        Args:
            metadata: Component metadata containing configuration warnings
        """
        super().__init__()

        config_warnings = metadata.get("configuration_warnings", [])
        config_errors = metadata.get("configuration_errors", [])

        config_rows = []

        # Configuration errors (if any)
        if config_errors:
            config_rows.append(
                SecondaryText(
                    "Configuration Errors:",
                    weight=Theme.Typography.WEIGHT_SEMIBOLD,
                )
            )
            for error in config_errors:
                config_rows.append(
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.ERROR,
                                size=16,
                                color=Theme.Colors.ERROR,
                            ),
                            BodyText(error),
                        ],
                        spacing=Theme.Spacing.SM,
                    )
                )
            config_rows.append(ft.Container(height=Theme.Spacing.SM))

        # Configuration warnings (if any)
        if config_warnings:
            config_rows.append(
                SecondaryText(
                    "Configuration Warnings:",
                    weight=Theme.Typography.WEIGHT_SEMIBOLD,
                )
            )
            for warning in config_warnings:
                config_rows.append(
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.WARNING_AMBER,
                                size=16,
                                color=Theme.Colors.WARNING,
                            ),
                            BodyText(warning),
                        ],
                        spacing=Theme.Spacing.SM,
                    )
                )

        # If no warnings or errors, show success message
        if not config_warnings and not config_errors:
            config_rows.append(
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE,
                            size=16,
                            color=Theme.Colors.SUCCESS,
                        ),
                        BodyText("All providers configured correctly"),
                    ],
                    spacing=Theme.Spacing.SM,
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
        worker_dep = dependencies.get("worker", "Unknown")

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
                stat_row("Worker Dependency", worker_dep),
            ],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD


class CommsDetailDialog(ft.AlertDialog):
    """
    Communications service detail modal dialog.

    Displays comprehensive comms service information including provider configuration,
    channel status, and message capabilities.
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize comms detail dialog.

        Args:
            component_data: Comms service ComponentStatus from health check
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
                H2Text("📧 Communications Service Details"),
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
                    ProvidersSection(metadata),
                    ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                    ConfigurationSection(metadata),
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
