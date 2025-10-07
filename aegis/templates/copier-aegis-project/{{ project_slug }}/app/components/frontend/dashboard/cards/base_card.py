"""
Base Card Abstract Class

Provides common functionality for all dashboard component cards,
eliminating code duplication and ensuring consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Any

import flet as ft
from app.components.frontend.controls import LabelText, SecondaryText, TitleText
from app.services.system.models import ComponentStatus, ComponentStatusType


class BaseCard(ABC):
    """
    Abstract base class for all dashboard component cards.

    Provides common functionality including:
    - Status-aware coloring
    - Hover effects and animations
    - Technology badge creation
    - Standard card layout and styling
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the base card with component data.

        Args:
            component_data: ComponentStatus containing health and metrics
        """
        self.component_data = component_data
        self._card_container: ft.Container | None = None

    def _get_status_colors(self) -> tuple[str, str, str]:
        """
        Get status-aware colors for the card.

        Returns:
            Tuple of (primary_color, background_color, border_color)
        """
        status = self.component_data.status

        if status == ComponentStatusType.HEALTHY:
            return (ft.Colors.GREEN, ft.Colors.SURFACE, ft.Colors.GREEN)
        elif status == ComponentStatusType.INFO:
            return (ft.Colors.BLUE, ft.Colors.SURFACE, ft.Colors.BLUE)
        elif status == ComponentStatusType.WARNING:
            return (ft.Colors.ORANGE, ft.Colors.SURFACE, ft.Colors.ORANGE)
        else:  # UNHEALTHY
            return (ft.Colors.RED, ft.Colors.SURFACE, ft.Colors.RED)

    def _create_technology_badge(
        self,
        title: str,
        subtitle: str,
        badge_text: str,
        icon: str,
        badge_color: str,
        width: int = 160,
    ) -> ft.Container:
        """
        Create a standardized technology badge section.

        Args:
            title: Main technology title (e.g., "FastAPI", "Worker")
            subtitle: Technology subtitle (e.g., "Backend API", "arq + Redis")
            badge_text: Badge label text (e.g., "ACTIVE", "QUEUES")
            icon: Emoji icon for the technology
            badge_color: Background color for the badge
            width: Width of the badge container

        Returns:
            Container with the technology badge
        """
        primary_color, _, _ = self._get_status_colors()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(icon, size=32),
                        padding=ft.padding.all(8),
                        bgcolor=primary_color,
                        border_radius=12,
                        margin=ft.margin.only(bottom=8),
                    ),
                    TitleText(title),
                    SecondaryText(subtitle),
                    ft.Container(
                        content=LabelText(
                            badge_text,
                            color=ft.Colors.WHITE,
                        ),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=badge_color,
                        border_radius=8,
                        margin=ft.margin.only(top=4),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.padding.all(16),
            width=width,
            alignment=ft.alignment.center,
        )

    def _create_section_container(
        self,
        content: list[ft.Control],
        width: int,
        title: str | None = None,
    ) -> ft.Container:
        """
        Create a standardized section container with optional title.

        Args:
            content: List of controls to include in the section
            width: Width of the section container
            title: Optional section title

        Returns:
            Container with the section content
        """
        section_content = []
        if title:
            section_content.extend(
                [
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                ]
            )
        section_content.extend(content)

        return ft.Container(
            content=ft.Column(
                section_content,
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            ),
            width=width,
            padding=ft.padding.all(16),
            alignment=ft.alignment.top_left,
        )

    @abstractmethod
    def _get_technology_info(self) -> dict[str, Any]:
        """
        Get technology-specific information for the badge.

        Returns:
            Dictionary with keys: title, subtitle, badge_text, icon, badge_color
        """
        pass

    @abstractmethod
    def _create_middle_section(self) -> ft.Container:
        """
        Create the middle section content (component-specific).

        Returns:
            Container with the middle section content
        """
        pass

    @abstractmethod
    def _create_right_section(self) -> ft.Container:
        """
        Create the right section content (component-specific).

        Returns:
            Container with the right section content
        """
        pass

    def _get_responsive_widths(self) -> dict[str, int]:
        """
        Get responsive widths for the 3-section layout.

        Returns:
            Dictionary with 'left', 'middle', 'right', and 'total' widths
        """
        # Default responsive widths - can be overridden by subclasses
        return {
            "left": 140,  # Technology badge - fixed but smaller
            "middle": 420,  # Main content - gets most space (was 400)
            "right": 220,  # Details - compact but functional (was 240)
            "total": 800,  # Total card width
        }

    @abstractmethod
    def _get_card_width(self) -> int:
        """
        Get the total width for this card type.

        Returns:
            Card width in pixels
        """
        return self._get_responsive_widths()["total"]

    def build(self) -> ft.Container:
        """Build and return the complete card with responsive 3-section layout."""
        primary_color, background_color, border_color = self._get_status_colors()
        tech_info = self._get_technology_info()
        widths = self._get_responsive_widths()

        # Create sections with responsive widths
        left_section = ft.Container(
            content=self._create_technology_badge(
                title=tech_info["title"],
                subtitle=tech_info["subtitle"],
                badge_text=tech_info["badge_text"],
                icon=tech_info["icon"],
                badge_color=tech_info["badge_color"],
                width=widths["left"],
            ),
            width=widths["left"],
        )

        middle_section = ft.Container(
            content=self._create_middle_section(),
            width=widths["middle"],
            expand=True,  # Make middle section flexible
        )

        right_section = ft.Container(
            content=self._create_right_section(),
            width=widths["right"],
        )

        self._card_container = ft.Container(
            content=ft.Row(
                [
                    left_section,
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                    middle_section,
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                    right_section,
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, border_color),
            border_radius=16,
            padding=0,
            width=widths["total"],
            height=240,
        )

        return self._card_container
