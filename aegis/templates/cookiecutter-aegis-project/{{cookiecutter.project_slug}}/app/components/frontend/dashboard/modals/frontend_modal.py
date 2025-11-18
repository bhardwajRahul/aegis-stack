"""
Frontend Detail Modal

Displays comprehensive frontend framework information including Flet capabilities,
configuration, and integration status.
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
    """Overview section showing key frontend metrics."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize overview section.

        Args:
            metadata: Component metadata containing frontend information
        """
        super().__init__()

        framework = metadata.get("framework", "Flet")
        version = metadata.get("version", "Unknown")
        integration = metadata.get("integration", "FastAPI")
        theme_support = metadata.get("theme_support", "Light / Dark")

        self.content = ft.Column(
            [
                H2Text("Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard(
                            "Framework",
                            f"{framework} {version}",
                            ft.Icons.WEB,
                            Theme.Colors.PRIMARY,
                        ),
                        MetricCard(
                            "Integration",
                            integration,
                            ft.Icons.LINK,
                            Theme.Colors.SUCCESS,
                        ),
                        MetricCard(
                            "Theme",
                            theme_support,
                            ft.Icons.PALETTE,
                            Theme.Colors.INFO,
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class ConfigurationSection(ft.Container):
    """Configuration section showing framework settings and details."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize configuration section.

        Args:
            metadata: Component metadata containing configuration
        """
        super().__init__()

        framework = metadata.get("framework", "Flet")
        version = metadata.get("version", "Unknown")
        integration = metadata.get("integration", "FastAPI")
        ui_type = metadata.get("ui_type", "Reactive Web")
        platform = metadata.get("platform", "Cross-platform")
        components = metadata.get("components", "Material 3")
        theme_support = metadata.get("theme_support", "Light / Dark")
        auto_refresh = metadata.get("auto_refresh", 30)

        # Build configuration rows
        config_rows = []

        # Framework row with badge
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Framework:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    ft.Container(
                        content=ft.Text(
                            f"{framework} {version}",
                            size=Theme.Typography.BODY_SMALL,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
                        ),
                        bgcolor=Theme.Colors.PRIMARY,
                        border_radius=Theme.Components.BADGE_RADIUS,
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Integration Type row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Integration Type:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(f"{integration} integrated"),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # UI Type row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "UI Type:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(ui_type),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Platform row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Platform:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(platform),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Components row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Components:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(components),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Theme Support row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Theme Support:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(f"{theme_support} available"),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Auto Refresh row
        config_rows.append(
            ft.Row(
                [
                    SecondaryText(
                        "Auto Refresh:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=200,
                    ),
                    BodyText(f"Every {auto_refresh} seconds"),
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


class CapabilitiesSection(ft.Container):
    """Capabilities section showing frontend features and capabilities."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize capabilities section.

        Args:
            metadata: Component metadata containing capability information
        """
        super().__init__()

        # Build capability rows
        capability_rows = []

        # Material Design 3
        capability_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color=Theme.Colors.SUCCESS),
                    BodyText("Material Design 3"),
                ],
                spacing=Theme.Spacing.SM,
            )
        )

        # Theme Switching
        capability_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color=Theme.Colors.SUCCESS),
                    BodyText("Theme Switching (Light/Dark)"),
                ],
                spacing=Theme.Spacing.SM,
            )
        )

        # Auto Refresh
        auto_refresh = metadata.get("auto_refresh", 30)
        capability_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color=Theme.Colors.SUCCESS),
                    BodyText(f"Auto Refresh ({auto_refresh}s)"),
                ],
                spacing=Theme.Spacing.SM,
            )
        )

        # Reactive UI Updates
        capability_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color=Theme.Colors.SUCCESS),
                    BodyText("Reactive UI Updates"),
                ],
                spacing=Theme.Spacing.SM,
            )
        )

        # Cross-platform Rendering
        capability_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color=Theme.Colors.SUCCESS),
                    BodyText("Cross-platform Rendering"),
                ],
                spacing=Theme.Spacing.SM,
            )
        )

        # FastAPI Integration
        integration = metadata.get("integration", "FastAPI")
        capability_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color=Theme.Colors.SUCCESS),
                    BodyText(f"{integration} Integration"),
                ],
                spacing=Theme.Spacing.SM,
            )
        )

        self.content = ft.Column(
            [
                H2Text("Capabilities"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(capability_rows, spacing=Theme.Spacing.SM),
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
        backend_dep = dependencies.get("backend", "Available")

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
                stat_row("Backend Integration", backend_dep),
            ],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD


class FrontendDetailDialog(ft.AlertDialog):
    """
    Frontend detail modal dialog.

    Displays comprehensive frontend framework information including Flet capabilities,
    configuration, and integration status.
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize frontend detail dialog.

        Args:
            component_data: Frontend ComponentStatus from health check
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
                H2Text("🎨 Frontend Details"),
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
                    CapabilitiesSection(metadata),
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
