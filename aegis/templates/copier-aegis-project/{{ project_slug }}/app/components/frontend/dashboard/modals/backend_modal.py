"""
Backend Detail Modal

Displays comprehensive backend/FastAPI information including routes,
middleware stack, system metrics, and configuration details.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    DisplayText,
    H2Text,
    LabelText,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus, ComponentStatusType

from ..cards.card_utils import create_progress_indicator

# Route section column widths (pixels)
COL_WIDTH_PATH = 300
COL_WIDTH_METHODS = 150
COL_WIDTH_TAGS = 150
COL_WIDTH_NAME = 200

# Middleware section column widths (pixels)
COL_WIDTH_ORDER = 60
COL_WIDTH_TYPE = 250
COL_WIDTH_MODULE = 300
COL_WIDTH_SECURITY = 100


class MetricCard(ft.Container):
    """Reusable metric card component for backend statistics."""

    def __init__(self, icon: str, value: str, label: str, color: str) -> None:
        """
        Initialize metric card.

        Args:
            icon: Icon emoji or text
            value: Metric value to display
            label: Metric label text
            color: Icon background color
        """
        super().__init__()
        self.content = ft.Column(
            [
                ft.Container(
                    content=ft.Text(icon, size=32),
                    padding=ft.padding.all(8),
                    bgcolor=color,
                    border_radius=8,
                    width=48,
                    height=48,
                    alignment=ft.alignment.center,
                ),
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
    """Backend overview section with key metrics."""

    def __init__(self, backend_component: ComponentStatus) -> None:
        """
        Initialize overview section.

        Args:
            backend_component: ComponentStatus containing backend data
        """
        super().__init__()
        metadata = backend_component.metadata or {}

        # Extract metrics
        total_routes = metadata.get("total_routes", 0)
        total_endpoints = metadata.get("total_endpoints", 0)
        total_middleware = metadata.get("total_middleware", 0)
        security_count = metadata.get("security_count", 0)
        deprecated_count = metadata.get("deprecated_count", 0)
        method_counts = metadata.get("method_counts", {})

        # Build metric cards
        metric_cards = [
            MetricCard(
                icon="🛣️",
                value=str(total_routes),
                label="Total Routes",
                color=ft.Colors.BLUE,
            ),
            MetricCard(
                icon="🎯",
                value=str(total_endpoints),
                label="Endpoints",
                color=ft.Colors.GREEN,
            ),
            MetricCard(
                icon="🔧",
                value=str(total_middleware),
                label="Middleware",
                color=ft.Colors.PURPLE,
            ),
            MetricCard(
                icon="🔒",
                value=str(security_count),
                label="Security Layers",
                color=ft.Colors.AMBER,
            ),
        ]

        # Add deprecated count if any
        if deprecated_count > 0:
            metric_cards.append(
                MetricCard(
                    icon="⚠️",
                    value=str(deprecated_count),
                    label="Deprecated",
                    color=ft.Colors.ORANGE,
                )
            )

        # Method distribution
        method_text = ", ".join(
            [f"{count} {method}" for method, count in method_counts.items()]
        )

        self.content = ft.Column(
            [
                H2Text("Overview"),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Row(
                    metric_cards,
                    spacing=Theme.Spacing.MD,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            SecondaryText("HTTP Methods:"),
                            BodyText(method_text or "None"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.padding.symmetric(
                        horizontal=Theme.Spacing.MD, vertical=Theme.Spacing.SM
                    ),
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.all(Theme.Spacing.MD)


class RouteCard(ft.Container):
    """Expandable card for displaying route details."""

    def __init__(self, route_info: dict[str, object]) -> None:
        """
        Initialize route card.

        Args:
            route_info: Dictionary containing route information
        """
        super().__init__()
        self.route_info = route_info
        self.is_expanded = False

        # Extract route data
        self.path = str(route_info.get("path", ""))
        self.methods = list(route_info.get("methods", []))
        self.name = str(route_info.get("name", ""))
        self.summary = str(route_info.get("summary", ""))
        self.description = str(route_info.get("description", ""))
        self.tags = list(route_info.get("tags", []))
        self.deprecated = bool(route_info.get("deprecated", False))
        self.path_params = list(route_info.get("path_params", []))
        self.dependencies = route_info.get("dependencies", 0)
        self.response_model = str(route_info.get("response_model", ""))

        # Create method badges
        method_badges = []
        method_colors = {
            "GET": ft.Colors.BLUE,
            "POST": ft.Colors.GREEN,
            "PUT": ft.Colors.ORANGE,
            "PATCH": ft.Colors.PURPLE,
            "DELETE": ft.Colors.RED,
        }
        for method in self.methods:
            method_badges.append(
                ft.Container(
                    content=LabelText(
                        method,
                        color=Theme.Colors.BADGE_TEXT,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    bgcolor=method_colors.get(method, ft.Colors.GREY),
                    border_radius=4,
                )
            )

        # Create tag badges
        tag_badges = []
        for tag in self.tags:
            tag_badges.append(
                ft.Container(
                    content=LabelText(
                        tag,
                        color=Theme.Colors.BADGE_TEXT,
                    ),
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    bgcolor=ft.Colors.GREY_700,
                    border_radius=4,
                )
            )

        # Create header (using GestureDetector for click handling)
        self.header = ft.GestureDetector(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.ARROW_RIGHT,
                            size=16,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Container(
                            content=PrimaryText(self.path),
                            expand=True,
                        ),
                        ft.Row(
                            method_badges,
                            spacing=4,
                        ),
                        ft.Row(
                            tag_badges,
                            spacing=4,
                        ),
                        ft.Icon(
                            ft.Icons.WARNING,
                            size=16,
                            color=ft.Colors.ORANGE,
                            visible=self.deprecated,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.all(Theme.Spacing.SM),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
            ),
            on_tap=self._toggle_expand,
            mouse_cursor=ft.MouseCursor.CLICK,
        )

        # Create expandable details
        detail_rows = [
            ft.Row(
                [
                    SecondaryText("Endpoint Name:"),
                    BodyText(self.name or "N/A"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        ]

        if self.summary:
            detail_rows.append(
                ft.Row(
                    [
                        SecondaryText("Summary:"),
                        BodyText(self.summary),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        if self.description:
            detail_rows.append(
                ft.Column(
                    [
                        SecondaryText("Description:"),
                        BodyText(self.description),
                    ],
                    spacing=4,
                )
            )

        if self.path_params:
            detail_rows.append(
                ft.Row(
                    [
                        SecondaryText("Path Parameters:"),
                        BodyText(", ".join(self.path_params)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        detail_rows.append(
            ft.Row(
                [
                    SecondaryText("Dependencies:"),
                    BodyText(str(self.dependencies)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

        if self.response_model:
            detail_rows.append(
                ft.Row(
                    [
                        SecondaryText("Response Model:"),
                        BodyText(self.response_model),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        if self.deprecated:
            detail_rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.WARNING, size=16, color=ft.Colors.ORANGE),
                            SecondaryText("This route is deprecated"),
                        ],
                        spacing=4,
                    ),
                    bgcolor=ft.Colors.ORANGE_50,
                    padding=ft.padding.all(8),
                    border_radius=4,
                )
            )

        self.details = ft.Container(
            content=ft.Column(
                detail_rows,
                spacing=Theme.Spacing.SM,
            ),
            padding=ft.padding.all(Theme.Spacing.MD),
            bgcolor=ft.Colors.SURFACE,
            border_radius=8,
            visible=False,
        )

        # Main content
        self.content = ft.Column(
            [self.header, self.details],
            spacing=Theme.Spacing.XS,
        )
        self.padding = ft.padding.symmetric(
            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
        )

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        """Toggle expansion state."""
        self.is_expanded = not self.is_expanded
        self.details.visible = self.is_expanded

        # Update arrow icon - navigate: GestureDetector → Container → Row → Icon
        if isinstance(e.control, ft.GestureDetector):
            gesture_detector = e.control
            if isinstance(gesture_detector.content, ft.Container):
                container = gesture_detector.content
                if isinstance(container.content, ft.Row):
                    row = container.content
                    if len(row.controls) > 0 and isinstance(row.controls[0], ft.Icon):
                        arrow_icon = row.controls[0]
                        arrow_icon.name = (
                            ft.Icons.ARROW_DROP_DOWN
                            if self.is_expanded
                            else ft.Icons.ARROW_RIGHT
                        )

        self.update()


class RoutesSection(ft.Container):
    """Routes section displaying all backend routes."""

    def __init__(self, backend_component: ComponentStatus) -> None:
        """
        Initialize routes section.

        Args:
            backend_component: ComponentStatus containing backend data
        """
        super().__init__()
        metadata = backend_component.metadata or {}
        routes = metadata.get("routes", [])

        # Create route cards
        route_cards = []
        for route in routes:
            route_cards.append(RouteCard(route))

        # Build section
        self.content = ft.Column(
            [
                H2Text(f"Routes ({len(routes)})"),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Container(
                    content=ft.Column(
                        route_cards
                        if route_cards
                        else [SecondaryText("No routes found")],
                        spacing=Theme.Spacing.XS,
                    ),
                    padding=ft.padding.symmetric(vertical=Theme.Spacing.SM),
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.all(Theme.Spacing.MD)


class MiddlewareCard(ft.Container):
    """Expandable card for displaying middleware details."""

    def __init__(self, middleware_info: dict[str, object]) -> None:
        """
        Initialize middleware card.

        Args:
            middleware_info: Dictionary containing middleware information
        """
        super().__init__()
        self.middleware_info = middleware_info
        self.is_expanded = False

        # Extract middleware data
        self.order = middleware_info.get("order", 0)
        self.type_name = str(middleware_info.get("type", ""))
        self.module = str(middleware_info.get("module", ""))
        self.is_security = bool(middleware_info.get("is_security", False))
        self.config = middleware_info.get("config", {})

        # Create header (using GestureDetector for click handling)
        self.header = ft.GestureDetector(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.ARROW_RIGHT,
                            size=16,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Container(
                            content=LabelText(str(self.order)),
                            width=40,
                        ),
                        ft.Container(
                            content=PrimaryText(self.type_name),
                            expand=2,
                        ),
                        ft.Container(
                            content=SecondaryText(self.module),
                            expand=3,
                        ),
                        ft.Container(
                            content=LabelText(
                                "🔒 Security",
                                color=Theme.Colors.BADGE_TEXT,
                            ),
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            bgcolor=ft.Colors.AMBER,
                            border_radius=4,
                            visible=self.is_security,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.all(Theme.Spacing.SM),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
            ),
            on_tap=self._toggle_expand,
            mouse_cursor=ft.MouseCursor.CLICK,
        )

        # Create expandable config details
        config_rows = []
        if self.config:
            for key, value in self.config.items():
                config_rows.append(
                    ft.Row(
                        [
                            SecondaryText(f"{key}:"),
                            BodyText(str(value)),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
        else:
            config_rows.append(SecondaryText("No configuration available"))

        self.details = ft.Container(
            content=ft.Column(
                config_rows,
                spacing=Theme.Spacing.SM,
            ),
            padding=ft.padding.all(Theme.Spacing.MD),
            bgcolor=ft.Colors.SURFACE,
            border_radius=8,
            visible=False,
        )

        # Main content
        self.content = ft.Column(
            [self.header, self.details],
            spacing=Theme.Spacing.XS,
        )
        self.padding = ft.padding.symmetric(
            horizontal=Theme.Spacing.SM, vertical=Theme.Spacing.XS
        )

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        """Toggle expansion state."""
        self.is_expanded = not self.is_expanded
        self.details.visible = self.is_expanded

        # Update arrow icon - navigate: GestureDetector → Container → Row → Icon
        if isinstance(e.control, ft.GestureDetector):
            gesture_detector = e.control
            if isinstance(gesture_detector.content, ft.Container):
                container = gesture_detector.content
                if isinstance(container.content, ft.Row):
                    row = container.content
                    if len(row.controls) > 0 and isinstance(row.controls[0], ft.Icon):
                        arrow_icon = row.controls[0]
                        arrow_icon.name = (
                            ft.Icons.ARROW_DROP_DOWN
                            if self.is_expanded
                            else ft.Icons.ARROW_RIGHT
                        )

        self.update()


class MiddlewareSection(ft.Container):
    """Middleware section displaying full middleware stack."""

    def __init__(self, backend_component: ComponentStatus) -> None:
        """
        Initialize middleware section.

        Args:
            backend_component: ComponentStatus containing backend data
        """
        super().__init__()
        metadata = backend_component.metadata or {}
        middleware_stack = metadata.get("middleware_stack", [])

        # Create middleware cards
        middleware_cards = []
        for middleware in middleware_stack:
            middleware_cards.append(MiddlewareCard(middleware))

        # Build section
        self.content = ft.Column(
            [
                H2Text(f"Middleware Stack ({len(middleware_stack)})"),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Container(
                    content=ft.Column(
                        middleware_cards
                        if middleware_cards
                        else [SecondaryText("No middleware found")],
                        spacing=Theme.Spacing.XS,
                    ),
                    padding=ft.padding.symmetric(vertical=Theme.Spacing.SM),
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.all(Theme.Spacing.MD)


class SystemMetricsSection(ft.Container):
    """System metrics section showing CPU, memory, and disk usage."""

    def __init__(self, backend_component: ComponentStatus) -> None:
        """
        Initialize system metrics section.

        Args:
            backend_component: ComponentStatus containing backend data
        """
        super().__init__()
        sub_components = backend_component.sub_components or {}

        # Extract system metrics from sub_components
        cpu_data = sub_components.get("cpu")
        memory_data = sub_components.get("memory")
        disk_data = sub_components.get("disk")

        metrics = []

        # CPU metric
        if cpu_data and cpu_data.metadata:
            cpu_percent = cpu_data.metadata.get("percent_used", 0.0)
            cpu_cores = cpu_data.metadata.get("core_count", 0)
            cpu_color = self._get_metric_color(cpu_percent)
            metrics.append(
                create_progress_indicator(
                    label=f"CPU Usage ({cpu_cores} cores)",
                    value=cpu_percent,
                    details=f"{cpu_percent:.1f}%",
                    color=cpu_color,
                )
            )

        # Memory metric
        if memory_data and memory_data.metadata:
            memory_percent = memory_data.metadata.get("percent_used", 0.0)
            memory_total = memory_data.metadata.get("total_gb", 0.0)
            memory_available = memory_data.metadata.get("available_gb", 0.0)
            memory_used = memory_total - memory_available
            memory_color = self._get_metric_color(memory_percent)
            metrics.append(
                create_progress_indicator(
                    label="Memory Usage",
                    value=memory_percent,
                    details=f"{memory_used:.1f} / {memory_total:.1f} GB",
                    color=memory_color,
                )
            )

        # Disk metric
        if disk_data and disk_data.metadata:
            disk_percent = disk_data.metadata.get("percent_used", 0.0)
            disk_free = disk_data.metadata.get("free_gb", 0.0)
            disk_total = disk_data.metadata.get("total_gb", 0.0)
            disk_color = self._get_metric_color(disk_percent)
            metrics.append(
                create_progress_indicator(
                    label="Disk Usage",
                    value=disk_percent,
                    details=f"{disk_free:.1f} GB free / {disk_total:.1f} GB",
                    color=disk_color,
                )
            )

        # Build section
        self.content = ft.Column(
            [
                H2Text("System Metrics"),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Container(
                    content=ft.Column(
                        metrics if metrics else [SecondaryText("No metrics available")],
                        spacing=Theme.Spacing.MD,
                    ),
                    padding=ft.padding.symmetric(vertical=Theme.Spacing.SM),
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.all(Theme.Spacing.MD)

    def _get_metric_color(self, percent: float) -> str:
        """Get color based on metric percentage."""
        if percent >= 90:
            return ft.Colors.RED
        elif percent >= 70:
            return ft.Colors.ORANGE
        else:
            return ft.Colors.GREEN


class BackendDetailDialog(ft.AlertDialog):
    """
    Comprehensive backend detail modal.

    Displays routes, middleware stack, system metrics, and configuration
    details for the FastAPI backend component.
    """

    def __init__(self, backend_component: ComponentStatus) -> None:
        """
        Initialize backend detail dialog.

        Args:
            backend_component: ComponentStatus containing backend data
        """
        # Get status badge
        status_badge = self._create_status_badge(backend_component.status)

        # Create sections
        overview = OverviewSection(backend_component)
        routes = RoutesSection(backend_component)
        middleware = MiddlewareSection(backend_component)
        system_metrics = SystemMetricsSection(backend_component)

        # Build scrollable content
        content = ft.Container(
            content=ft.Column(
                [overview, routes, middleware, system_metrics],
                spacing=Theme.Spacing.LG,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=900,
            height=700,
        )

        super().__init__(
            modal=False,
            title=ft.Row(
                [
                    ft.Text("Backend Details", size=24, weight=ft.FontWeight.BOLD),
                    status_badge,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=content,
            actions=[
                ft.TextButton("Close", on_click=self._close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _create_status_badge(self, status: ComponentStatusType) -> ft.Container:
        """Create status badge for dialog title."""
        status_colors = {
            ComponentStatusType.HEALTHY: (ft.Colors.GREEN, "Healthy"),
            ComponentStatusType.INFO: (ft.Colors.BLUE, "Info"),
            ComponentStatusType.WARNING: (ft.Colors.ORANGE, "Warning"),
            ComponentStatusType.UNHEALTHY: (ft.Colors.RED, "Unhealthy"),
        }

        color, text = status_colors.get(status, (ft.Colors.GREY, "Unknown"))

        return ft.Container(
            content=LabelText(text, color=Theme.Colors.BADGE_TEXT),
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
            bgcolor=color,
            border_radius=12,
        )

    def _close_dialog(self, e: ft.ControlEvent) -> None:
        """Close the dialog."""
        if e.page:
            e.page.close(self)
