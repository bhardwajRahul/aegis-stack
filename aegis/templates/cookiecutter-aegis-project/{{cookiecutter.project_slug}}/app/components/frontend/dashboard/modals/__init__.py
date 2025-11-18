"""
Dashboard Modal Components

Reusable modal dialogs for displaying detailed component information.
Each modal inherits from ft.AlertDialog and uses component composition.
"""

from .ai_modal import AIDetailDialog
from .auth_modal import AuthDetailDialog
from .backend_modal import BackendDetailDialog
from .database_modal import DatabaseDetailDialog
from .redis_modal import RedisDetailDialog
from .scheduler_modal import SchedulerDetailDialog
from .worker_modal import WorkerDetailDialog

__all__ = [
    "AIDetailDialog",
    "AuthDetailDialog",
    "BackendDetailDialog",
    "DatabaseDetailDialog",
    "RedisDetailDialog",
    "SchedulerDetailDialog",
    "WorkerDetailDialog",
]
