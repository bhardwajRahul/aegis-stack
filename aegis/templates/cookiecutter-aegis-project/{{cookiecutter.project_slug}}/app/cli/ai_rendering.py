"""
Shared rendering utilities for AI chat responses.

Provides consistent, beautiful output formatting across streaming
and non-streaming modes using marko markdown parser with terminal rendering.
"""

import re

from marko import Markdown
from marko.ext.gfm import GFM
from rich.console import Console

from app.cli.marko_terminal_renderer import TerminalRenderer


class StreamingMarkdownRenderer:
    """
    Line-based streaming markdown renderer using marko.

    Processes markdown content as it streams in, using marko to parse complete
    blocks and render them with beautiful ANSI styling for terminal output.
    """

    def __init__(self, console: Console):
        """
        Initialize streaming renderer.

        Args:
            console: Rich console instance for output management
        """
        self.console = console
        self.buffer = ""
        self.in_code_block = False
        self.code_buffer = []
        self.code_lang = ""
        self.markdown = Markdown(extensions=[GFM], renderer=TerminalRenderer)

    def add_delta(self, delta: str) -> None:
        """
        Process streaming delta and display formatted content with smart buffering.

        Uses line-buffering for markdown structures (code blocks, lists, tables)
        and word-streaming for plain conversational text for smooth output.

        Args:
            delta: New text content to process
        """
        # Add new content to buffer
        self.buffer += delta

        # Smart buffering based on content type
        if self.in_code_block or self._is_markdown_structure():
            # Use line-buffering for markdown structures (safe, correct formatting)
            self._process_complete_lines()
        else:
            # Use word-streaming for plain text (smooth, responsive)
            self._stream_plain_text()

    def _is_markdown_structure(self) -> bool:
        """
        Detect if buffer contains markdown structures requiring line-buffering.

        Returns:
            True if buffer contains markdown patterns, False for plain text
        """
        if not self.buffer.strip():
            return False

        # Get the current line being built (text after last newline)
        current_line = self.buffer.split("\n")[-1].strip()

        # Markdown patterns that need careful line-by-line handling
        markdown_indicators = [
            "```",  # Code blocks (critical!)
            "#",  # Headers
            "- ",  # Unordered lists
            "* ",  # Unordered lists (alternate)
            "+ ",  # Unordered lists (alternate)
            "> ",  # Blockquotes
            "|",  # Tables
        ]

        # Check if line starts with markdown
        for indicator in markdown_indicators:
            if current_line.startswith(indicator):
                return True

        # Check for numbered lists using regex (handles any number)
        # Check for inline formatting that might break across words
        # (bold/italic can be streamed word-by-word safely)
        return bool(re.match(r"^\d+\. ", current_line))

    def _stream_plain_text(self) -> None:
        """
        Stream plain text word-by-word for smooth, responsive output.

        Renders complete words immediately while keeping incomplete words
        in buffer. Falls back to line-buffering when newlines are encountered.
        """
        # If we hit a newline, process complete lines normally
        if "\n" in self.buffer:
            self._process_complete_lines()
            return

        # Word-level streaming for smooth plain text output
        # Split on spaces to identify complete words
        if " " in self.buffer:
            # Split and find word boundaries
            parts = self.buffer.rsplit(" ", 1)  # Split from right to keep last word

            if len(parts) == 2:
                complete_text, incomplete_word = parts

                # Render complete text with trailing space
                if complete_text:
                    # For plain text, just write directly (no markdown parsing needed)
                    self.console.file.write(complete_text + " ")
                    self.console.file.flush()

                # Keep incomplete word in buffer
                self.buffer = incomplete_word

    def _process_complete_lines(self) -> None:
        """Process any complete lines in the buffer."""
        lines = self.buffer.split("\n")

        # Keep the last (potentially incomplete) line in buffer
        if len(lines) > 1:
            complete_lines = lines[:-1]
            self.buffer = lines[-1]

            # Process each complete line
            for line in complete_lines:
                self._render_line(line)

    def _render_line(self, line: str) -> None:
        """
        Render a complete line with markdown formatting using marko.

        Args:
            line: Complete line to render
        """
        # Handle code blocks (accumulate until closing)
        if self.in_code_block:
            if line.strip() == "```":
                # End of code block - render complete block
                self._render_code_block()
                self.in_code_block = False
                self.code_buffer = []
                self.code_lang = ""
            else:
                # Inside code block, accumulate
                self.code_buffer.append(line)
            return

        if line.strip().startswith("```"):
            # Start of code block
            self.code_lang = line.strip()[3:].strip() or "text"
            self.in_code_block = True
            self.code_buffer = []
            return

        # For other content, parse line as markdown and render
        if line.strip():
            # Parse and render single line with marko
            rendered = self.markdown(line)
            # Write to console's file to support both terminal and testing
            self.console.file.write(rendered)
            self.console.file.flush()
        else:
            # Empty line
            self.console.print()

    def _render_code_block(self) -> None:
        """Render accumulated code block using marko."""
        code_content = "\n".join(self.code_buffer)

        # Create markdown code block
        markdown_code = f"```{self.code_lang}\n{code_content}\n```"

        # Parse and render with marko
        rendered = self.markdown(markdown_code)
        # Write to console's file to support both terminal and testing
        self.console.file.write(rendered)
        self.console.file.flush()

    def finalize(self) -> None:
        """Finalize any remaining content in buffer."""
        if self.buffer.strip():
            # Process any remaining incomplete line
            rendered = self.markdown(self.buffer.strip())
            # Write to console's file to support both terminal and testing
            self.console.file.write(rendered)
            self.console.file.flush()

        # Handle unclosed code block
        if self.in_code_block and self.code_buffer:
            self._render_code_block()


