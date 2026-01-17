"""Frontend UI controls for styled components."""

from .buttons import ConfirmDialog
from .data_table import DataTable, DataTableColumn
from .expandable_data_table import ExpandableDataTable, ExpandableRow
from .service_card import ServiceCard
from .table import (
    TableCellText,
    TableHeaderText,
    TableNameText,
)
from .tag import Tag
from .tech_badge import TechBadge
from .text import (
    AccentText,
    BodyText,
    ConfirmationText,
    DisplayText,
    ErrorText,
    H1Text,
    H2Text,
    H3Text,
    LabelText,
    MetricText,
    PrimaryText,
    SecondaryText,
    SuccessText,
    TitleText,
    WarningText,
)

__all__ = [
    # Legacy controls (refactored to use theme)
    "PrimaryText",
    "SecondaryText",
    "TitleText",
    "ConfirmationText",
    "MetricText",
    "LabelText",
    # New theme-based controls
    "DisplayText",
    "H1Text",
    "H2Text",
    "H3Text",
    "BodyText",
    "AccentText",
    "SuccessText",
    "WarningText",
    "ErrorText",
    # Table controls
    "DataTable",
    "DataTableColumn",
    "ExpandableDataTable",
    "ExpandableRow",
    "TableHeaderText",
    "TableCellText",
    "TableNameText",
    # Badge/Tag controls
    "Tag",
    "TechBadge",
    # Card layout controls
    "ServiceCard",
    # Dialog controls
    "ConfirmDialog",
]
