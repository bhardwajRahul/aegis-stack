"""
Scheduler Detail Modal

Displays comprehensive scheduler component information using composition.
Each section is self-contained and can be reused and tested independently.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from ..cards.card_utils import format_next_run_time, format_schedule_human_readable
from .base_detail_popup import BaseDetailPopup
from .modal_constants import ModalLayout
from .modal_sections import MetricCard


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

        # Create metric cards directly
        self.content = ft.Row(
            [
                MetricCard(
                    "Total Tasks",
                    str(total_tasks),
                    Theme.Colors.INFO,
                ),
                MetricCard(
                    "Active Tasks",
                    str(active_tasks),
                    Theme.Colors.SUCCESS,
                ),
                MetricCard(
                    "Paused Tasks",
                    str(paused_tasks),
                    Theme.Colors.WARNING,
                ),
            ],
            spacing=Theme.Spacing.MD,
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

        self.content = ft.Column(
            [
                PrimaryText(
                    job_name,
                    size=Theme.Typography.BODY_LARGE,
                    weight=Theme.Typography.WEIGHT_SEMIBOLD,
                ),
                ft.Row(
                    [
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
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.SURFACE
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(1, ft.Colors.OUTLINE)


class EmptyJobsPlaceholder(ft.Container):
    """Placeholder display when no jobs are scheduled."""

    def __init__(self) -> None:
        """Initialize empty jobs placeholder."""
        super().__init__()

        self.content = ft.Row(
            [
                SecondaryText(
                    "No scheduled jobs",
                    size=Theme.Typography.BODY_LARGE,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=Theme.Spacing.MD,
        )
        self.padding = Theme.Spacing.XL
        self.bgcolor = ft.Colors.SURFACE
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(1, ft.Colors.OUTLINE)


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
                H3Text("Scheduled Jobs"),
                ft.Container(height=Theme.Spacing.SM),
                jobs_content,
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class StatisticsSection(ft.Container):
    """Component statistics and information section."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
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
                H3Text("Component Information"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(stats_rows, spacing=Theme.Spacing.SM),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class SchedulerDetailDialog(BaseDetailPopup):
    """
    Modal dialog for displaying detailed scheduler information.

    Inherits from BaseDetailDialog for consistent modal structure.
    Custom sections provide scheduler-specific content.
    """

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize the scheduler detail popup.

        Args:
            component_data: ComponentStatus containing scheduler health and metrics
        """
        metadata = component_data.metadata or {}

        # Build sections
        sections = [
            OverviewSection(metadata),
            JobsSection(metadata),
            ft.Divider(
                height=ModalLayout.SECTION_DIVIDER_HEIGHT, color=ft.Colors.OUTLINE
            ),
            StatisticsSection(component_data, page),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Scheduler",
            sections=sections,
        )
