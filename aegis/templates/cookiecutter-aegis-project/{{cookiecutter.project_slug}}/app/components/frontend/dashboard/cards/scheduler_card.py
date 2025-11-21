"""
Stunning Scheduler Component Card

Modern, visually striking card component that displays scheduled jobs,
job statistics, and scheduling information using shared utility functions.
"""

import flet as ft
from app.components.frontend.controls import PrimaryText
from app.components.frontend.controls.tech_badge import TechBadge
from app.services.system.models import ComponentStatus

from .card_container import CardContainer
from .card_utils import (
    create_responsive_3_section_layout,
    create_stats_row,
    format_next_run_time,
    format_schedule_human_readable,
    get_status_colors,
)


class SchedulerCard:
    """
    Visually stunning, wide component card for displaying Scheduler/APScheduler metrics.

    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, jobs, stats)
    - Scheduled job indicators with next run times
    - Job statistics and scheduler status
    - Status-aware coloring and hover effects
    - 800px width for optimal content spacing
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the Scheduler card with component data.

        Args:
            component_data: ComponentStatus containing scheduler health and metrics
        """
        self.component_data = component_data
        self._card_container: ft.Container | None = None

    def _handle_job_hover_simple(self, e: ft.ControlEvent) -> None:
        """Simple hover handler that works with event source."""
        container = e.control
        buttons = container.content.controls[0].controls[2]  # Access the buttons row

        if e.data == "true":  # Mouse enter
            container.border = ft.border.all(1, ft.Colors.GREY_400)
            buttons.opacity = 1.0
        else:  # Mouse leave
            container.border = ft.border.all(1, ft.Colors.TRANSPARENT)
            buttons.opacity = 0.0
        container.update()

    def _create_technology_badge(self) -> ft.Container:
        """Create the Scheduler technology badge section."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return TechBadge(
            title="APScheduler",
            subtitle="Task Scheduling",
            badge_text="Jobs",
            badge_color=ft.Colors.TEAL,
            primary_color=primary_color,
            width=160,
        )

    def _create_jobs_section(self) -> ft.Container:
        """Create the scheduled jobs section with job list."""
        # Get real scheduled jobs from component metadata
        upcoming_tasks = []
        if (
            self.component_data.metadata
            and "upcoming_tasks" in self.component_data.metadata
        ):
            upcoming_tasks = self.component_data.metadata["upcoming_tasks"]

        job_list_items = []
        for task in upcoming_tasks:
            # Format next run time
            next_run_display = format_next_run_time(task.get("next_run", ""))
            schedule = task.get("schedule", "Unknown schedule")

            job_list_items.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.SCHEDULE, size=16, color=ft.Colors.GREY
                                    ),
                                    ft.Text(
                                        task.get("name", task.get("id", "Unknown")),
                                        size=15,
                                        weight=ft.FontWeight.W_500,
                                        color=ft.Colors.ON_SURFACE,
                                        expand=True,
                                    ),
                                    ft.Row(
                                        [
                                            ft.IconButton(
                                                icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
                                                icon_size=16,
                                                icon_color=ft.Colors.GREY,
                                                tooltip="Pause job",
                                                on_click=lambda _: None,
                                                style=ft.ButtonStyle(
                                                    padding=ft.padding.all(2),
                                                ),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                icon_size=16,
                                                icon_color=ft.Colors.GREY,
                                                tooltip="Delete job",
                                                on_click=lambda _: None,
                                                style=ft.ButtonStyle(
                                                    padding=ft.padding.all(2),
                                                ),
                                            ),
                                        ],
                                        spacing=0,
                                        opacity=0.0,  # Hidden by default
                                    ),
                                ],
                                spacing=8,
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row(
                                [
                                    ft.Text(
                                        next_run_display,
                                        size=12,
                                        color=ft.Colors.GREY,
                                    ),
                                    ft.Text("|", size=12, color=ft.Colors.GREY),
                                    ft.Text(
                                        format_schedule_human_readable(schedule),
                                        size=12,
                                        color=ft.Colors.GREY,
                                    ),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=ft.padding.symmetric(vertical=2, horizontal=8),
                    border=ft.border.all(1, ft.Colors.TRANSPARENT),
                    border_radius=8,
                    on_hover=self._handle_job_hover_simple,
                )
            )

        # Add placeholder if no jobs
        if not job_list_items:
            job_list_items.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.SCHEDULE_OUTLINED,
                                size=20,
                                color=ft.Colors.GREY,
                            ),
                            ft.Text("No active jobs", color=ft.Colors.GREY),
                        ],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.all(20),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY),
                    border_radius=12,
                )
            )

        return ft.Container(
            content=ft.Container(
                content=ft.Column(
                    job_list_items,
                    spacing=2,
                    scroll=ft.ScrollMode.AUTO,
                ),
                height=250,  # Fixed height to force scrolling
                padding=ft.padding.all(
                    0
                ),  # Remove any default padding from inner container
            ),
            width=400,  # Section width
            padding=ft.padding.only(left=12, right=12, bottom=12, top=0),
            alignment=ft.alignment.top_left,
        )

    def _create_stats_section(self) -> ft.Container:
        """Create the scheduler statistics section."""
        # Get real scheduler stats from component metadata
        metadata = self.component_data.metadata or {}

        total_tasks = str(metadata.get("total_tasks", 0))
        active_tasks = str(metadata.get("active_tasks", 0))
        paused_tasks = str(metadata.get("paused_tasks", 0))

        # Get next job info
        upcoming_tasks = metadata.get("upcoming_tasks", [])
        next_job = "None"
        if upcoming_tasks:
            next_job = format_next_run_time(upcoming_tasks[0].get("next_run", ""))

        scheduler_stats = {
            "Total Tasks": total_tasks,
            "Active Tasks": active_tasks,
            "Paused Tasks": paused_tasks,
            "Next Task": next_job,
        }

        stats_content = [
            PrimaryText("Task Statistics"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
        ]

        # Add all stats using the utility function
        for stat_name, stat_value in scheduler_stats.items():
            stats_content.append(create_stats_row(stat_name, stat_value))

        # Add scheduler status
        stats_content.extend(
            [
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                create_stats_row(
                    "Status",
                    self.component_data.status.value.title(),
                    get_status_colors(self.component_data)[0],
                ),
            ]
        )

        return ft.Container(
            content=ft.Column(
                stats_content,
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.padding.all(16),
            width=240,  # Stats section width
            alignment=ft.alignment.top_left,
        )

    def build(self) -> ft.Container:
        """Build and return the complete Scheduler card with responsive layout."""
        primary_color, background_color, border_color = get_status_colors(
            self.component_data
        )

        # Use shared responsive 3-section layout prioritizing middle section
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_jobs_section(),
            right_content=self._create_stats_section(),
        )

        return CardContainer(
            content=content,
            border_color=border_color,
            component_data=self.component_data,
            component_name="scheduler",
        )
