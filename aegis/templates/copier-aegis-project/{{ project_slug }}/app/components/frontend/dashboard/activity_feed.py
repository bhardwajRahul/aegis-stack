"""
Activity Feed Panel

Shows recent system activity and events using the existing DataTable component.
Groups consecutive alerts from the same component to keep the feed scannable.
"""

from dataclasses import dataclass
from datetime import datetime

import flet as ft
from app.components.frontend.controls import (
    DataTable,
    DataTableColumn,
    PrimaryText,
    SecondaryText,
    Tag,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system import activity
from app.services.system.activity import ActivityEvent

from .cards.card_utils import get_status_color

# Minimum consecutive same-component alerts before grouping
GROUP_THRESHOLD = 2

# Severity ranking for worst_status calculation (higher = worse)
_STATUS_SEVERITY: dict[str, int] = {
    "success": 0,
    "healthy": 0,
    "info": 1,
    "warning": 2,
    "error": 3,
    "unhealthy": 3,
}


def format_relative_time(timestamp: datetime) -> str:
    """Format timestamp as relative time."""
    now = datetime.now()
    diff = now - timestamp

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return timestamp.strftime("%b %d %H:%M")


@dataclass
class EventGroup:
    """UI-only grouping of consecutive same-component events."""

    component: str
    events: list[ActivityEvent]  # newest first (matches feed order)

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def latest_event(self) -> ActivityEvent:
        return self.events[0]

    @property
    def worst_status(self) -> str:
        """Return the most severe status in the group."""
        worst = "success"
        worst_sev = 0
        for event in self.events:
            sev = _STATUS_SEVERITY.get(event.status.lower(), 0)
            if sev > worst_sev:
                worst_sev = sev
                worst = event.status
        return worst

    @property
    def group_key(self) -> str:
        """Key based on component + count + oldest event timestamp.

        Count is included so the key changes when new events join the group,
        forcing refresh to rebuild the row instead of reusing the stale one.
        """
        oldest = self.events[-1]
        return f"{self.component}:{self.count}:{oldest.timestamp.isoformat()}"


def group_consecutive_events(
    events: list[ActivityEvent],
) -> list[ActivityEvent | EventGroup]:
    """Group consecutive same-component events into EventGroups.

    Single O(n) pass. Runs of fewer than GROUP_THRESHOLD are passed through
    as individual events.
    """
    if not events:
        return []

    result: list[ActivityEvent | EventGroup] = []
    run: list[ActivityEvent] = [events[0]]

    for event in events[1:]:
        if event.component == run[0].component:
            run.append(event)
        else:
            _flush_run(run, result)
            run = [event]

    _flush_run(run, result)
    return result


def _flush_run(
    run: list[ActivityEvent],
    result: list[ActivityEvent | EventGroup],
) -> None:
    """Flush accumulated run into result list."""
    if len(run) >= GROUP_THRESHOLD:
        result.append(EventGroup(component=run[0].component, events=run))
    else:
        result.extend(run)


class ExpandableActivityRow(ft.Container):
    """An expandable activity row that shows details when clicked."""

    def __init__(self, event: ActivityEvent) -> None:
        super().__init__()
        self._event = event
        self._expanded = False
        self._expand_icon: ft.Icon | None = None

        # Status dot color (uses utility for consistency across components)
        dot_color = get_status_color(event.status)
        time_ago = format_relative_time(event.timestamp)

        # Store reference to time text for updates
        self._time_text = SecondaryText(time_ago)

        # Build the header row content
        header_content = ft.Row(
            [
                # Status dot
                ft.Container(
                    width=8,
                    height=8,
                    bgcolor=dot_color,
                    border_radius=4,
                    margin=ft.margin.only(right=8),
                ),
                # Stacked title + subtitle (expand to fill)
                ft.Column(
                    [
                        PrimaryText(event.message),
                        self._time_text,  # Use stored reference
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Add expand icon if there are details
        if event.details:
            self._expand_icon = ft.Icon(
                ft.Icons.EXPAND_MORE,
                size=16,
                color=Theme.Colors.TEXT_SECONDARY,
            )
            header_content.controls.append(self._expand_icon)

        # Details section (hidden by default)
        self._details_container = ft.Container(
            content=SecondaryText(event.details or ""),
            padding=ft.padding.only(left=20, top=8, bottom=4),
            visible=False,
        )

        self.content = ft.Column(
            [header_content, self._details_container],
            spacing=0,
        )
        # No hover handler - DataTableRow handles hover effects
        self.on_click = self._toggle_expand if event.details else None

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        """Toggle the expanded state."""
        self._expanded = not self._expanded
        self._details_container.visible = self._expanded

        # Rotate the expand icon
        if self._expand_icon:
            self._expand_icon.name = (
                ft.Icons.EXPAND_LESS if self._expanded else ft.Icons.EXPAND_MORE
            )

        # Use page from event - control's page reference may be stale after refresh
        if e.page:
            e.page.update(self)

    def update_time(self) -> None:
        """Update the relative time display."""
        if self._time_text:
            self._time_text.value = format_relative_time(self._event.timestamp)


class GroupedActivityRow(ft.Container):
    """A collapsible group of consecutive same-component alerts."""

    def __init__(self, group: EventGroup) -> None:
        super().__init__()
        self._group = group
        self._expanded = False

        # Build child rows (created once, reused across expand/collapse)
        self._child_rows = [ExpandableActivityRow(e) for e in group.events]

        # Dot color reflects latest (most recent) event status
        dot_color = get_status_color(group.latest_event.status)
        time_ago = format_relative_time(group.latest_event.timestamp)

        # Store reference to time text for updates
        self._time_text = SecondaryText(time_ago)

        # Count badge
        self._count_tag = Tag(
            f"{group.count} alerts",
            color=dot_color,
        )

        # Expand/collapse icon
        self._expand_icon = ft.Icon(
            ft.Icons.EXPAND_MORE,
            size=16,
            color=Theme.Colors.TEXT_SECONDARY,
        )

        # Component display name (capitalize first letter)
        display_name = group.component.replace("_", " ").title()

        # Header row: dot + name + count badge + time + expand icon
        self._header = ft.Row(
            [
                # Status dot
                ft.Container(
                    width=8,
                    height=8,
                    bgcolor=dot_color,
                    border_radius=4,
                    margin=ft.margin.only(right=8),
                ),
                # Component name + time (expand to fill)
                ft.Column(
                    [
                        PrimaryText(display_name),
                        self._time_text,
                    ],
                    spacing=2,
                    expand=True,
                ),
                self._count_tag,
                self._expand_icon,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Child rows container (hidden by default)
        self._children_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=row,
                        padding=ft.padding.only(left=16),
                    )
                    for row in self._child_rows
                ],
                spacing=0,
            ),
            visible=False,
        )

        self.content = ft.Column(
            [self._header, self._children_container],
            spacing=0,
        )
        self.on_click = self._toggle_expand

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        """Toggle expanded state showing/hiding individual alerts."""
        self._expanded = not self._expanded
        self._children_container.visible = self._expanded
        self._expand_icon.name = (
            ft.Icons.EXPAND_LESS if self._expanded else ft.Icons.EXPAND_MORE
        )
        if e.page:
            e.page.update(self)

    def update_time(self) -> None:
        """Update time display on summary and all child rows."""
        if self._time_text:
            self._time_text.value = format_relative_time(
                self._group.latest_event.timestamp
            )
        for row in self._child_rows:
            row.update_time()


class ActivityFeed(ft.Container):
    """
    Activity feed panel showing recent system events.

    Uses DataTable for consistent styling with other tables in the app.
    Supports expandable rows to show event details.
    Groups consecutive same-component alerts into collapsible rows.
    Expands to fill available vertical space with scroll-on-overflow.
    """

    def __init__(self, max_events: int = 40) -> None:
        """Initialize the activity feed.

        Args:
            max_events: Maximum number of events to display (default: 40)
        """
        super().__init__()
        self._max_events = max_events
        self._table: DataTable | None = None
        self._rows_by_key: dict[str, ExpandableActivityRow | GroupedActivityRow] = {}
        self._current_events: list[ActivityEvent] = []

        # Define single column - header will show "Activity"
        self._columns = [DataTableColumn("Activity")]

        # Build initial table
        self._build_table()

        # Set content directly - use expand to fill available space
        self.content = self._table
        self.expand = True

    def _build_table(self) -> None:
        """Build the table with current events, grouping consecutive alerts."""
        events = activity.get_recent(limit=self._max_events)
        self._current_events = events

        if events:
            grouped = group_consecutive_events(events)
            rows = []
            for item in grouped:
                row = self._create_row(item)
                key = _item_key(item)
                self._rows_by_key[key] = row
                rows.append([row])
        else:
            # Show placeholder when no events yet
            placeholder_event = ActivityEvent(
                component="system",
                event_type="info",
                message="Waiting for events...",
                status="success",
            )
            rows = [[ExpandableActivityRow(placeholder_event)]]

        # Use DataTable with expand=True - fills available space, scrolls on overflow
        self._table = DataTable(
            columns=self._columns,
            rows=rows,
            row_padding=10,
            expand=True,
        )

    def refresh(self) -> None:
        """Refresh with in-place updates to preserve expanded state."""
        new_events = activity.get_recent(limit=self._max_events)

        if not new_events:
            return

        new_grouped = group_consecutive_events(new_events)
        new_keys = {_item_key(item) for item in new_grouped}
        old_keys = set(self._rows_by_key.keys())

        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        kept_keys = new_keys & old_keys

        # Update time display on existing rows
        for key in kept_keys:
            row = self._rows_by_key.get(key)
            if row:
                row.update_time()

        # Remove stale rows from tracking
        for key in removed_keys:
            self._rows_by_key.pop(key, None)

        # Create new rows for added items
        for item in new_grouped:
            key = _item_key(item)
            if key in added_keys:
                self._rows_by_key[key] = self._create_row(item)

        # Rebuild table rows in correct order (reusing existing row objects)
        rows = []
        for item in new_grouped:
            key = _item_key(item)
            row = self._rows_by_key.get(key)
            if row:
                rows.append([row])

        self._current_events = new_events

        # Update table content (reuses row objects, preserving state)
        self._table = DataTable(
            columns=self._columns,
            rows=rows,
            row_padding=10,
            expand=True,
        )
        self.content = self._table

    def _create_row(
        self, item: ActivityEvent | EventGroup
    ) -> ExpandableActivityRow | GroupedActivityRow:
        """Create the appropriate row type for an item."""
        if isinstance(item, EventGroup):
            return GroupedActivityRow(item)
        return ExpandableActivityRow(item)


def _item_key(item: ActivityEvent | EventGroup) -> str:
    """Return a stable string key for an event or group."""
    if isinstance(item, EventGroup):
        return item.group_key
    return item.timestamp.isoformat()
