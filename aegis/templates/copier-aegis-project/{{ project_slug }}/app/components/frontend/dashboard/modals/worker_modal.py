"""
Worker Detail Modal

Displays comprehensive worker component information using component composition.
Each section is a self-contained Flet control that can be reused and tested.
"""

import time

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    DataTableColumn,
    ExpandableDataTable,
    ExpandableRow,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.components.worker.registry import get_queue_metadata
from app.services.system.models import ComponentStatus
from app.services.system.ui import get_component_label

from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard

# Worker health status thresholds
FAILURE_RATE_CRITICAL_THRESHOLD = 20  # % - Red status (failing)
FAILURE_RATE_WARNING_THRESHOLD = 5  # % - Yellow status (degraded)
SUCCESS_RATE_HEALTHY_THRESHOLD = 95  # % - Green display
SUCCESS_RATE_WARNING_THRESHOLD = 80  # % - Yellow display

# Queue health table column widths (pixels)
COL_WIDTH_STATUS_ICON = 30
COL_WIDTH_QUEUED = 80
COL_WIDTH_PROCESSING = 80
COL_WIDTH_COMPLETED = 100
COL_WIDTH_FAILED = 80
COL_WIDTH_SUCCESS_RATE = 100
COL_WIDTH_THROUGHPUT = 80
COL_WIDTH_ETA = 80
COL_WIDTH_STATUS = 80


def _build_queue_expanded_content(queue_name: str) -> ft.Control:
    """Build expanded content showing registered functions for a queue.

    Args:
        queue_name: Name of the queue (e.g., 'system', 'load_test')

    Returns:
        Column with queue description and registered functions in table format
    """
    try:
        metadata = get_queue_metadata(queue_name)
        description = metadata.get("description", "")
        functions = metadata.get("functions", [])
        max_jobs = metadata.get("max_jobs", 10)
        timeout = metadata.get("timeout", 300)
    except Exception:
        description = f"Queue: {queue_name}"
        functions = []
        max_jobs = 10
        timeout = 300

    content: list[ft.Control] = []

    # Description on top with italic styling
    if description:
        content.append(
            ft.Text(
                description,
                size=Theme.Typography.BODY,
                italic=True,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
        content.append(ft.Container(height=Theme.Spacing.SM))

    # Registered functions in a mini table
    if functions:
        # Table header
        header_style = ft.TextStyle(
            size=11,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        task_header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text("Task", style=header_style),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Text("Status", style=header_style),
                        width=70,
                        alignment=ft.alignment.center_right,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.only(bottom=6),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        )

        # Task rows
        task_rows = [task_header]
        cell_style = ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE)

        for func in functions:
            task_row = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(func, style=cell_style),
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Registered",
                                size=10,
                                color=Theme.Colors.SUCCESS,
                                weight=ft.FontWeight.W_500,
                            ),
                            width=70,
                            alignment=ft.alignment.center_right,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(vertical=4),
            )
            task_rows.append(task_row)

        # Wrap in a styled container
        tasks_table = ft.Container(
            content=ft.Column(task_rows, spacing=0),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
            border_radius=6,
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)),
            padding=ft.padding.all(10),
        )
        content.append(tasks_table)
    else:
        content.append(
            SecondaryText("No tasks registered", size=Theme.Typography.BODY_SMALL)
        )

    # Config info row
    content.append(ft.Container(height=Theme.Spacing.SM))
    content.append(
        ft.Row(
            [
                SecondaryText(f"Concurrency: {max_jobs}", size=11),
                SecondaryText("|", size=11),
                SecondaryText(f"Timeout: {timeout}s", size=11),
            ],
            spacing=8,
        )
    )

    return ft.Column(content, spacing=4)


