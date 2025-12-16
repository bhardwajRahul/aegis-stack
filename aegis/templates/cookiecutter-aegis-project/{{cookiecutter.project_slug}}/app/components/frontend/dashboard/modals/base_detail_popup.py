"""
Base Detail Popup for Component Modals

Extends BasePopup with consistent modal structure for component details,
including title, status badge, scrollable sections, and close button.
"""

import flet as ft
from app.components.frontend.controls import H2Text, Tag
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus, ComponentStatusType

from .base_popup import BasePopup
from .modal_constants import ModalLayout


class BaseDetailPopup(BasePopup):
    """
    Base class for all component detail popups.

    Provides consistent title formatting, status badges, layout structure,
    and close behavior. Child classes need only provide sections and
    customization parameters.

    Usage:
        class MyDetailPopup(BaseDetailPopup):
            def __init__(self, component_data: ComponentStatus, page: ft.Page):
                sections = [
                    MyOverviewSection(component_data.metadata),
                    ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                    MyStatsSection(component_data),
                ]

                super().__init__(
                    page=page,
                    component_data=component_data,
                    title_text="My Component Details",
                    sections=sections,
                )
    """

    def __init__(
        self,
        page: ft.Page,
        component_data: ComponentStatus,
        title_text: str,
        sections: list[ft.Control],
        width: int = ModalLayout.DEFAULT_WIDTH,
        height: int = ModalLayout.DEFAULT_HEIGHT,
        scrollable: bool = True,
    ) -> None:
        """
        Initialize the base detail popup.

        Args:
            component_data: ComponentStatus containing component health and metrics
            title_text: Title text (e.g., "Scheduler Details")
            sections: List of section controls to display in modal body
            width: Modal width in pixels (default: 900)
            height: Modal height in pixels (default: 700)
            scrollable: Whether to wrap sections in scrollable container (default: True).
                        Set to False when using tabs that handle their own scrolling.
        """
        self.component_data = component_data
        self.title_text = title_text

        # Build sections container - scrollable or direct based on parameter
        if scrollable:
            sections_container = ft.Container(
                content=ft.Column(
                    sections,
                    spacing=0,
                    scroll=ft.ScrollMode.AUTO,
                ),
                expand=True,
            )
        else:
            # For tabs or content that manages its own scrolling
            sections_container = ft.Container(
                content=sections[0]
                if len(sections) == 1
                else ft.Column(sections, spacing=0),
                expand=True,
            )

        # Build modal content with title, sections, and close button
        modal_content = ft.Column(
            controls=[
                # Title with status badge
                self._create_title(),
                ft.Divider(height=1),
                # Sections (scrollable or not based on parameter)
                sections_container,
                # Actions
                ft.Container(
                    content=ft.Row(
                        [ft.TextButton("Close", on_click=self._handle_close_click)],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    padding=ft.padding.only(top=10),
                ),
            ],
            spacing=10,
            expand=True,
        )

        # Wrap in container with padding
        content_container = ft.Container(
            content=modal_content,
            padding=20,
            width=width,
            height=height,
        )

        # Initialize BasePopup with styled container
        super().__init__(
            page=page,
            content=content_container,
            width=width,
            height=height,
            border=ft.border.all(1, self._get_status_color()),
            border_radius=Theme.Components.CARD_RADIUS,
            bgcolor=ft.Colors.SURFACE,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
        )

    def _create_title(self) -> ft.Control:
        """
        Create the modal title with status badge.

        Returns a Row containing the title text with icon and a status badge
        using theme-aware colors.
        """
        status_color = self._get_status_color()

        return ft.Row(
            [
                H2Text(self.title_text),
                Tag(
                    text=self.component_data.status.value.upper(),
                    color=status_color,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _get_status_color(self) -> str:
        """
        Map component status to theme color.

        Returns:
            Theme color constant based on component status
        """
        status_map = {
            ComponentStatusType.HEALTHY: Theme.Colors.SUCCESS,
            ComponentStatusType.INFO: Theme.Colors.INFO,
            ComponentStatusType.WARNING: Theme.Colors.WARNING,
            ComponentStatusType.UNHEALTHY: Theme.Colors.ERROR,
        }
        return status_map.get(self.component_data.status, ft.Colors.ON_SURFACE_VARIANT)

    def _handle_close_click(self, e: ft.ControlEvent) -> None:
        """Handle close button click."""
        self.hide()
        if e.page:
            e.page.update()
