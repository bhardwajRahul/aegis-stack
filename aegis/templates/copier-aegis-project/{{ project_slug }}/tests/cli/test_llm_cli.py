"""Tests for LLM catalog CLI commands."""

from unittest.mock import patch

from app.cli.main import app
from app.services.ai.llm_service import ModalityListResult, VendorListResult
from typer.testing import CliRunner

runner = CliRunner()


class TestLLMVendorsCommand:
    """Tests for the 'llm vendors' command."""

    def test_vendors_help(self) -> None:
        """Test that vendors help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "vendors", "--help"])
        assert result.exit_code == 0
        assert "List all LLM vendors" in result.output

    @patch("app.cli.llm.list_vendors")
    def test_vendors_empty_catalog(self, mock_list_vendors) -> None:
        """Test vendors command with empty catalog."""
        mock_list_vendors.return_value = []

        result = runner.invoke(app, ["llm", "vendors"])

        assert result.exit_code == 0
        assert "No vendors found" in result.output
        assert "llm sync" in result.output

    @patch("app.cli.llm.list_vendors")
    def test_vendors_with_data(self, mock_list_vendors) -> None:
        """Test vendors command with vendor data."""
        mock_list_vendors.return_value = [
            VendorListResult(name="anthropic", model_count=22),
            VendorListResult(name="openai", model_count=15),
        ]

        result = runner.invoke(app, ["llm", "vendors"])

        assert result.exit_code == 0
        assert "anthropic" in result.output
        assert "22" in result.output
        assert "openai" in result.output
        assert "15" in result.output
        assert "2 total" in result.output


class TestLLMModalitiesCommand:
    """Tests for the 'llm modalities' command."""

    def test_modalities_help(self) -> None:
        """Test that modalities help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "modalities", "--help"])
        assert result.exit_code == 0
        assert "List all modalities" in result.output

    @patch("app.cli.llm.list_modalities")
    def test_modalities_empty_catalog(self, mock_list_modalities) -> None:
        """Test modalities command with empty catalog."""
        mock_list_modalities.return_value = []

        result = runner.invoke(app, ["llm", "modalities"])

        assert result.exit_code == 0
        assert "No modalities found" in result.output
        assert "llm sync" in result.output

    @patch("app.cli.llm.list_modalities")
    def test_modalities_with_data(self, mock_list_modalities) -> None:
        """Test modalities command with modality data."""
        mock_list_modalities.return_value = [
            ModalityListResult(modality="audio", model_count=72),
            ModalityListResult(modality="image", model_count=451),
            ModalityListResult(modality="text", model_count=1748),
            ModalityListResult(modality="video", model_count=10),
        ]

        result = runner.invoke(app, ["llm", "modalities"])

        assert result.exit_code == 0
        assert "audio" in result.output
        assert "72" in result.output
        assert "text" in result.output
        assert "1748" in result.output
        # Rich table may wrap "(4 total)" across lines
        assert "4" in result.output and "total" in result.output


class TestLLMStatusCommand:
    """Tests for the 'llm status' command."""

    def test_status_help(self) -> None:
        """Test that status help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "status", "--help"])
        assert result.exit_code == 0
        assert "Show LLM catalog statistics" in result.output


class TestLLMSyncCommand:
    """Tests for the 'llm sync' command."""

    def test_sync_help(self) -> None:
        """Test that sync help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "sync", "--help"])
        assert result.exit_code == 0
        assert "Sync LLM catalog" in result.output
        assert "--mode" in result.output
        assert "--dry-run" in result.output
        assert "--refresh" in result.output


class TestLLMListCommand:
    """Tests for the 'llm list' command."""

    def test_list_help(self) -> None:
        """Test that list help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "list", "--help"])
        assert result.exit_code == 0
        assert "List LLM models" in result.output
        assert "--vendor" in result.output
        assert "--modality" in result.output


class TestLLMUseCommand:
    """Tests for the 'llm use' command."""

    def test_use_help(self) -> None:
        """Test that use help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "use", "--help"])
        assert result.exit_code == 0
        assert "Switch to a different LLM model" in result.output
        assert "--force" in result.output


class TestLLMInfoCommand:
    """Tests for the 'llm info' command."""

    def test_info_help(self) -> None:
        """Test that info help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "info", "--help"])
        assert result.exit_code == 0
        assert "Show detailed information" in result.output


class TestLLMCurrentCommand:
    """Tests for the 'llm current' command."""

    def test_current_help(self) -> None:
        """Test that current help text is displayed correctly."""
        result = runner.invoke(app, ["llm", "current", "--help"])
        assert result.exit_code == 0
        assert "Show current LLM configuration" in result.output
