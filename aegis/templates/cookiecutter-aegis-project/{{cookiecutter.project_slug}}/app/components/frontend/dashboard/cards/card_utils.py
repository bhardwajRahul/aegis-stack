"""
Card Utility Functions

Simple shared functions to eliminate code duplication across dashboard cards.
No inheritance or ABC complexity - just common functionality extracted.
"""

from collections.abc import Callable
from typing import Any

import flet as ft

from app.components.frontend.controls import LabelText, SecondaryText, TitleText
from app.services.system.models import ComponentStatus, ComponentStatusType


def get_status_colors(component_data: ComponentStatus) -> tuple[str, str, str]:
    """
    Get status-aware colors for any card.

    Args:
        component_data: ComponentStatus containing status information

    Returns:
        Tuple of (primary_color, background_color, border_color)
    """
    status = component_data.status

    if status == ComponentStatusType.HEALTHY:
        return (ft.Colors.GREEN, ft.Colors.SURFACE, ft.Colors.GREEN)
    elif status == ComponentStatusType.INFO:
        return (ft.Colors.BLUE, ft.Colors.SURFACE, ft.Colors.BLUE)
    elif status == ComponentStatusType.WARNING:
        return (ft.Colors.ORANGE, ft.Colors.SURFACE, ft.Colors.ORANGE)
    else:  # UNHEALTHY
        return (ft.Colors.RED, ft.Colors.SURFACE, ft.Colors.RED)


def create_hover_handler(
    card_container: ft.Container,
) -> Callable[[ft.ControlEvent], None] | None:
    """
    Create a hover event handler for any card.

    Args:
        card_container: The card container (unused now)

    Returns:
        None (hover effects disabled)
    """
    return None


def create_responsive_3_section_layout(
    left_content: ft.Control, middle_content: ft.Control, right_content: ft.Control
) -> ft.Row:
    """
    Create responsive 3-section card layout prioritizing middle section.

    Args:
        left_content: Technology badge content
        middle_content: Main metrics/data content (gets priority)
        right_content: Details/performance content

    Returns:
        Row with responsive flex layout
    """
    return ft.Row(
        [
            # Left: Tech badge (flexible, can shrink to minimum)
            ft.Container(
                content=left_content,
                expand=2,  # ~20% of space, can shrink
                width=100,  # Minimum width to keep badge readable
            ),
            ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
            # Middle: Metrics (PRIORITY - gets most space and protection)
            ft.Container(
                content=middle_content,
                expand=5,  # ~50% of space, PRIORITY SECTION
                padding=ft.padding.all(16),
                width=300,  # Minimum width to keep metrics functional
            ),
            ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
            # Right: Details (flexible, shrinks most aggressively)
            ft.Container(
                content=right_content,
                expand=3,  # ~30% of space, can shrink aggressively
                padding=ft.padding.all(16),
                width=150,  # Minimum width to prevent complete disappearance
            ),
        ]
    )


def create_tech_badge(
    title: str,
    subtitle: str,
    icon: str,
    badge_text: str,
    badge_color: str,
    primary_color: str,
    width: int | None = 160,
) -> ft.Container:
    """
    Create a standardized technology badge section.

    Args:
        title: Main technology title (e.g., "FastAPI", "Worker")
        subtitle: Technology subtitle (e.g., "Backend API", "arq + Redis")
        icon: Emoji icon for the technology
        badge_text: Badge label text (e.g., "ACTIVE", "QUEUES")
        badge_color: Background color for the badge
        primary_color: Primary color for the icon background
        width: Width of the badge container

    Returns:
        Container with the technology badge
    """
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


def create_stats_row(label: str, value: str, value_color: str | None = None) -> ft.Row:
    """
    Create a standardized statistics row with label and value.

    Args:
        label: The label text (e.g., "Active Workers")
        value: The value text (e.g., "2")
        value_color: Optional color for the value text

    Returns:
        Row with label and value properly aligned
    """
    value_control = LabelText(value)
    if value_color:
        value_control.color = value_color

    return ft.Row(
        [
            SecondaryText(f"{label}:"),
            value_control,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def create_standard_card_container(
    content: ft.Row,
    primary_color: str,
    border_color: str,
    width: int | None,
    hover_handler: Callable[..., Any] | None,
) -> ft.Container:
    """
    Create a standardized card container with consistent styling.

    Args:
        content: The main row content of the card
        primary_color: Primary color for the card
        border_color: Border color for the card
        width: Width of the card
        hover_handler: Hover event handler function

    Returns:
        Styled card container
    """
    return ft.Container(
        content=content,
        bgcolor=ft.Colors.SURFACE,
        border=ft.border.all(1, border_color),
        border_radius=16,
        padding=0,
        scale=1,
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_hover=hover_handler,
        width=width,
        height=280,
    )


def create_health_status_indicator(
    healthy_count: int, total_count: int
) -> ft.Container:
    """
    Create a circular health status indicator with color coding.

    Args:
        healthy_count: Number of healthy components
        total_count: Total number of components

    Returns:
        Container with circular progress and component count
    """
    if total_count == 0:
        percentage = 0.0
    else:
        percentage = (healthy_count / total_count) * 100

    # Color coding based on health percentage
    if percentage >= 100:
        color = ft.Colors.GREEN  # All healthy
        status_text = "Healthy"
        status_color = ft.Colors.GREEN
    elif percentage >= 70:
        color = ft.Colors.AMBER  # Mostly healthy
        status_text = "Warning"
        status_color = ft.Colors.ORANGE
    else:
        color = ft.Colors.RED  # Significant issues
        status_text = "Critical"
        status_color = ft.Colors.RED

    return ft.Container(
        content=ft.Row(
            [
                ft.ProgressRing(
                    value=percentage / 100,
                    color=color,
                    bgcolor=ft.Colors.with_opacity(0.3, color),
                    stroke_width=6,
                    width=50,
                    height=50,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"{healthy_count}/{total_count}",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE,
                            ),
                            ft.Text(
                                status_text,
                                size=12,
                                color=status_color,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=2,
                    ),
                    margin=ft.margin.only(left=12),
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )


def create_progress_indicator(
    label: str, value: float, details: str, color: str
) -> ft.Container:
    """
    Create a progress indicator with label, progress bar, and details.

    Args:
        label: Label for the progress indicator
        value: Progress value (0-100)
        details: Additional details text
        color: Color for the progress bar

    Returns:
        Container with the progress indicator
    """
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    label,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.GREY_600,
                ),
                ft.Container(
                    content=ft.ProgressBar(
                        value=value / 100.0,
                        height=8,
                        color=color,
                        bgcolor=ft.Colors.GREY_300,
                        border_radius=4,
                    ),
                    margin=ft.margin.only(top=4, bottom=4),
                ),
                ft.Row(
                    [
                        ft.Text(
                            f"{value:.1f}%",
                            size=16,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.ON_SURFACE,
                        ),
                        ft.Text(
                            details,
                            size=14,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=2,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        expand=True,
    )
