"""
Activity Feed Panel

Shows recent system activity and events using the existing DataTable component.
"""

from datetime import datetime

import flet as ft
from app.components.frontend.controls import (
    DataTable,
    DataTableColumn,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system import activity
from app.services.system.activity import ActivityEvent

from .cards.card_utils import get_status_color


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


class ActivityFeed(ft.Container):
    """
    Activity feed panel showing recent system events.

    Uses DataTable for consistent styling with other tables in the app.
    Supports expandable rows to show event details.
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
        self._rows_by_timestamp: dict[datetime, ExpandableActivityRow] = {}
        self._current_events: list[ActivityEvent] = []

        # Define single column - header will show "Activity"
        self._columns = [DataTableColumn("Activity")]

        # Build initial table
        self._build_table()

        # Set content directly - use expand to fill available space
        self.content = self._table
        self.expand = True

    def _build_table(self) -> None:
        """Build the table with current events."""
        events = activity.get_recent(limit=self._max_events)
        self._current_events = events

        if events:
            # Each row is a single cell containing the expandable row control
            rows = []
            for event in events:
                row = ExpandableActivityRow(event)
                self._rows_by_timestamp[event.timestamp] = row
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

        # Build set of new timestamps for quick lookup
        new_timestamps = {e.timestamp for e in new_events}
        old_timestamps = {e.timestamp for e in self._current_events}

        # Find new, removed, and kept events
        added_timestamps = new_timestamps - old_timestamps
        removed_timestamps = old_timestamps - new_timestamps
        kept_timestamps = new_timestamps & old_timestamps

        # Update time display on existing rows
        for ts in kept_timestamps:
            if ts in self._rows_by_timestamp:
                self._rows_by_timestamp[ts].update_time()

        # Remove old rows from tracking
        for ts in removed_timestamps:
            self._rows_by_timestamp.pop(ts, None)

        # Create new rows for new events
        for event in new_events:
            if event.timestamp in added_timestamps:
                row = ExpandableActivityRow(event)
                self._rows_by_timestamp[event.timestamp] = row

        # Rebuild table rows in correct order (reusing existing row objects)
        rows = []
        for event in new_events:
            row = self._rows_by_timestamp.get(event.timestamp)
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
