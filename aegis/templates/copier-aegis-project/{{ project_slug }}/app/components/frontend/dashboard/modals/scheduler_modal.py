"""
Scheduler Detail Modal

Displays comprehensive scheduler component information using composition.
Each section is self-contained and can be reused and tested independently.
"""

import flet as ft
from app.components.frontend.controls import (
    DataTableColumn,
    ExpandableDataTable,
    ExpandableRow,
    SecondaryText,
    TableCellText,
    TableNameText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from ..cards.card_utils import (
    format_next_run_time,
    format_schedule_human_readable,
    get_status_detail,
)
from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard


class MiniMetricCard(ft.Container):
    """Compact metric card for use in expanded row content."""

    def __init__(self, label: str, value: str, color: str) -> None:
        super().__init__()

        self.content = ft.Column(
            [
                SecondaryText(label, size=10),
                ft.Text(value, size=16, weight=ft.FontWeight.W_600, color=color),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.padding = ft.padding.symmetric(horizontal=12, vertical=8)
        self.bgcolor = ft.Colors.SURFACE
        self.border_radius = 6
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
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


def _get_mock_job_stats(job_id: str) -> dict:
    """Get mock statistics for a job (placeholder until milestone 21).

    Args:
        job_id: Job identifier

    Returns:
        Mock statistics dict
    """
    # Mock data - will be replaced with real API calls
    return {
        "success_rate": 98.5,
        "total_runs": 142,
        "avg_duration_ms": 1200,
        "last_run": "2m ago",
        "last_status": "success",
    }


def _get_mock_recent_executions(job_id: str) -> list[dict]:
    """Get mock recent executions for a job (placeholder until milestone 21).

    Args:
        job_id: Job identifier

    Returns:
        Mock executions list
    """
    # Mock data - will be replaced with real API calls
    return [
        {"time": "2m ago", "duration": "1.1s", "status": "success", "error": None},
        {"time": "1d 2h ago", "duration": "1.3s", "status": "success", "error": None},
        {
            "time": "2d 2h ago",
            "duration": "0.8s",
            "status": "failed",
            "error": "Connection timeout",
        },
    ]


def _format_duration(ms: int) -> str:
    """Format milliseconds to human readable duration."""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        return f"{ms / 60000:.1f}m"


def _build_job_expanded_content(task: dict) -> ft.Control:
    """Build expanded content for a scheduled job.

    Args:
        task: Task dictionary with job details

    Returns:
        Column with job info, stats, history, and action buttons
    """
    function = task.get("function", "Unknown")
    description = task.get("description")
    # Hidden for now - will be used when action buttons are enabled
    # job_id = task.get("id", task.get("job_id", "Unknown"))
    # status = task.get("status", "active")

    # Get mock data (will be replaced with API calls) - hidden for now
    # stats = _get_mock_job_stats(job_id)
    # recent = _get_mock_recent_executions(job_id)

    content: list[ft.Control] = []

    # === Section 1: Job Info ===
    if description:
        content.append(
            ft.Text(
                description,
                size=Theme.Typography.BODY,
                italic=True,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )

    content.append(
        SecondaryText(f"Function: {function}", size=Theme.Typography.BODY_SMALL)
    )
    content.append(ft.Container(height=Theme.Spacing.MD))

    # === Work in Progress Notice (hidden for now) ===
    # wip_notice = ft.Container(
    #     content=ft.Row(
    #         [
    #             ft.Icon(ft.Icons.CONSTRUCTION, size=16, color=ft.Colors.ORANGE_900),
    #             ft.Text(
    #                 "Work in progress - data below is placeholder, not real execution history",
    #                 size=12,
    #                 color=ft.Colors.ORANGE_900,
    #             ),
    #         ],
    #         spacing=8,
    #     ),
    #     bgcolor=ft.Colors.ORANGE_100,
    #     padding=ft.padding.symmetric(horizontal=12, vertical=8),
    #     border_radius=6,
    # )
    # content.append(wip_notice)
    # content.append(ft.Container(height=Theme.Spacing.MD))

    # === Section 2: Stats Row (hidden for now) ===
    # success_rate = stats["success_rate"]
    # rate_color = (
    #     Theme.Colors.SUCCESS
    #     if success_rate >= 95
    #     else Theme.Colors.WARNING
    #     if success_rate >= 80
    #     else Theme.Colors.ERROR
    # )
    #
    # stats_row = ft.Row(
    #     [
    #         MiniMetricCard("Success Rate", f"{success_rate:.1f}%", rate_color),
    #         MiniMetricCard("Total Runs", str(stats["total_runs"]), Theme.Colors.INFO),
    #         MiniMetricCard(
    #             "Avg Duration",
    #             _format_duration(stats["avg_duration_ms"]),
    #             ft.Colors.PURPLE_200,
    #         ),
    #         MiniMetricCard(
    #             "Last Run",
    #             stats["last_run"],
    #             Theme.Colors.SUCCESS
    #             if stats["last_status"] == "success"
    #             else Theme.Colors.ERROR,
    #         ),
    #     ],
    #     spacing=Theme.Spacing.SM,
    # )
    # content.append(stats_row)
    # content.append(ft.Container(height=Theme.Spacing.MD))

    # === Section 3: Recent Executions (hidden for now) ===
    # content.append(SecondaryText("Recent Executions", size=Theme.Typography.BODY_SMALL))
    # content.append(ft.Container(height=Theme.Spacing.XS))
    #
    # # Build execution rows
    # exec_columns = [
    #     DataTableColumn("Time", width=100, style="secondary"),
    #     DataTableColumn("Duration", width=70, alignment="right", style="body"),
    #     DataTableColumn("Status", style=None),  # passthrough for Tag
    # ]
    #
    # exec_rows = []
    # for ex in recent:
    #     is_success = ex["status"] == "success"
    #     if is_success:
    #         status_tag = Tag(text="Success", color=Theme.Colors.SUCCESS)
    #     else:
    #         error_text = ex.get("error", "Failed")
    #         # Truncate long errors
    #         if len(error_text) > 25:
    #             error_text = error_text[:22] + "..."
    #         status_tag = ft.Row(
    #             [
    #                 Tag(text="Failed", color=Theme.Colors.ERROR),
    #                 SecondaryText(error_text, size=10),
    #             ],
    #             spacing=4,
    #         )
    #
    #     exec_rows.append([ex["time"], ex["duration"], status_tag])
    #
    # exec_table = DataTable(
    #     columns=exec_columns,
    #     rows=exec_rows,
    #     row_padding=4,
    #     empty_message="No execution history",
    #     show_header_border=True,
    #     show_row_borders=False,
    # )
    # content.append(exec_table)
    # content.append(ft.Container(height=Theme.Spacing.MD))

    # === Section 4: Action Buttons (hidden for now) ===
    # is_active = status == "active"
    # pause_resume_text = "Pause" if is_active else "Resume"
    # pause_resume_icon = (
    #     ft.Icons.PAUSE_CIRCLE_OUTLINE if is_active else ft.Icons.PLAY_CIRCLE_OUTLINE
    # )
    #
    # actions_row = ft.Row(
    #     [
    #         ft.Container(expand=True),  # Spacer to push buttons right
    #         ft.OutlinedButton(
    #             text="Trigger Now",
    #             icon=ft.Icons.PLAY_ARROW,
    #             on_click=lambda e: _on_trigger_click(e, job_id),
    #         ),
    #         ft.OutlinedButton(
    #             text=pause_resume_text,
    #             icon=pause_resume_icon,
    #             on_click=lambda e: _on_pause_toggle_click(e, job_id, is_active),
    #         ),
    #     ],
    #     spacing=Theme.Spacing.SM,
    # )
    # content.append(actions_row)

    return ft.Column(content, spacing=0)


def _on_trigger_click(e: ft.ControlEvent, job_id: str) -> None:
    """Handle trigger button click - shows confirmation dialog.

    Args:
        e: Click event
        job_id: Job to trigger
    """
    page = e.page
    if not page:
        return

    def close_dialog(e: ft.ControlEvent) -> None:
        dialog.open = False
        page.update()

    def confirm_trigger(e: ft.ControlEvent) -> None:
        dialog.open = False
        page.update()
        # TODO: Call API to trigger job when milestone 21 is complete
        page.open(
            ft.SnackBar(content=ft.Text(f"Triggered job: {job_id} (not implemented)"))
        )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Trigger Job"),
        content=ft.Text(f"Run '{job_id}' now?"),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.FilledButton("Run", on_click=confirm_trigger),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(dialog)


def _on_pause_toggle_click(e: ft.ControlEvent, job_id: str, is_active: bool) -> None:
    """Handle pause/resume button click.

    Args:
        e: Click event
        job_id: Job to pause/resume
        is_active: Current active state
    """
    page = e.page
    if not page:
        return

    action = "Paused" if is_active else "Resumed"
    # TODO: Call API to pause/resume job when milestone 21 is complete
    page.open(ft.SnackBar(content=ft.Text(f"{action} job: {job_id} (not implemented)")))


def _build_job_row(task: dict) -> ExpandableRow:
    """Build expandable row for a scheduled job.

    Args:
        task: Task dictionary with name, next_run, schedule, status

    Returns:
        ExpandableRow with cells and expanded content
    """
    job_name = task.get("name", task.get("id", "Unknown"))
    next_run = task.get("next_run", "")
    schedule = task.get("schedule", "Unknown schedule")
    status = task.get("status", "active")

    next_run_display = format_next_run_time(next_run)
    schedule_display = format_schedule_human_readable(schedule)

    # Status icon and text
    status_icon = "🟢" if status == "active" else "🟠"
    status_text = "Active" if status == "active" else "Paused"

    cells = [
        TableNameText(f"{status_icon} {job_name}"),
        TableCellText(next_run_display),
        TableCellText(schedule_display),
        TableCellText(status_text),
    ]

    return ExpandableRow(
        cells=cells,
        expanded_content=_build_job_expanded_content(task),
    )


class JobsSection(ft.Container):
    """Scheduled jobs list section using ExpandableDataTable."""

    def __init__(self, metadata: dict) -> None:
        """
        Initialize jobs section.

        Args:
            metadata: Component metadata containing upcoming_tasks
        """
        super().__init__()

        upcoming_tasks = metadata.get("upcoming_tasks", [])

        # Define columns
        columns = [
            DataTableColumn("Job Name"),  # expands
            DataTableColumn("Next Run", width=150),
            DataTableColumn("Schedule", width=200),
            DataTableColumn("Status", width=70),
        ]

        # Build expandable rows
        rows = [_build_job_row(task) for task in upcoming_tasks]

        # Build table
        self.content = ExpandableDataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No scheduled jobs",
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
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Scheduler",
            subtitle_text="APScheduler",
            sections=sections,
            status_detail=get_status_detail(component_data),
        )
