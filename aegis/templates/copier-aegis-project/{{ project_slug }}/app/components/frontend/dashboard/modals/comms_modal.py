"""
Communications Service Detail Modal

Displays comprehensive comms service information including provider configuration,
channel status, and message capabilities.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    SecondaryText,
    Tag,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard


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

        self.content = ft.Row(
            [
                MetricCard(
                    "Channels",
                    f"{channels_configured}/{channels_total}",
                    status_color,
                ),
                MetricCard(
                    "Status",
                    status_text,
                    status_color,
                ),
                MetricCard(
                    "Capabilities",
                    ", ".join(capabilities) if capabilities else "None",
                    Theme.Colors.PRIMARY,
                ),
            ],
            spacing=Theme.Spacing.MD,
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
                    Tag(
                        text=email_provider.title()
                        if email_provider
                        else "Not Configured",
                        color=Theme.Colors.SUCCESS
                        if email_configured
                        else Theme.Colors.WARNING,
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
                    Tag(
                        text=sms_provider.title() if sms_provider else "Not Configured",
                        color=Theme.Colors.SUCCESS
                        if sms_configured
                        else Theme.Colors.WARNING,
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
                    Tag(
                        text=voice_provider.title()
                        if voice_provider
                        else "Not Configured",
                        color=Theme.Colors.SUCCESS
                        if voice_configured
                        else Theme.Colors.WARNING,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        self.content = ft.Column(
            [
                H3Text("Providers"),
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
                config_rows.append(BodyText(f"  • {error}"))
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
                config_rows.append(BodyText(f"  • {warning}"))

        # If no warnings or errors, show success message
        if not config_warnings and not config_errors:
            config_rows.append(BodyText("• All providers configured correctly"))

        self.content = ft.Column(
            [
                H3Text("Configuration"),
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
                H3Text("Statistics"),
                ft.Container(height=Theme.Spacing.SM),
                stat_row("Component Status", status.value.upper()),
                stat_row("Health Message", message),
                stat_row("Response Time", f"{response_time:.2f}ms"),
                ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                stat_row("Backend Dependency", backend_dep),
                stat_row("Worker Dependency", worker_dep),
            ],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD


class CommsDetailDialog(BaseDetailPopup):
    """
    Communications service detail popup dialog.

    Displays comprehensive comms service information including provider configuration,
    channel status, and message capabilities.
    """

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize the comms service details popup.

        Args:
            component_data: ComponentStatus containing component health and metrics
        """
        metadata = component_data.metadata or {}

        # Build sections
        sections = [
            OverviewSection(metadata),
            ProvidersSection(metadata),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            ConfigurationSection(metadata),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            StatisticsSection(component_data),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Comms Service",
            sections=sections,
        )
