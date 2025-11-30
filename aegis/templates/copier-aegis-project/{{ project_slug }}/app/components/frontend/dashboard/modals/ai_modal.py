"""
AI Service Detail Modal

Displays comprehensive AI service information including provider configuration,
conversation statistics, and usage metrics.
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

from ..cards.card_utils import PROVIDER_COLORS
from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard


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

        self.content = ft.Row(
            [
                MetricCard(
                    "Total Conversations",
                    str(total_conversations),
                    Theme.Colors.PRIMARY,
                ),
                MetricCard(
                    "Total Messages",
                    str(total_messages),
                    Theme.Colors.INFO,
                ),
                MetricCard(
                    "Unique Users",
                    str(unique_users),
                    Theme.Colors.SUCCESS,
                ),
            ],
            spacing=Theme.Spacing.MD,
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
        provider_color = PROVIDER_COLORS.get(
            provider.lower(), ft.Colors.ON_SURFACE_VARIANT
        )

        # Build configuration rows
        config_rows = []

        # Provider row with badges
        provider_badges = [
            Tag(text=provider.upper(), color=provider_color),
        ]

        if free_tier:
            provider_badges.append(
                Tag(text="FREE TIER", color=Theme.Colors.SUCCESS),
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
                    Tag(text=model, color=Theme.Colors.INFO),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Status row
        status_text = "Enabled" if enabled else "Disabled"
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
        streaming_text = "Supported" if streaming_supported else "Not Supported"
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
        validation_text = "Valid" if config_valid else "Invalid"
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
                H3Text("Statistics"),
                ft.Container(height=Theme.Spacing.SM),
                stat_row("Component Status", status.value.upper()),
                stat_row("Health Message", message),
                stat_row("Response Time", f"{response_time:.2f}ms"),
                ft.Divider(height=20, color=ft.Colors.OUTLINE),
                stat_row("Total Conversations", str(total_conversations)),
                stat_row("Total Messages", str(total_messages)),
                stat_row("Unique Users", str(unique_users)),
                stat_row("Avg Messages/Conv", f"{avg_messages:.1f}"),
                ft.Divider(height=20, color=ft.Colors.OUTLINE),
                stat_row("Engine", engine),
                stat_row("Configuration Valid", "Yes" if config_valid else "No"),
                stat_row("Validation Errors", str(validation_errors_count)),
            ],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD


class AIDetailDialog(BaseDetailPopup):
    """
    AI service detail popup.

    Displays comprehensive AI service information including provider configuration,
    conversation statistics, and usage metrics.
    """

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize the ai service details popup.

        Args:
            component_data: ComponentStatus containing component health and metrics
        """
        metadata = component_data.metadata or {}

        # Build sections
        sections = [
            OverviewSection(metadata),
            ConfigurationSection(metadata),
            ft.Divider(height=20, color=ft.Colors.OUTLINE),
            StatisticsSection(component_data),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="AI Service",
            sections=sections,
        )
