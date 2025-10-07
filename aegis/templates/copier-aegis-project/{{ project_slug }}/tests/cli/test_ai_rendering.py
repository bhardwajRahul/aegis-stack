"""Tests for AI chat rendering utilities."""

import re
from io import StringIO

from app.cli.ai_rendering import (
    StreamingMarkdownRenderer,
    _clean_ai_content,
    render_ai_header,
    render_conversation_metadata,
    render_error_message,
    render_markdown_response,
    render_thinking_spinner,
)
from rich.console import Console


def strip_ansi_codes(text: str) -> str:
    """
    Strip ANSI escape codes from text for testing.

    Marko terminal renderer adds ANSI escape codes that make string comparison
    difficult. This helper removes all ANSI escape sequences to get clean text.

    Args:
        text: Text potentially containing ANSI codes

    Returns:
        Clean text without ANSI codes
    """
    # Pattern matches all ANSI escape sequences
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


class TestRenderAIHeader:
    """Test AI header rendering."""

    def test_inline_header(self):
        """Test inline header style (🤖:)."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_ai_header(console, inline=True)

        result = output.getvalue()
        assert "🤖: " in result
        assert "Response:" not in result
        # Should not have a newline at the end (end="" parameter)
        assert not result.endswith("\n\n")

    def test_separate_line_header(self):
        """Test separate line header style."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_ai_header(console, inline=False)

        result = output.getvalue()
        assert "🤖 " in result
        assert "Response:" in result

    def test_header_styles(self):
        """Test that headers have proper styling."""
        output = StringIO()
        console = Console(
            file=output, force_terminal=True, width=80, legacy_windows=False
        )

        render_ai_header(console, inline=True)

        result = output.getvalue()
        assert "🤖" in result


class TestRenderMarkdownResponse:
    """Test markdown response rendering with marko."""

    def test_simple_text(self):
        """Test rendering plain text."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_markdown_response(console, "Hello world")

        result = output.getvalue()
        assert "Hello world" in result

    def test_code_block(self):
        """Test rendering code blocks."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        content = "```python\nprint('hello')\n```"
        render_markdown_response(console, content)

        result = output.getvalue()
        assert "print" in result
        assert "hello" in result

    def test_empty_content(self):
        """Test handling empty content."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_markdown_response(console, "")

        result = output.getvalue()
        assert "No response content" in result

    def test_whitespace_only_content(self):
        """Test handling whitespace-only content."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_markdown_response(console, "   \n\t  ")

        result = output.getvalue()
        assert "No response content" in result

    def test_markdown_formatting(self):
        """Test various markdown elements with marko."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        content = """# Header
- Bullet point
**Bold text**
`inline code`"""
        render_markdown_response(console, content)

        result = strip_ansi_codes(output.getvalue())
        assert "Header" in result
        assert "Bullet point" in result
        assert "Bold text" in result
        assert "inline code" in result

    def test_heading_rendering(self):
        """Test that headings render with ANSI codes."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        content = "# Level 1\n## Level 2\n### Level 3"
        render_markdown_response(console, content)

        result = strip_ansi_codes(output.getvalue())
        # Headers should be semantically rendered (content only, no # markers)
        assert "Level 1" in result
        assert "Level 2" in result
        assert "Level 3" in result