def _compute_queue_values(
    queue_component: ComponentStatus,
) -> dict[str, str | float | None]:
    """Compute display values for a queue health row.

    Returns dict with keys: status_icon, status_color, status_text,
    queued_jobs, jobs_ongoing, jobs_completed, jobs_failed,
    success_rate, rate_color.
    """
    metadata = queue_component.metadata or {}
    worker_alive = metadata.get("worker_alive", False)
    queued_jobs = metadata.get("queued_jobs", 0)
    jobs_ongoing = metadata.get("jobs_ongoing", 0)
    jobs_completed = metadata.get("jobs_completed", 0)
    jobs_failed = metadata.get("jobs_failed", 0)
    failure_rate = metadata.get("failure_rate_percent", 0.0)
    has_job_history = (jobs_completed + jobs_failed) > 0

    # Determine status icon and color (matching card behavior)
    message = queue_component.message or ""
    if not worker_alive:
        if "no functions" in message.lower():
            status_icon = "⚪"  # No tasks defined
            status_color = ft.Colors.GREY_600
            status_text = "No Tasks"
        else:
            status_icon = "🔴"  # Offline - problem
            status_color = Theme.Colors.ERROR
            status_text = "Offline"
    elif failure_rate > FAILURE_RATE_CRITICAL_THRESHOLD:
        status_icon = "🔴"  # Failing
        status_color = Theme.Colors.ERROR
        status_text = "Failing"
    elif failure_rate > FAILURE_RATE_WARNING_THRESHOLD:
        status_icon = "🟠"  # Degraded
        status_color = Theme.Colors.WARNING
        status_text = "Degraded"
    elif jobs_ongoing > 0:
        status_icon = "🔵"  # Active - processing
        status_color = Theme.Colors.INFO
        status_text = "Active"
    else:
        status_icon = "🟢"  # Healthy
        status_color = Theme.Colors.SUCCESS
        status_text = "Online"

    # Success rate display with color coding
    success_rate: float | None = (
        (100 - failure_rate) if (worker_alive and has_job_history) else None
    )
    if success_rate is None:
        rate_color = ft.Colors.ON_SURFACE_VARIANT
    elif success_rate >= SUCCESS_RATE_HEALTHY_THRESHOLD:
        rate_color = Theme.Colors.SUCCESS
    elif success_rate >= SUCCESS_RATE_WARNING_THRESHOLD:
        rate_color = Theme.Colors.WARNING
    else:
        rate_color = Theme.Colors.ERROR

    return {
        "status_icon": status_icon,
        "status_color": status_color,
        "status_text": status_text,
        "queued_jobs": queued_jobs,
        "jobs_ongoing": jobs_ongoing,
        "jobs_completed": jobs_completed,
        "jobs_failed": jobs_failed,
        "success_rate": success_rate,
        "rate_color": rate_color,
    }


def _format_eta(seconds: float) -> str:
    """Format an ETA in seconds to a human-readable string."""
    if seconds < 1:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s}s" if s else f"{m}m"
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if m else f"{h}h"


