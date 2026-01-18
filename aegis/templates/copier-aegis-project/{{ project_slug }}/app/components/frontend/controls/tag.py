"""
Tag component for badges and labels.

Modern tag UI control based on ee-toolset design.
"""

import flet as ft
from app.components.frontend.styles import FontConfig


class Tag(ft.Container):
    """
    Tag component for displaying badges, labels, and categories.

    Features bordered design with colored text and border, sized for compact display.
    """

    def __init__(self, text: str, color: str = ft.Colors.AMBER) -> None:
        super().__init__(
            border=ft.border.all(1, color),
            border_radius=ft.border_radius.all(5),
            padding=ft.Padding(7.5, 2.5, 7.5, 2.5),
            alignment=ft.alignment.center,
            content=ft.Text(
                text,
                weight=ft.FontWeight.W_700,
                color=color,
                font_family=FontConfig.FAMILY_PRIMARY,
                size=FontConfig.SIZE_TERTIARY,
                text_align=ft.TextAlign.CENTER,
            ),
        )
