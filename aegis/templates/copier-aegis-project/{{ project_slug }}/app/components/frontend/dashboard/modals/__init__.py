"""
Dashboard Modal Components

Reusable modal dialogs for displaying detailed component information.
Each modal inherits from ft.AlertDialog and uses component composition.
"""

from .scheduler_modal import SchedulerDetailDialog
from .worker_modal import WorkerDetailDialog

__all__ = [
    "SchedulerDetailDialog",
    "WorkerDetailDialog",
]
