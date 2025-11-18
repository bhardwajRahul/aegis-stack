"""
Scheduler Detail Modal

Displays comprehensive scheduler component information using component composition.
Each section is a self-contained Flet control that can be reused and tested independently.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    DisplayText,
    H2Text,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from ..cards.card_utils import format_next_run_time, format_schedule_human_readable


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
    """Overview section showing key scheduler metrics."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize overview section.

        Args:
            metadata: Component metadata containing task counts
        """
        super().__init__()

        total_tasks = metadata.get("total_tasks", 0)
        active_tasks = metadata.get("active_tasks", 0)
        paused_tasks = metadata.get("paused_tasks", 0)

        self.content = ft.Column(
            [
                H2Text("Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard(
                            "Total Tasks",
                            str(total_tasks),
                            ft.Icons.SCHEDULE,
                            Theme.Colors.INFO,
                        ),
                        MetricCard(
                            "Active Tasks",
                            str(active_tasks),
                            ft.Icons.PLAY_CIRCLE_OUTLINE,
                            Theme.Colors.SUCCESS,
                        ),
                        MetricCard(
                            "Paused Tasks",
                            str(paused_tasks),
                            ft.Icons.PAUSE_CIRCLE_OUTLINE,
                            Theme.Colors.WARNING,
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class JobItem(ft.Container):
    """Individual scheduled job item display."""

    def __init__(self, task: dict) -> None:
        """
        Initialize job item.

        Args:
            task: Task dictionary with name, next_run, schedule
        """
        super().__init__()

        job_name = task.get("name", task.get("id", "Unknown"))
        next_run = task.get("next_run", "")
        schedule = task.get("schedule", "Unknown schedule")

        next_run_display = format_next_run_time(next_run)
        schedule_display = format_schedule_human_readable(schedule)

        self.content = ft.Row(
            [
                ft.Icon(ft.Icons.SCHEDULE, size=24, color=Theme.Colors.PRIMARY),
                ft.Column(
                    [
                        PrimaryText(
                            job_name,
                            size=Theme.Typography.BODY_LARGE,
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        ),
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ACCESS_TIME,
                                    size=14,
                                    color=Theme.Colors.TEXT_TERTIARY,
                                ),
                                SecondaryText(
                                    f"Next run: {next_run_display}",
                                    size=Theme.Typography.BODY_SMALL,
                                ),
                                SecondaryText("|", size=Theme.Typography.BODY_SMALL),
                                SecondaryText(
                                    schedule_display,
                                    size=Theme.Typography.BODY_SMALL,
                                ),
                            ],
                            spacing=Theme.Spacing.SM,
                        ),
                    ],
                    spacing=Theme.Spacing.XS,
                    expand=True,
                ),
            ],
            spacing=Theme.Spacing.MD,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.OUTLINE_VARIANT)
        self.border_radius = Theme.Components.CARD_RADIUS


class EmptyJobsPlaceholder(ft.Container):
    """Placeholder display when no jobs are scheduled."""

    def __init__(self) -> None:
        """Initialize empty jobs placeholder."""
        super().__init__()

        self.content = ft.Row(
            [
                ft.Icon(
                    ft.Icons.SCHEDULE_OUTLINED,
                    size=48,
                    color=Theme.Colors.TEXT_TERTIARY,
                ),
                SecondaryText(
                    "No scheduled jobs",
                    size=Theme.Typography.BODY_LARGE,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=Theme.Spacing.MD,
        )
        self.padding = Theme.Spacing.XL
        self.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.OUTLINE_VARIANT)
        self.border_radius = Theme.Components.CARD_RADIUS


class JobsSection(ft.Container):
    """Scheduled jobs list section."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize jobs section.

        Args:
            metadata: Component metadata containing upcoming_tasks
        """
        super().__init__()

        upcoming_tasks = metadata.get("upcoming_tasks", [])

        if not upcoming_tasks:
            jobs_content = EmptyJobsPlaceholder()
        else:
            job_items = [JobItem(task) for task in upcoming_tasks]
            jobs_content = ft.Column(job_items, spacing=Theme.Spacing.SM)

        self.content = ft.Column(
            [
                H2Text("Scheduled Jobs"),
                ft.Container(height=Theme.Spacing.SM),
                jobs_content,
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class StatisticsSection(ft.Container):
    """Component statistics and information section."""

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize statistics section.

        Args:
            component_data: Complete component status information
        """
        super().__init__()

        stats = {
            "Component Status": component_data.status.value.title(),
            "Health Message": component_data.message,
            "Response Time": f"{component_data.response_time_ms:.2f}ms"
            if component_data.response_time_ms
            else "N/A",
        }

        stats_rows = []
        for label, value in stats.items():
            stats_rows.append(
                ft.Row(
                    [
                        SecondaryText(
                            f"{label}:",
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            width=150,
                        ),
                        BodyText(value),
                    ],
                    spacing=Theme.Spacing.MD,
                )
            )

        self.content = ft.Column(
            [
                H2Text("Component Information"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(stats_rows, spacing=Theme.Spacing.SM),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class SchedulerDetailDialog(ft.AlertDialog):
    """
    Modal dialog for displaying detailed scheduler information.

    Inherits from ft.AlertDialog and composes custom control components
    to build a complete, self-contained modal experience.
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the scheduler detail modal.

        Args:
            component_data: ComponentStatus containing scheduler health and metrics
        """
        self.component_data = component_data
        metadata = component_data.metadata or {}

        # Build modal content
        title = self._create_title()
        content = ft.Container(
            content=ft.Column(
                [
                    OverviewSection(metadata),
                    ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                    JobsSection(metadata),
                    ft.Divider(height=20, color=Theme.Colors.BORDER_DEFAULT),
                    StatisticsSection(component_data),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=900,
            height=700,
        )

        # Initialize dialog
        super().__init__(
            modal=False,
            title=title,
            content=content,
            actions=[
                ft.TextButton("Close", on_click=self._close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _create_title(self) -> ft.Control:
        """Create the modal title with status indicator."""
        status = self.component_data.status
        if status.value == "healthy":
            status_color = Theme.Colors.SUCCESS
        elif status.value == "info":
            status_color = Theme.Colors.INFO
        elif status.value == "warning":
            status_color = Theme.Colors.WARNING
        else:  # unhealthy
            status_color = Theme.Colors.ERROR

        return ft.Row(
            [
                H2Text("⏰ Scheduler Details"),
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

    def _close(self, e: ft.ControlEvent) -> None:
        """Close the modal dialog."""
        self.open = False
        e.page.update()