class TestRenderConversationMetadata:
    """Test conversation metadata rendering."""

    def test_basic_metadata(self):
        """Test basic conversation ID only."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_conversation_metadata(console, "conv-123")

        result = strip_ansi_codes(output.getvalue())
        assert "💬 Conversation: conv-123" in result
        assert "Messages:" not in result
        assert "Response time:" not in result

    def test_full_metadata(self):
        """Test all metadata fields."""
        output = StringIO()
        console = Console(
            file=output, force_terminal=True, width=80, force_jupyter=False
        )

        render_conversation_metadata(
            console, "conv-123", message_count=5, response_time=123.4
        )

        result = strip_ansi_codes(output.getvalue())
        assert "💬 Conversation: conv-123" in result
        assert "ℹ️  Messages: 5" in result
        assert "⏱️  Response time: 123.4ms" in result

    def test_partial_metadata(self):
        """Test with only some metadata fields."""
        output = StringIO()
        console = Console(
            file=output, force_terminal=True, width=80, force_jupyter=False
        )

        render_conversation_metadata(console, "conv-456", message_count=10)

        result = strip_ansi_codes(output.getvalue())
        assert "💬 Conversation: conv-456" in result
        assert "ℹ️  Messages: 10" in result
        assert "Response time:" not in result

    def test_response_time_formatting(self):
        """Test response time is formatted to 1 decimal place."""
        output = StringIO()
        console = Console(
            file=output, force_terminal=True, width=80, force_jupyter=False
        )

        render_conversation_metadata(console, "conv-789", response_time=1234.56789)

        result = strip_ansi_codes(output.getvalue())
        assert "⏱️  Response time: 1234.6ms" in result


class TestRenderErrorMessage:
    """Test error message rendering."""

    def test_basic_error(self):
        """Test basic error message."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_error_message(console, "Connection failed")

        result = output.getvalue()
        assert "❌ Error: Connection failed" in result
        assert "💡 Suggestion:" not in result

    def test_error_with_suggestion(self):
        """Test error message with suggestion."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        render_error_message(console, "API key invalid", "Check your .env file")

        result = output.getvalue()
        assert "❌ Error: API key invalid" in result
        assert "💡 Suggestion: Check your .env file" in result


class TestRenderThinkingSpinner:
    """Test thinking spinner creation."""

    def test_spinner_creation(self):
        """Test that spinner is created correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        spinner, live = render_thinking_spinner(console)

        assert spinner is not None
        assert live is not None
        assert str(spinner.text) == "🤖 Thinking..."
        assert spinner.style == "bright_blue"

    def test_spinner_lifecycle(self):
        """Test spinner start and stop."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        spinner, live = render_thinking_spinner(console)

        # Test that we can start and stop without errors
        live.start()
        live.stop()

        assert str(spinner.text) == "🤖 Thinking..."


class TestStreamingMarkdownRenderer:
    """Test the streaming markdown renderer with marko."""

    def test_simple_text_streaming(self):
        """Test streaming of simple text without markdown."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        renderer = StreamingMarkdownRenderer(console)

        renderer.add_delta("Hello ")
        renderer.add_delta("world!")
        renderer.add_delta("\n")
        renderer.finalize()

        result = strip_ansi_codes(output.getvalue())
        assert "Hello world!" in result

    def test_header_streaming(self):
        """Test header rendering in streaming mode."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        renderer = StreamingMarkdownRenderer(console)

        renderer.add_delta("# Level 1\n")
        renderer.add_delta("## Level 2\n")
        renderer.finalize()

        result = strip_ansi_codes(output.getvalue())
        assert "Level 1" in result
        assert "Level 2" in result

    def test_bullet_point_streaming(self):
        """Test bullet point rendering during streaming."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        renderer = StreamingMarkdownRenderer(console)

        renderer.add_delta("- First bullet\n")
        renderer.add_delta("- Second bullet\n")
        renderer.finalize()

        result = strip_ansi_codes(output.getvalue())
        assert "First bullet" in result
        assert "Second bullet" in result

    def test_code_block_streaming(self):
        """Test code block rendering during streaming."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        renderer = StreamingMarkdownRenderer(console)

        renderer.add_delta("```python\n")
        renderer.add_delta("def hello():\n")
        renderer.add_delta("    return 'world'\n")
        renderer.add_delta("```\n")
        renderer.finalize()

        result = strip_ansi_codes(output.getvalue())
        assert "def hello():" in result
        assert "return 'world'" in result

    def test_incomplete_line_buffering(self):
        """Test that incomplete lines are properly buffered during streaming."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        renderer = StreamingMarkdownRenderer(console)

        # Send partial content without newline
        renderer.add_delta("This is a partial")
        # Should not output anything yet (buffered)

        # Complete the line
        renderer.add_delta(" line\n")
        result = strip_ansi_codes(output.getvalue())
        assert "This is a partial line" in result

    def test_streaming_mixed_content(self):
        """Test streaming of mixed markdown content."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        renderer = StreamingMarkdownRenderer(console)

        # Stream complex content piece by piece
        content_parts = [
            "# Main Header\n",
            "\n",
            "Some text here.\n",
            "\n",
            "- First item\n",
            "- Second item\n",
            "\n",
            "```python\n",
            "print('test')\n",
            "```\n",
        ]

        for part in content_parts:
            renderer.add_delta(part)
        renderer.finalize()

        result = strip_ansi_codes(output.getvalue())
        assert "Main Header" in result
        assert "Some text here." in result
        assert "First item" in result
        assert "Second item" in result
        assert "print('test')" in result


class TestContentCleaning:
    """Test AI content cleaning utilities."""

    def test_clean_excessive_whitespace(self):
        """Test removal of excessive whitespace."""
        messy_content = """


        Line 1


        Line 2



        Line 3


        """
        cleaned = _clean_ai_content(messy_content)

        # Should not start or end with empty lines
        assert not cleaned.startswith("\n")
        assert not cleaned.endswith("\n")

        # Should contain the content lines
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned
        assert "Line 3" in cleaned

    def test_preserve_single_empty_lines(self):
        """Test that single empty lines are preserved."""
        content = "Line 1\n\nLine 2\n\nLine 3"
        cleaned = _clean_ai_content(content)
        assert cleaned == "Line 1\n\nLine 2\n\nLine 3"

    def test_remove_trailing_whitespace(self):
        """Test removal of trailing whitespace from lines."""
        content = "Line 1   \nLine 2\t\n  Line 3     "
        cleaned = _clean_ai_content(content)
        lines = cleaned.split("\n")

        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "  Line 3"  # Leading spaces preserved, trailing removed

    def test_normalize_consecutive_empty_lines(self):
        """Test that consecutive empty lines are limited to 1."""
        content = "Line 1\n\n\n\nLine 2"
        cleaned = _clean_ai_content(content)

        # Should have exactly one empty line between content
        expected = "Line 1\n\nLine 2"
        assert cleaned == expected
