"""Status line UI component for Illiana CLI chat.

Provides a persistent status bar at the bottom of the terminal during
interactive chat sessions, showing token count, model info, RAG status,
and version.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass

from prompt_toolkit.formatted_text import HTML


@dataclass
class ChatSessionState:
    """Mutable state for the chat session status line."""

    provider: str = ""
    model: str = ""
    rag_enabled: bool = False
    rag_collection: str | None = None
    cumulative_tokens: int = 0
    cumulative_cost: float = 0.0
    version: str = ""

    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Add tokens from a chat exchange."""
        self.cumulative_tokens += input_tokens + output_tokens

    def add_cost(self, cost: float) -> None:
        """Add cost from a chat exchange."""
        self.cumulative_cost += cost

    def format_status_line(self) -> HTML:
        """Format the status line with HTML markup for prompt_toolkit."""
        term_width = shutil.get_terminal_size().columns

        # Build components
        if self.provider:
            model_str = f"{self.provider}/{self.model}"
        else:
            model_str = "not connected"

        if self.rag_enabled and self.rag_collection:
            rag_str = f"RAG: ON ({self.rag_collection})"
        elif self.rag_enabled:
            rag_str = "RAG: ON"
        else:
            rag_str = "RAG: OFF"

        tokens_str = f"{self.cumulative_tokens:,} tokens"
        cost_str = f"${self.cumulative_cost:.4f}"
        version_str = f"v{self.version}"

        # Separator (middle dot)
        sep = " <style bg='default' fg='ansibrightblack'>\u00b7</style> "

        # Build parts with colors
        parts = [
            f"<style fg='ansicyan'>{model_str}</style>",
            f"<style fg='ansigreen'>{rag_str}</style>"
            if self.rag_enabled
            else f"<style fg='ansibrightblack'>{rag_str}</style>",
            f"<style fg='ansiyellow'>{tokens_str}</style>",
            f"<style fg='ansigreen'>{cost_str}</style>",
            f"<style fg='ansibrightblack'>{version_str}</style>",
        ]

        # For narrow terminals, abbreviate
        if term_width < 60:
            # Abbreviated format: model | tokens | cost
            parts = [
                f"<style fg='ansicyan'>{self.model or 'n/a'}</style>",
                f"<style fg='ansiyellow'>{tokens_str}</style>",
                f"<style fg='ansigreen'>{cost_str}</style>",
            ]
        elif term_width < 80:
            # Skip version
            parts = parts[:-1]

        status_content = sep.join(parts)

        # Add divider line above status
        divider = "─" * term_width
        full_line = f"<style fg='ansibrightblack'>{divider}</style>\n{status_content}\n"
        return HTML(full_line)


def create_toolbar_callback(state: ChatSessionState) -> Callable[[], HTML]:
    """Create a bottom_toolbar callback that reads from state.

    Args:
        state: The ChatSessionState instance to read from.

    Returns:
        A callable that returns the formatted status line.
    """

    def get_toolbar() -> HTML:
        return state.format_status_line()

    return get_toolbar