def _build_queue_health_row(queue_component: ComponentStatus) -> ExpandableRow:
    """Build row cells for a single queue health status.

    Args:
        queue_component: ComponentStatus for a single queue

    Returns:
        ExpandableRow with controls for each column
    """
    queue_name = queue_component.name
    vals = _compute_queue_values(queue_component)

    cells = [
        ft.Text(vals["status_icon"], size=16),
        PrimaryText(queue_name, size=Theme.Typography.BODY),
        BodyText(str(vals["queued_jobs"]), text_align=ft.TextAlign.CENTER),
        BodyText(str(vals["jobs_ongoing"]), text_align=ft.TextAlign.CENTER),
        BodyText(str(vals["jobs_completed"]), text_align=ft.TextAlign.CENTER),
        BodyText(str(vals["jobs_failed"]), text_align=ft.TextAlign.CENTER),
        SecondaryText(
            f"{vals['success_rate']:.1f}%"
            if vals["success_rate"] is not None
            else "N/A",
            color=vals["rate_color"],
            weight=Theme.Typography.WEIGHT_SEMIBOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        SecondaryText(
            "—",
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
        ),
        SecondaryText(
            "—",
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
        ),
        SecondaryText(
            vals["status_text"],
            color=vals["status_color"],
            weight=Theme.Typography.WEIGHT_SEMIBOLD,
            text_align=ft.TextAlign.CENTER,
        ),
    ]

    return ExpandableRow(
        cells=cells,
        expanded_content=_build_queue_expanded_content(queue_name),
    )


class OverviewSection(ft.Container):
    """Overview section showing key worker metrics."""

    def __init__(self, worker_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize overview section.

        Args:
            worker_component: Worker ComponentStatus with metadata and sub_components
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        metadata = worker_component.metadata or {}

        # Get queue sub-components
        queues_component = worker_component.sub_components.get("queues")
        if queues_component and queues_component.sub_components:
            total_queues = len(queues_component.sub_components)
        else:
            total_queues = 0

        total_ongoing = metadata.get("total_ongoing", 0)
        total_queued = metadata.get("total_queued", 0)
        total_completed = metadata.get("total_completed", 0)
        total_failed = metadata.get("total_failed", 0)

        # Color for failed jobs - red if any failures
        failed_color = Theme.Colors.ERROR if total_failed > 0 else Theme.Colors.SUCCESS

        # Store references for live updates
        self._card_queues = MetricCard(
            "Total Queues", str(total_queues), Theme.Colors.INFO
        )
        self._card_processing = MetricCard(
            "Processing", str(total_ongoing), Theme.Colors.INFO
        )
        self._card_queued = MetricCard(
            "Queued", str(total_queued), Theme.Colors.WARNING
        )
        self._card_completed = MetricCard(
            "Completed", str(total_completed), Theme.Colors.SUCCESS
        )
        self._card_failed = MetricCard("Failed", str(total_failed), failed_color)

        self.content = ft.Row(
            [
                self._card_queues,
                self._card_processing,
                self._card_queued,
                self._card_completed,
                self._card_failed,
            ],
            spacing=Theme.Spacing.MD,
        )

    def update_data(self, worker_component: ComponentStatus) -> None:
        """Update metric values in place."""
        metadata = worker_component.metadata or {}

        queues_component = worker_component.sub_components.get("queues")
        if queues_component and queues_component.sub_components:
            total_queues = len(queues_component.sub_components)
        else:
            total_queues = 0

        total_failed = metadata.get("total_failed", 0)
        failed_color = Theme.Colors.ERROR if total_failed > 0 else Theme.Colors.SUCCESS

        self._card_queues.set_value(str(total_queues))
        self._card_processing.set_value(str(metadata.get("total_ongoing", 0)))
        self._card_queued.set_value(str(metadata.get("total_queued", 0)))
        self._card_completed.set_value(str(metadata.get("total_completed", 0)))
        self._card_failed.set_value(str(total_failed), failed_color)

    def _increment_card(self, card: MetricCard, delta: int = 1) -> None:
        """Increment a MetricCard's numeric value by delta."""
        current = int(card.value_text.value or "0")
        card.set_value(str(current + delta))

    def sync_queued(self, total: int) -> None:
        """Set queued card to an explicit value (used after per-queue cleanup)."""
        self._card_queued.set_value(str(total))

    def increment_queued(self) -> None:
        """Increment queued count by 1."""
        self._increment_card(self._card_queued)

    def decrement_queued(self) -> None:
        """Decrement queued count by 1 (floor at 0)."""
        current = int(self._card_queued.value_text.value or "0")
        self._card_queued.set_value(str(max(0, current - 1)))

    def increment_ongoing(self) -> None:
        """Increment processing count by 1."""
        self._increment_card(self._card_processing)

    def decrement_ongoing(self) -> None:
        """Decrement processing count by 1 (floor at 0)."""
        current = int(self._card_processing.value_text.value or "0")
        self._card_processing.set_value(str(max(0, current - 1)))

    def increment_completed(self) -> None:
        """Increment completed count by 1."""
        self._increment_card(self._card_completed)

    def increment_failed(self) -> None:
        """Increment failed count by 1."""
        self._increment_card(self._card_failed)
        # Ensure failed color is red when > 0
        self._card_failed.value_text.color = Theme.Colors.ERROR

    def set_totals(
        self,
        total_queued: int,
        total_ongoing: int,
        total_completed: int,
        total_failed: int,
    ) -> None:
        """Set all counters to absolute values from SSE batch data."""
        self._card_queued.set_value(str(total_queued))
        self._card_processing.set_value(str(total_ongoing))
        self._card_completed.set_value(str(total_completed))
        failed_color = Theme.Colors.ERROR if total_failed > 0 else Theme.Colors.SUCCESS
        self._card_failed.set_value(str(total_failed), failed_color)


class QueueHealthSection(ft.Container):
    """Queue health status table section."""

    def __init__(self, worker_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize queue health section.

        Args:
            worker_component: Worker ComponentStatus with queue sub-components
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        # Extract queue sub-components
        queues_component = worker_component.sub_components.get("queues")
        queue_components = []
        if queues_component and queues_component.sub_components:
            queue_components = list(queues_component.sub_components.values())

        # Define columns
        self._columns = [
            DataTableColumn("", width=COL_WIDTH_STATUS_ICON),  # Status icon
            DataTableColumn("Queue Name"),  # expands
            DataTableColumn("Queued", width=COL_WIDTH_QUEUED, alignment="center"),
            DataTableColumn(
                "Processing", width=COL_WIDTH_PROCESSING, alignment="center"
            ),
            DataTableColumn("Completed", width=COL_WIDTH_COMPLETED, alignment="center"),
            DataTableColumn("Failed", width=COL_WIDTH_FAILED, alignment="center"),
            DataTableColumn(
                "Success Rate", width=COL_WIDTH_SUCCESS_RATE, alignment="center"
            ),
            DataTableColumn("Tasks/s", width=COL_WIDTH_THROUGHPUT, alignment="center"),
            DataTableColumn("ETA", width=COL_WIDTH_ETA, alignment="center"),
            DataTableColumn("Status", width=COL_WIDTH_STATUS, alignment="center"),
        ]

        # Build row data and store cell references by queue name
        rows = []
        self._queue_cells: dict[str, list] = {}
        # Throughput tracking: {queue: {"start_time": float, "start_completed": int}}
        self._queue_tracking: dict[str, dict[str, float | int]] = {}
        for queue in queue_components:
            row = _build_queue_health_row(queue)
            rows.append(row)
            self._queue_cells[queue.name] = row.cells

        # Build table (stored for potential rebuild on queue list changes)
        self._table = ExpandableDataTable(
            columns=self._columns,
            rows=rows,
            row_padding=6,
            empty_message="No queues configured",
        )

        self.content = self._table

    def update_data(self, worker_component: ComponentStatus) -> None:
        """Update queue health values in place by mutating existing cell controls."""
        queues_component = worker_component.sub_components.get("queues")
        if not queues_component or not queues_component.sub_components:
            return

        # If queue list changed, rebuild the entire table
        new_names = set(queues_component.sub_components.keys())
        if new_names != set(self._queue_cells.keys()):
            queue_components = list(queues_component.sub_components.values())
            rows = []
            self._queue_cells = {}
            for queue in queue_components:
                row = _build_queue_health_row(queue)
                rows.append(row)
                self._queue_cells[queue.name] = row.cells
            self._table._rows = rows
            self._table._expanded = [False] * len(rows)
            self._table._build()
            return

        # Same queues — mutate cell values in place (no rebuild needed)
        for queue_name, queue_comp in queues_component.sub_components.items():
            cells = self._queue_cells.get(queue_name)
            if not cells:
                continue

            vals = _compute_queue_values(queue_comp)
            # cells: [0]=icon, [1]=name, [2]=queued, [3]=processing,
            #         [4]=completed, [5]=failed, [6]=rate,
            #         [7]=tasks/s, [8]=ETA, [9]=status
            cells[0].value = vals["status_icon"]
            cells[2].value = str(vals["queued_jobs"])
            cells[3].value = str(vals["jobs_ongoing"])
            cells[4].value = str(vals["jobs_completed"])
            cells[5].value = str(vals["jobs_failed"])
            cells[6].value = (
                f"{vals['success_rate']:.1f}%"
                if vals["success_rate"] is not None
                else "N/A"
            )
            cells[6].color = vals["rate_color"]
            cells[9].value = vals["status_text"]
            cells[9].color = vals["status_color"]

    def _increment_cell(self, queue: str, cell_idx: int, delta: int = 1) -> None:
        """Increment a numeric cell value for a queue row."""
        cells = self._queue_cells.get(queue)
        if not cells:
            return
        current = int(cells[cell_idx].value or "0")
        cells[cell_idx].value = str(current + delta)

    def increment_queued(self, queue: str) -> None:
        """Increment queued cell (index 2) for a queue."""
        self._increment_cell(queue, 2)

    def decrement_queued(self, queue: str) -> None:
        """Decrement queued cell (index 2) for a queue, floor at 0."""
        cells = self._queue_cells.get(queue)
        if not cells:
            return
        current = int(cells[2].value or "0")
        cells[2].value = str(max(0, current - 1))

    def increment_ongoing(self, queue: str) -> None:
        """Increment processing cell (index 3) for a queue."""
        self._increment_cell(queue, 3)
        cells = self._queue_cells.get(queue)
        if cells:
            cells[0].value = "🔵"
            cells[9].value = "Active"
            cells[9].color = Theme.Colors.INFO

    def decrement_ongoing(self, queue: str) -> None:
        """Decrement processing cell (index 3) for a queue, floor at 0."""
        cells = self._queue_cells.get(queue)
        if not cells:
            return
        current = int(cells[3].value or "0")
        new_val = max(0, current - 1)
        cells[3].value = str(new_val)
        if new_val == 0:
            queued = int(cells[2].value or "0")
            if queued <= 1:
                # Revert to Online when truly idle. The <= 1 guard
                # tolerates a stale queued count of 1 caused by SSE
                # event gaps (events published between read_queue_totals
                # and the first XREAD are lost, leaving the counter off
                # by 1). Zero out queued to prevent the stale value from
                # persisting in the UI.
                cells[2].value = "0"
                cells[0].value = "🟢"
                cells[9].value = "Online"
                cells[9].color = Theme.Colors.SUCCESS
                self._queue_tracking.pop(queue, None)

    def total_queued(self) -> int:
        """Sum queued values across all queue rows."""
        total = 0
        for cells in self._queue_cells.values():
            total += int(cells[2].value or "0")
        return total

    def increment_completed(self, queue: str) -> None:
        """Increment completed cell (index 4) for a queue."""
        self._increment_cell(queue, 4)
        self._update_throughput(queue)

    def increment_failed(self, queue: str) -> None:
        """Increment failed cell (index 5) for a queue."""
        self._increment_cell(queue, 5)
        self._update_throughput(queue)

    def _update_throughput(self, queue: str) -> None:
        """Recompute tasks/s and ETA for a queue based on completed count."""
        cells = self._queue_cells.get(queue)
        if not cells:
            return

        completed = int(cells[4].value or "0")
        queued = int(cells[2].value or "0")

        tracking = self._queue_tracking.get(queue)
        if not tracking:
            # First completion event — start tracking
            self._queue_tracking[queue] = {
                "start_time": time.monotonic(),
                "start_completed": completed - 1,  # this call already incremented
            }
            cells[7].value = "—"
            cells[8].value = "—"
            return

        elapsed = time.monotonic() - tracking["start_time"]
        delta = completed - int(tracking["start_completed"])
        if elapsed < 0.1 or delta <= 0:
            return

        tps = delta / elapsed
        cells[7].value = f"{tps:.1f}"
        cells[7].color = Theme.Colors.INFO

        # ETA based on queued jobs remaining
        if queued > 0 and tps > 0:
            eta_s = queued / tps
            eta_str = _format_eta(eta_s)
            cells[8].value = eta_str
            # Only color as warning when showing a real ETA, not "—"
            cells[8].color = (
                Theme.Colors.WARNING if eta_str != "—" else ft.Colors.ON_SURFACE_VARIANT
            )
        else:
            cells[8].value = "—"
            cells[8].color = ft.Colors.ON_SURFACE_VARIANT

    def set_queue_totals(
        self,
        queue: str,
        queued: int,
        ongoing: int,
        completed: int,
        failed: int,
    ) -> None:
        """Set absolute values for a queue row's numeric cells."""
        cells = self._queue_cells.get(queue)
        if not cells:
            return
        # cells: [2]=queued, [3]=processing, [4]=completed, [5]=failed
        cells[2].value = str(queued)
        cells[3].value = str(ongoing)
        cells[4].value = str(completed)
        cells[5].value = str(failed)
        # Update success rate
        total = completed + failed
        if total > 0:
            rate = (completed / total) * 100
            cells[6].value = f"{rate:.1f}%"
            cells[6].color = (
                Theme.Colors.SUCCESS
                if rate >= 95
                else Theme.Colors.WARNING
                if rate >= 80
                else Theme.Colors.ERROR
            )
        else:
            cells[6].value = "N/A"
        # Reset throughput tracking with new baseline
        self._queue_tracking[queue] = {
            "start_time": time.monotonic(),
            "start_completed": completed,
        }
        cells[7].value = "—"
        cells[7].color = ft.Colors.ON_SURFACE_VARIANT
        cells[8].value = "—"
        cells[8].color = ft.Colors.ON_SURFACE_VARIANT
        # set_queue_totals is the authoritative baseline — set status here
        if ongoing > 0:
            cells[0].value = "🔵"
            cells[9].value = "Active"
            cells[9].color = Theme.Colors.INFO
        else:
            cells[0].value = "🟢"
            cells[9].value = "Online"
            cells[9].color = Theme.Colors.SUCCESS


class BrokerSection(ft.Container):
    """Visual broker connection diagram showing Redis as the message broker."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize broker section.

        Args:
            component_data: Worker ComponentStatus with Redis URL in metadata
        """
        super().__init__()

        metadata = component_data.metadata or {}
        redis_url = metadata.get("redis_url", "redis://localhost:6379")

        # Parse URL for display (just host:port)
        display_url = redis_url.replace("redis://", "")

        # Arrow pointing down from table to broker
        arrow = ft.Container(
            content=ft.Text("▼", size=24, color=ft.Colors.OUTLINE),
            alignment=ft.alignment.center,
        )

        # Redis broker box
        broker_box = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Redis", size=16, weight=ft.FontWeight.W_600),
                    SecondaryText("Message Broker", size=12),
                    ft.Container(height=4),
                    BodyText(display_url, size=11),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            padding=ft.padding.all(16),
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            width=160,
        )

        self.content = ft.Column(
            [arrow, broker_box],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )
        self.padding = Theme.Spacing.MD


class WorkerDetailDialog(BaseDetailPopup):
    """
    Worker component detail popup dialog.

    Displays comprehensive worker information including queue health,
    job statistics, and broker connection diagram.
    """

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize worker detail popup.

        Args:
            component_data: Worker ComponentStatus from health check
        """
        # Build sections (store references for live updates)
        self._overview = OverviewSection(component_data, page)
        self._queue_health = QueueHealthSection(component_data, page)
        self._broker = BrokerSection(component_data, page)
        self._dirty = False

        sections = [self._overview, self._queue_health, self._broker]

        # Compute status detail (e.g., "2/3 queues online")
        status_detail = self._compute_status_detail(component_data)

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Worker",
            subtitle_text=get_component_label("worker"),
            sections=sections,
            status_detail=status_detail,
        )

    def update_data(self, component_data: ComponentStatus) -> None:
        """Update all sections with fresh data (mutates existing controls)."""
        self._overview.update_data(component_data)
        self._queue_health.update_data(component_data)

        # Update status badge in header
        new_detail = self._compute_status_detail(component_data)
        self.update_status(component_data.status, new_detail)

        # Push changes to Flet client — page.update() alone doesn't
        # propagate to controls inside page.overlay popups
        self.update()

    def increment_queued(self, queue: str) -> None:
        """A job was enqueued — increment queued counters."""
        self._overview.increment_queued()
        self._queue_health.increment_queued(queue)
        self._dirty = True

    def decrement_queued(self, queue: str) -> None:
        """A job left the queue — decrement queued counters."""
        self._overview.decrement_queued()
        self._queue_health.decrement_queued(queue)
        self._dirty = True

    def increment_ongoing(self, queue: str) -> None:
        """A job started processing — increment ongoing counters."""
        self._overview.increment_ongoing()
        self._queue_health.increment_ongoing(queue)
        self._dirty = True

    def increment_completed(self, queue: str) -> None:
        """A job completed — increment completed, decrement ongoing."""
        self._overview.increment_completed()
        self._overview.decrement_ongoing()
        self._queue_health.increment_completed(queue)
        self._queue_health.decrement_ongoing(queue)
        # Sync summary queued card with per-queue totals (cleanup may have zeroed rows)
        self._overview.sync_queued(self._queue_health.total_queued())
        self._dirty = True

    def increment_failed(self, queue: str) -> None:
        """A job failed — increment failed, decrement ongoing."""
        self._overview.increment_failed()
        self._overview.decrement_ongoing()
        self._queue_health.increment_failed(queue)
        self._queue_health.decrement_ongoing(queue)
        # Sync summary queued card with per-queue totals (cleanup may have zeroed rows)
        self._overview.sync_queued(self._queue_health.total_queued())
        self._dirty = True

    def set_totals(self, queues: dict[str, dict[str, int]]) -> None:
        """Set all counters to absolute values from SSE batch data.

        Args:
            queues: Mapping of queue_type → {queued, ongoing, completed, failed}
        """
        total_queued = total_ongoing = total_completed = total_failed = 0
        for queue, vals in queues.items():
            q = vals.get("queued", 0)
            o = vals.get("ongoing", 0)
            c = vals.get("completed", 0)
            f = vals.get("failed", 0)
            total_queued += q
            total_ongoing += o
            total_completed += c
            total_failed += f
            self._queue_health.set_queue_totals(queue, q, o, c, f)
        self._overview.set_totals(
            total_queued,
            total_ongoing,
            total_completed,
            total_failed,
        )
        self._dirty = True

    def flush(self) -> None:
        """Push pending UI changes to the Flet client.

        Called by the SSE listener on a time-based schedule rather than
        per-event, so the browser isn't overwhelmed during high throughput.
        """
        if self._dirty:
            self.update()
            self._dirty = False

    @staticmethod
    def _compute_status_detail(component_data: ComponentStatus) -> str | None:
        """Get status detail for non-healthy states.

        Uses health check message for detail text.
        """
        from app.components.frontend.dashboard.cards.card_utils import get_status_detail

        return get_status_detail(component_data)
