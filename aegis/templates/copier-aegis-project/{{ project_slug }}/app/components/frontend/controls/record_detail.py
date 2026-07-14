"""Reusable read-only detail popup.

A record-agnostic dialog: pass a title and grouped ``(label, value)`` sections
and it renders a clean, scrollable key/value view. Callers (transactions,
trades, anything) supply their own field mapping, so the dialog itself stays
generic — one component for every "click a row, see everything" surface.
"""

from __future__ import annotations

import flet as ft

from app.components.frontend.controls.buttons import PulseButton
from app.components.frontend.controls.text import BodyText, H3Text, SecondaryText
from app.components.frontend.theme import AegisTheme as Theme

# (label, value) — value is pre-formatted by the caller. Empty/None values are
# dropped so a record only shows the fields it actually has.
DetailField = tuple[str, str | None]
DetailSection = tuple[str, list[DetailField]]


class RecordDetailDialog(ft.AlertDialog):
    """A titled, scrollable label/value detail dialog. ``show()`` opens it."""

    def __init__(
        self,
        page: ft.Page,
        title: str,
        sections: list[DetailSection],
        *,
        subtitle: str | None = None,
    ) -> None:
        self._page = page
        blocks: list[ft.Control] = []
        if subtitle:
            blocks.append(SecondaryText(subtitle))
        for section_title, fields in sections:
            rows = [
                self._field_row(label, value)
                for label, value in fields
                if value not in (None, "")
            ]
            if not rows:
                continue
            if section_title:
                blocks.append(
                    ft.Container(
                        content=H3Text(section_title),
                        padding=ft.padding.only(top=Theme.Spacing.SM),
                    )
                )
            blocks.extend(rows)
        super().__init__(
            modal=True,
            title=H3Text(title),
            content=ft.Container(
                content=ft.Column(
                    blocks,
                    spacing=Theme.Spacing.XS,
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
                width=560,
            ),
            actions=[
                PulseButton(
                    on_click_callable=self._close, text="Close", variant="muted"
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

    def _field_row(self, label: str, value: str | None) -> ft.Control:
        return ft.Row(
            [
                ft.Container(content=SecondaryText(label), width=200),
                ft.Container(
                    content=BodyText(str(value), selectable=True), expand=True
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=Theme.Spacing.MD,
        )

    async def _close(self) -> None:
        self.open = False
        self._page.update()

    def show(self) -> None:
        self._page.open(self)
