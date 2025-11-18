"""
AI Service Detail Modal

Displays comprehensive AI service information including provider configuration,
conversation statistics, and usage metrics.
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

from ..cards.card_utils import PROVIDER_COLORS


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
    """Overview section showing key AI service metrics."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize overview section.

        Args:
            metadata: Component metadata containing conversation stats
        """
        super().__init__()

        total_conversations = metadata.get("total_conversations", 0)
        total_messages = metadata.get("total_messages", 0)
        unique_users = metadata.get("unique_users", 0)

        self.content = ft.Column(
            [
                H2Text("Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard(
                            "Total Conversations",
                            str(total_conversations),
                            ft.Icons.CHAT,
                            Theme.Colors.PRIMARY,
                        ),
                        MetricCard(
                            "Total Messages",
                            str(total_messages),
                            ft.Icons.MESSAGE,
                            Theme.Colors.INFO,
                        ),
                        MetricCard(
                            "Unique Users",
                            str(unique_users),
                            ft.Icons.PEOPLE,
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
    """Configuration section showing provider and model details."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize configuration section.

        Args:
            metadata: Component metadata containing provider config
        """
        super().__init__()

        provider = metadata.get("provider", "Unknown")
        model = metadata.get("model", "Unknown")
        enabled = metadata.get("enabled", False)
        config_valid = metadata.get("configuration_valid", False)
        streaming_supported = metadata.get("provider_supports_streaming", False)
        free_tier = metadata.get("provider_free_tier", False)

        # Provider color
        provider_color = PROVIDER_COLORS.get(provider.lower(), ft.Colors.GREY)

        # Build configuration rows
        config_rows = []

        # Provider row with badges
        provider_badges = [
            ft.Container(
                content=ft.Text(
                    provider.upper(),
                    size=Theme.Typography.BODY_SMALL,
                    weight=Theme.Typography.WEIGHT_SEMIBOLD,
                    color=Theme.Colors.BADGE_TEXT,
                ),
                padding=ft.padding.symmetric(
                    horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                ),
                bgcolor=provider_color,
                border_radius=Theme.Components.BADGE_RADIUS,
            ),
        ]

        if free_tier:
            provider_badges.append(
                ft.Container(
                    content=ft.Text(
                        "FREE TIER",
                        size=Theme.Typography.BODY_SMALL,
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        color=Theme.Colors.BADGE_TEXT,
                    ),
                    padding=ft.padding.symmetric(
                        horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                    ),
                    bgcolor=Theme.Colors.SUCCESS,
                    border_radius=Theme.Components.BADGE_RADIUS,
                ),
            )

        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Provider:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    ft.Row(provider_badges, spacing=Theme.Spacing.SM),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Model row (full name, no truncation)
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Model:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    BodyText(model),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Status row
        status_text = "✅ Enabled" if enabled else "❌ Disabled"
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Status:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    BodyText(status_text),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Streaming support row
        streaming_text = "✅ Supported" if streaming_supported else "❌ Not Supported"
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Streaming:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    BodyText(streaming_text),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Configuration validation row
        validation_text = "✅ Valid" if config_valid else "❌ Invalid"
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Configuration:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    BodyText(validation_text),
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

        # Conversation statistics
        total_conversations = metadata.get("total_conversations", 0)
        total_messages = metadata.get("total_messages", 0)
        unique_users = metadata.get("unique_users", 0)
        avg_messages = metadata.get("avg_messages_per_conversation", 0.0)

        # Configuration
        engine = metadata.get("engine", "Unknown")
        config_valid = metadata.get("configuration_valid", False)
        validation_errors_count = metadata.get("validation_errors_count", 0)

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
                stat_row("Total Conversations", str(total_conversations)),
                stat_row("Total Messages", str(total_messages)),
                stat_row("Unique Users", str(unique_users)),
                stat_row("Avg Messages/Conv", f"{avg_messages:.1f}"),
                ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                stat_row("Engine", engine),
                stat_row("Configuration Valid", "Yes" if config_valid else "No"),
                stat_row("Validation Errors", str(validation_errors_count)),
            ],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD


class AIDetailDialog(ft.AlertDialog):
    """
    AI service detail modal dialog.

    Displays comprehensive AI service information including provider configuration,
    conversation statistics, and usage metrics.
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize AI detail dialog.

        Args:
            component_data: AI service ComponentStatus from health check
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
                H2Text("🤖 AI Service Details"),
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
