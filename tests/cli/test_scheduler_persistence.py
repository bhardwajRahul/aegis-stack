"""
Test scheduler persistence configuration based on user selection.

These tests verify that the scheduler only uses database persistence
when the user explicitly selects database FOR scheduler persistence,
not just when a database component exists independently.
"""

from typing import Any
from unittest.mock import patch

from aegis.__main__ import interactive_component_selection
from aegis.core.template_generator import TemplateGenerator


class TestSchedulerPersistenceTracking:
    """Test scheduler persistence context tracking in interactive flow."""

    @patch("typer.confirm")
    def test_scheduler_with_persistence_selected(self, mock_confirm: Any) -> None:
        """Test scheduler + persistence sets scheduler_with_persistence=True."""
        # Simulate: no redis, no worker, yes scheduler, yes persistence, yes sqlite
        mock_confirm.side_effect = [False, False, True, True, True]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "scheduler" in components
        assert "database[sqlite]" in components
        assert scheduler_with_persistence is True

    @patch("typer.confirm")
    def test_scheduler_without_persistence(self, mock_confirm: Any) -> None:
        """Test scheduler without persistence keeps scheduler_with_persistence=False."""
        # Simulate: no redis, no worker, yes scheduler, no persistence, no database
        mock_confirm.side_effect = [False, False, True, False, False]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "scheduler" in components
        assert "database[sqlite]" not in components
        assert scheduler_with_persistence is False

    @patch("typer.confirm")
    def test_scheduler_persistence_declined_sqlite(self, mock_confirm: Any) -> None:
        """Test scheduler persistence declined at SQLite confirmation."""
        # Simulate: scheduler, persistence, no sqlite, no database
        mock_confirm.side_effect = [False, False, True, True, False, False]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "scheduler" in components
        assert "database[sqlite]" not in components
        assert scheduler_with_persistence is False

    @patch("typer.confirm")
    def test_scheduler_not_selected(self, mock_confirm: Any) -> None:
        """Test no scheduler selection keeps scheduler_with_persistence=False."""
        # Simulate: no redis, no worker, no scheduler, yes database
        mock_confirm.side_effect = [False, False, False, True]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "scheduler" not in components
        assert "database" in components
        assert scheduler_with_persistence is False

    @patch("typer.confirm")
    def test_database_selected_independently_of_scheduler(
        self, mock_confirm: Any
    ) -> None:
        """Test database selected independently doesn't affect scheduler persistence."""
        # Simulate: no redis, no worker, no scheduler, yes database
        mock_confirm.side_effect = [False, False, False, True]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "scheduler" not in components
        assert "database" in components
        assert scheduler_with_persistence is False

    @patch("typer.confirm")
    def test_both_scheduler_and_independent_database(self, mock_confirm: Any) -> None:
        """Test scheduler without persistence + independent database."""
        # Simulate: no redis, no worker, yes scheduler, no persistence, yes database
        mock_confirm.side_effect = [False, False, True, False, True]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "scheduler" in components
        assert "database" in components
        assert scheduler_with_persistence is False

    @patch("typer.confirm")
    def test_full_stack_with_scheduler_persistence(self, mock_confirm: Any) -> None:
        """Test full stack selection with scheduler persistence."""
        # Simulate: yes redis, yes worker, yes scheduler, yes persistence, yes sqlite
        mock_confirm.side_effect = [True, True, True, True, True]

        components, scheduler_with_persistence = interactive_component_selection()

        assert "redis" in components
        assert "worker" in components
        assert "scheduler" in components
        assert "database[sqlite]" in components
        assert scheduler_with_persistence is True


class TestTemplateGeneratorPersistenceContext:
    """Test template generator handling of scheduler persistence context."""

    def test_template_context_with_scheduler_persistence(self) -> None:
        """Test template context when scheduler_with_persistence=True."""
        components = ["scheduler", "database[sqlite]"]
        template_gen = TemplateGenerator(
            "test-project", components, scheduler_with_persistence=True
        )

        context = template_gen.get_template_context()

        assert context["include_scheduler"] == "yes"
        assert context["include_database"] == "yes"
        assert context["scheduler_with_persistence"] == "yes"
        assert context["database_engine"] == "sqlite"

    def test_template_context_without_scheduler_persistence(self) -> None:
        """Test template context when scheduler_with_persistence=False."""
        components = ["scheduler"]
        template_gen = TemplateGenerator(
            "test-project", components, scheduler_with_persistence=False
        )

        context = template_gen.get_template_context()

        assert context["include_scheduler"] == "yes"
        assert context["include_database"] == "no"
        assert context["scheduler_with_persistence"] == "no"

    def test_template_context_database_without_scheduler_persistence(self) -> None:
        """Test template context with database but no scheduler persistence."""
        components = ["scheduler", "database[sqlite]"]
        template_gen = TemplateGenerator(
            "test-project", components, scheduler_with_persistence=False
        )

        context = template_gen.get_template_context()

        assert context["include_scheduler"] == "yes"
        assert context["include_database"] == "yes"
        assert context["scheduler_with_persistence"] == "no"  # Key difference
        assert context["database_engine"] == "sqlite"

    def test_template_context_default_persistence_false(self) -> None:
        """Test template context defaults scheduler_with_persistence to False."""
        components = ["scheduler", "database[sqlite]"]
        template_gen = TemplateGenerator("test-project", components)

        context = template_gen.get_template_context()

        assert context["scheduler_with_persistence"] == "no"

    def test_template_context_independent_database_selection(self) -> None:
        """Test template context when database selected independently of scheduler."""
        components = ["database[sqlite]"]
        template_gen = TemplateGenerator(
            "test-project", components, scheduler_with_persistence=False
        )

        context = template_gen.get_template_context()

        assert context["include_scheduler"] == "no"
        assert context["include_database"] == "yes"
        assert context["scheduler_with_persistence"] == "no"
        assert context["database_engine"] == "sqlite"


class TestSchedulerPersistenceLogic:
    """Test the business logic of scheduler persistence selection."""

    @patch("typer.confirm")
    def test_scheduler_persistence_flow_messaging(self, mock_confirm: Any) -> None:
        """Test that the right messages are shown during scheduler persistence flow."""
        # We can't easily test the echo output, but we can test the logic flow
        mock_confirm.side_effect = [False, False, True, True, True]

        components, scheduler_with_persistence = interactive_component_selection()

        # Verify the logic worked correctly
        assert scheduler_with_persistence is True
        assert "scheduler" in components
        assert any("database[" in comp for comp in components)

    def test_scheduler_persistence_component_format(self) -> None:
        """Test that scheduler persistence results in correct component format."""
        with patch("typer.confirm") as mock_confirm:
            mock_confirm.side_effect = [False, False, True, True, True]

            components, scheduler_with_persistence = interactive_component_selection()

            # Should have database with engine info when added by scheduler
            database_components = [c for c in components if c.startswith("database")]
            assert len(database_components) == 1
            assert database_components[0] == "database[sqlite]"
