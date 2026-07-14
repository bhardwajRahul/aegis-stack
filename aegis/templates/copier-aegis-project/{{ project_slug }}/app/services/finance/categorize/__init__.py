"""Finance categorization + reconciliation passes (transfers, rules, …)."""

from app.services.finance.categorize.insights import (
    InsightGenerationResult,
    generate_insights,
)
from app.services.finance.categorize.recurring import (
    RecurringDetectionResult,
    detect_recurring,
)
from app.services.finance.categorize.transfers import (
    TransferDetectionResult,
    detect_transfers,
)

__all__ = [
    "InsightGenerationResult",
    "RecurringDetectionResult",
    "TransferDetectionResult",
    "detect_recurring",
    "detect_transfers",
    "generate_insights",
]
