"""Blog Service Card."""

import flet as ft
from app.services.blog.constants import BLOG_COMPONENT_NAME
from app.services.system.models import ComponentStatus
from app.services.system.ui import get_component_subtitle

from .card_container import CardContainer
from .card_utils import (
    create_header_row,
    create_metric_container,
    get_status_colors,
)


class BlogCard:
    """Blog service card showing editorial status."""

    def __init__(self, component_data: ComponentStatus) -> None:
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _create_metrics_section(self) -> ft.Container:
        published = self.metadata.get("published_posts", 0)
        drafts = self.metadata.get("draft_posts", 0)
        tags = self.metadata.get("tag_count", 0)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            create_metric_container("Published", str(published)),
                            create_metric_container("Drafts", str(drafts)),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),
                    ft.Row(
                        [create_metric_container("Tags", str(tags))],
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            expand=True,
        )

    def _create_card_content(self) -> ft.Container:
        subtitle = get_component_subtitle(
            f"service_{BLOG_COMPONENT_NAME}", self.metadata
        )

        return ft.Container(
            content=ft.Column(
                [
                    create_header_row("Blog", subtitle, self.component_data),
                    self._create_metrics_section(),
                ],
                spacing=0,
            ),
            padding=ft.padding.all(16),
            expand=True,
        )

    def build(self) -> ft.Container:
        """Build the blog card."""
        _, _, border_color = get_status_colors(self.component_data)
        return CardContainer(
            content=self._create_card_content(),
            component_name=BLOG_COMPONENT_NAME,
            component_data=self.component_data,
            border_color=border_color,
        )
