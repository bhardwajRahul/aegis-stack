"""Modal components for the Overseer dashboard."""

from app.components.frontend.dashboard.modals.base_modal import BaseDetailDialog
from app.components.frontend.dashboard.modals.modal_sections import (
    EmptyStatePlaceholder,
    MetricCardSection,
    StatRowsSection,
)

__all__ = [
    "BaseDetailDialog",
    "MetricCardSection",
    "StatRowsSection",
    "EmptyStatePlaceholder",
]
