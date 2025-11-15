"""
Scheduler Detail Modal

Displays comprehensive scheduler component information using component composition.
Each section is a self-contained Flet control that can be reused and tested independently.
"""

import flet as ft
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
                ft.Text(
                    value,
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Text(
                    label,
                    size=12,
                    color=ft.Colors.GREY_600,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )
        self.padding = 20
        self.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.GREY)
        self.border_radius = 12
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
                ft.Text(
                    "Overview",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Container(height=10),
                ft.Row(
                    [
                        MetricCard(
                            "Total Tasks",
                            str(total_tasks),
                            ft.Icons.SCHEDULE,
                            ft.Colors.BLUE,
                        ),
                        MetricCard(
                            "Active Tasks",
                            str(active_tasks),
                            ft.Icons.PLAY_CIRCLE_OUTLINE,
                            ft.Colors.GREEN,
                        ),
                        MetricCard(
                            "Paused Tasks",
                            str(paused_tasks),
                            ft.Icons.PAUSE_CIRCLE_OUTLINE,
                            ft.Colors.ORANGE,
                        ),
                    ],
                    spacing=20,
                ),
            ],
            spacing=0,
        )
        self.padding = 20


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
                ft.Icon(ft.Icons.SCHEDULE, size=24, color=ft.Colors.TEAL),
                ft.Column(
                    [
                        ft.Text(
                            job_name,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_SURFACE,
                        ),
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ACCESS_TIME,
                                    size=14,
                                    color=ft.Colors.GREY,
                                ),
                                ft.Text(
                                    f"Next run: {next_run_display}",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Text("|", size=12, color=ft.Colors.GREY),
                                ft.Text(
                                    schedule_display,
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            spacing=16,
        )
        self.padding = 16
        self.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.GREY)
        self.border_radius = 12


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
                    color=ft.Colors.GREY,
                ),
                ft.Text(
                    "No scheduled jobs",
                    size=16,
                    color=ft.Colors.GREY,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        self.padding = 40
        self.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.GREY)
        self.border_radius = 12


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
            jobs_content = ft.Column(job_items, spacing=12)

        self.content = ft.Column(
            [
                ft.Text(
                    "Scheduled Jobs",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Container(height=10),
                jobs_content,
            ],
            spacing=0,
        )
        self.padding = 20


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
                        ft.Text(
                            f"{label}:",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.GREY_700,
                            width=150,
                        ),
                        ft.Text(
                            value,
                            size=14,
                            color=ft.Colors.ON_SURFACE,
                        ),
                    ],
                    spacing=20,
                )
            )

        self.content = ft.Column(
            [
                ft.Text(
                    "Component Information",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Container(height=10),
                ft.Column(stats_rows, spacing=12),
            ],
            spacing=0,
        )
        self.padding = 20


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
        super().__init__()

        self.component_data = component_data
        metadata = component_data.metadata or {}

        # Configure dialog properties
        self.modal = True
        self.title = self._create_title()
        self.content = ft.Container(
            content=ft.Column(
                [
                    OverviewSection(metadata),
                    ft.Divider(height=20, color=ft.Colors.GREY_300),
                    JobsSection(metadata),
                    ft.Divider(height=20, color=ft.Colors.GREY_300),
                    StatisticsSection(component_data),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=900,
            height=700,
        )
        self.actions = [
            ft.TextButton("Close", on_click=self._close),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def _create_title(self) -> ft.Control:
        """Create the modal title with status indicator."""
        status = self.component_data.status
        if status.value == "healthy":
            status_color = ft.Colors.GREEN
        elif status.value == "info":
            status_color = ft.Colors.BLUE
        elif status.value == "warning":
            status_color = ft.Colors.ORANGE
        else:  # unhealthy
            status_color = ft.Colors.RED

        return ft.Row(
            [
                ft.Text(
                    "⏰ Scheduler Details",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Container(
                    content=ft.Text(
                        status.value.upper(),
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.WHITE,
                    ),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=status_color,
                    border_radius=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _close(self, e: ft.ControlEvent) -> None:
        """Close the modal dialog."""
        self.open = False
        e.page.update()