def render_ai_header(console: Console, inline: bool = True) -> None:
    """
    Render the AI response header.

    Args:
        console: Rich console instance
        inline: If True, use inline style (>), else use separate line style

    Examples:
        >>> render_ai_header(console, inline=True)  # Outputs: "> "
        >>> render_ai_header(console, inline=False) # Outputs: "> Response:"
    """
    if inline:
        console.print("> ", style="bright_blue", end="")
    else:
        console.print("> ", style="bright_blue", end="")
        console.print("Response:", style="bright_blue bold")


def render_markdown_response(console: Console, content: str) -> None:
    """
    Render markdown content with beautiful terminal styling using marko.

    Parses complete markdown content and renders with ANSI-styled output
    for beautiful terminal display.

    Args:
        console: Rich console instance
        content: Markdown content to render

    Examples:
        >>> render_markdown_response(console, "# Hello World")
        >>> render_markdown_response(console, "```python\\nprint('hi')\\n```")
    """
    if not content or not content.strip():
        console.print("(No response content)", style="dim italic")
        return

    # Clean up excessive whitespace from AI responses
    cleaned_content = _clean_ai_content(content)

    # Parse and render with marko (GFM for table support)
    markdown = Markdown(extensions=[GFM], renderer=TerminalRenderer)
    rendered = markdown(cleaned_content)

    # Write to console's file to support both terminal and testing
    console.file.write(rendered)
    console.file.flush()


def _clean_ai_content(content: str) -> str:
    """
    Clean up excessive whitespace and formatting issues from AI responses.

    Some AI providers send responses with excessive blank lines or spacing
    that hurts readability. This function normalizes the content.

    Args:
        content: Raw AI response content

    Returns:
        Cleaned content with normalized spacing
    """

    # Split into lines for processing
    lines = content.split("\n")
    cleaned_lines = []
    consecutive_empty = 0

    for line in lines:
        is_empty = not line.strip()

        if is_empty:
            consecutive_empty += 1
            # Allow maximum 1 consecutive empty line
            if consecutive_empty <= 1:
                cleaned_lines.append("")
        else:
            consecutive_empty = 0
            # Clean up the line (remove trailing whitespace)
            cleaned_lines.append(line.rstrip())

    # Remove leading and trailing empty lines
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    # Join back together
    return "\n".join(cleaned_lines)


def render_conversation_metadata(
    console: Console,
    conversation_id: str,
    message_count: int | None = None,
    response_time: float | None = None,
) -> None:
    """
    Render conversation metadata consistently.

    Args:
        console: Rich console instance
        conversation_id: The conversation identifier
        message_count: Number of messages in conversation
        response_time: Response time in milliseconds

    Examples:
        >>> render_conversation_metadata(console, "conv-123")
        >>> render_conversation_metadata(
        ...     console, "conv-123", message_count=5, response_time=150.5
        ... )
    """
    console.print()  # Blank line for spacing
    console.print(f"Conversation: {conversation_id}", style="dim")
    if message_count:
        console.print(f"Messages: {message_count}", style="dim")
    if response_time:
        console.print(f"Response time: {response_time:.1f}ms", style="dim")


def render_error_message(
    console: Console, error: str, suggestion: str | None = None
) -> None:
    """
    Render an error message consistently.

    Args:
        console: Rich console instance
        error: The error message to display
        suggestion: Optional suggestion for fixing the error

    Examples:
        >>> render_error_message(console, "Connection failed")
        >>> render_error_message(console, "API key invalid", "Check your .env file")
    """
    console.print(f"Error: {error}", style="red")
    if suggestion:
        console.print(f"Tip: {suggestion}", style="yellow dim")


def render_thinking_spinner(console: Console) -> tuple:
    """
    Create a thinking spinner for AI processing.

    Returns:
        Tuple of (Spinner, Live) objects to control the spinner

    Examples:
        >>> spinner, live = render_thinking_spinner(console)
        >>> live.start()
        >>> # ... do work ...
        >>> live.stop()
    """
    from rich.live import Live
    from rich.spinner import Spinner

    spinner = Spinner("dots", text="Thinking...", style="bright_blue")
    live = Live(spinner, console=console, refresh_per_second=12)
    return spinner, live
