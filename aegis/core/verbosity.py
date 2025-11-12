"""Verbosity control for Aegis CLI output.

This module provides a simple global verbosity flag that controls
the level of detail in CLI output across all commands.
"""

from typing import Any

# Global verbosity state
_verbose: bool = False


def set_verbose(enabled: bool) -> None:
    """Set the global verbosity flag.

    Args:
        enabled: True to enable verbose output, False for normal output
    """
    global _verbose
    _verbose = enabled


def is_verbose() -> bool:
    """Check if verbose mode is enabled.

    Returns:
        True if verbose mode is enabled, False otherwise
    """
    return _verbose


def verbose_print(*args: Any, **kwargs: Any) -> None:
    """Print only if verbose mode is enabled.

    Args:
        *args: Arguments to pass to print()
        **kwargs: Keyword arguments to pass to print()
    """
    if _verbose:
        print(*args, **kwargs)
