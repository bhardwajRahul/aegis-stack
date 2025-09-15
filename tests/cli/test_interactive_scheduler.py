"""
Tests for enhanced interactive scheduler component selection.

This module tests the context-aware scheduler persistence and database engine
selection functionality added to the interactive component selection.
"""

from typing import Any
from unittest.mock import patch

from aegis.cli.interactive import interactive_project_selection


class TestInteractiveSchedulerFlow:
    """Test cases for enhanced scheduler interactive flow."""

    @patch("typer.confirm")
    def test_scheduler_with_sqlite_persistence(self, mock_confirm: Any) -> None:
        """Test scheduler selection with SQLite database persistence."""
        # Mock user responses: redis=no, worker=no, scheduler=yes,
        # persistence=yes, continue with SQLite=yes, no auth service
        mock_confirm.side_effect = [
            False,
            False,
            True,
            True,
            True,
            False,
        ]  # redis, worker, scheduler, persistence, continue with SQLite, auth

        components, scheduler_backend, services = interactive_project_selection()

        # Should return scheduler[sqlite] and database with SQLite engine info
        assert "scheduler[sqlite]" in components
        assert "database[sqlite]" in components
        assert scheduler_backend == "sqlite"
        assert services == []  # No services selected

        # Verify correct calls were made (now includes auth service prompt)
        assert mock_confirm.call_count == 6

    # TODO: Add PostgreSQL tests when PostgreSQL support is implemented
    # @patch('typer.confirm')
    # @patch('typer.prompt')
    # def test_scheduler_with_postgresql_persistence(
    #     self, mock_prompt: Any, mock_confirm: Any
    # ) -> None:
    #     """Test scheduler selection with PostgreSQL database persistence."""

    # TODO: Add test for declining SQLite when PostgreSQL support is implemented
    # @patch('typer.confirm')
    # @patch('typer.prompt')
    # def test_scheduler_sqlite_declined_gets_postgresql(
    #     self, mock_prompt: Any, mock_confirm: Any
    # ) -> None:
    #     """Test declining SQLite switches to PostgreSQL."""

    @patch("typer.confirm")
    def test_scheduler_without_persistence(self, mock_confirm: Any) -> None:
        """Test scheduler selection without persistence (no database)."""
        # Mock user responses: redis=no, worker=no, scheduler=yes,
        # persistence=no, database=no
        mock_confirm.side_effect = [
            False,
            False,
            True,
            False,
            False,
            False,
        ]  # redis, worker, scheduler, no persistence, database=no, no auth

        components, scheduler_backend, _ = interactive_project_selection()

        # Should only return scheduler, no database
        assert "scheduler" in components
        assert not any(c.startswith("database") for c in components)
        assert scheduler_backend == "memory"

    @patch("typer.confirm")
    def test_scheduler_not_selected(self, mock_confirm: Any) -> None:
        """Test when scheduler is not selected."""
        # Mock user responses: scheduler=no, database=no (other components)
        mock_confirm.side_effect = [
            False,
            False,
            False,
            False,
            False,
        ]  # All components declined, no auth

        components, scheduler_backend, _ = interactive_project_selection()

        # Should return empty list (no infrastructure components)
        assert "scheduler" not in components
        assert not any(c.startswith("database") for c in components)
        assert components == []
        assert scheduler_backend == "memory"

    @patch("typer.confirm")
    def test_scheduler_skips_generic_database_prompt(self, mock_confirm: Any) -> None:
        """Test generic database prompt is skipped when added by scheduler."""
        # Mock user responses: redis=no, worker=no, scheduler=yes,
        # persistence=yes, continue=yes
        # The database prompt should be skipped
        mock_confirm.side_effect = [
            False,
            False,
            True,
            True,
            True,
            False,
        ]  # redis, worker, scheduler, persistence, continue SQLite, no auth

        components, scheduler_backend, _ = interactive_project_selection()

        # Should have scheduler[sqlite] and database
        assert "scheduler[sqlite]" in components
        assert "database[sqlite]" in components
        assert scheduler_backend == "sqlite"

        # Should not have been prompted for generic database
        # (6 confirms: redis, worker, scheduler, persist, continue, auth)
        assert mock_confirm.call_count == 6

    @patch("typer.confirm")
    def test_scheduler_declined_sqlite_no_database(self, mock_confirm: Any) -> None:
        """Test that declining SQLite results in no database."""
        # Mock user responses: redis=no, worker=no, scheduler=yes,
        # persistence=yes, decline SQLite, database=no
        mock_confirm.side_effect = [
            False,
            False,
            True,
            True,
            False,
            False,
            False,
        ]  # redis, worker, scheduler, persistence, decline SQLite, database=no, no auth

        components, scheduler_backend, _ = interactive_project_selection()

        # Should have scheduler but no database
        assert "scheduler" in components
        assert not any(c.startswith("database") for c in components)
        assert scheduler_backend == "memory"

    @patch("typer.confirm")
    def test_redis_worker_then_scheduler_sqlite(self, mock_confirm: Any) -> None:
        """Test complex flow: redis + worker, then scheduler with SQLite."""
        # Mock responses: redis=no, worker=yes (adds redis), scheduler=yes,
        # persistence=yes, continue SQLite
        mock_confirm.side_effect = [
            False,
            True,
            True,
            True,
            True,
            False,
        ]  # redis=no, worker=yes, scheduler=yes, persistence=yes, continue=yes, no auth

        components, scheduler_backend, _ = interactive_project_selection()

        # Should have redis (from worker), worker, scheduler[sqlite], database[sqlite]
        assert "redis" in components
        assert "worker" in components
        assert "scheduler[sqlite]" in components
        assert "database[sqlite]" in components
        assert len(components) == 4
        assert scheduler_backend == "sqlite"

    @patch("typer.confirm")
    def test_standalone_database_selection_still_works(self, mock_confirm: Any) -> None:
        """Test that standalone database selection (without scheduler) still works."""
        # Mock responses: redis=no, worker=no, scheduler=no, database=yes
        mock_confirm.side_effect = [False, False, False, True, False]

        components, scheduler_backend, _ = interactive_project_selection()

        # Should have just database (no engine suffix when not from scheduler)
        assert components == ["database"]
        assert "scheduler" not in components
        assert scheduler_backend == "memory"
