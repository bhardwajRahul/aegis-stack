"""Reusable row-action menu (kebab) and menu items for data tables.

Provides composable controls so tables can keep a single overflow
button per row instead of a strip of icon buttons. Theme-aware: icon
and label colors come from Material semantic tokens
(``ft.Colors.ON_SURFACE`` / ``ON_SURFACE_VARIANT`` / ``ERROR``) so they
adapt with light/dark mode.
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.components.frontend.theme import AegisTheme as Theme


class ActionMenuItem(ft.PopupMenuItem):
    """A row-action menu item with icon + label.

    Pass ``destructive=True`` to render in the error palette (red icon
    and label) for delete-style actions.
    """

    def __init__(
        self,
        label: str,
        icon: str,
        on_click: Callable[[ft.ControlEvent], None],
        *,
        destructive: bool = False,
    ) -> None:
        icon_color = ft.Colors.ERROR if destructive else ft.Colors.ON_SURFACE_VARIANT
        text_color = ft.Colors.ERROR if destructive else ft.Colors.ON_SURFACE
        super().__init__(
            content=ft.Row(
                [
                    ft.Icon(icon, color=icon_color, size=18),
                    ft.Text(label, color=text_color),
                ],
                spacing=Theme.Spacing.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=on_click,
        )


class ActionMenu(ft.PopupMenuButton):
    """Kebab-style row-action menu button.

    Composes a ``MORE_HORIZ`` icon trigger with the supplied items.
    Use ``ft.PopupMenuItem()`` (no args) inside ``items`` to insert a
    divider between groups.
    """

    def __init__(self, items: list[ft.PopupMenuItem]) -> None:
        super().__init__(
            icon=ft.Icons.MORE_HORIZ,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            tooltip="Actions",
            items=items,
        )
