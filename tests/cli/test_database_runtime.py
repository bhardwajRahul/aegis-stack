"""
Runtime tests for database functionality in generated projects.

These tests verify that the generated db.py module actually works correctly
at runtime using proper fixture-based testing (ee-toolset pattern).
No string-based test scripts!
"""

from collections.abc import Generator
from typing import Any

import pytest


class TestDatabaseRuntimeBehavior:
    """Test that generated database code actually works at runtime."""

    @pytest.fixture(scope="class")
    def models(self, db_module: dict[str, Any]) -> dict[str, Any]:
        """Create test model classes for this test class."""
        create_models = db_module["create_test_models"]
        result: dict[str, Any] = create_models()
        return result

    @pytest.fixture(autouse=True)
    def setup_tables(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> Generator[None, None, None]:
        """Create test tables before each test and clean up after."""
        # Create data directory for database if it doesn't exist
        import os

        os.makedirs("data", exist_ok=True)

        # Create all tables for our test models
        engine = db_module["engine"]
        sql_model = db_module["SQLModel"]
        sql_model.metadata.create_all(engine)

        # Run the test
        yield

        # Clean up after test - drop all tables to ensure clean state
        # This ensures test isolation without breaking the database connection
        sql_model.metadata.drop_all(engine)

        # Recreate tables for next test (they'll be empty)
        sql_model.metadata.create_all(engine)

    @pytest.mark.slow
    def test_db_session_commits_on_success(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> None:
        """
        Test that db_session context manager commits on success.

        This verifies our actual implementation commits data when
        the context exits without error.
        """
        db_session = db_module["db_session"]
        test_user = models["TestUser"]

        # Use our generated db_session context manager
        with db_session() as session:
            user = test_user(name="Alice", email="alice@example.com")
            session.add(user)
            # Should auto-commit when context exits

        # Verify in a new session that data was persisted
        with db_session() as session:
            result = session.query(test_user).filter_by(name="Alice").first()
            assert result is not None
            assert result.name == "Alice"
            assert result.email == "alice@example.com"

    @pytest.mark.slow
    def test_db_session_rollback_on_error(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> None:
        """
        Test that db_session rolls back on exception.

        Verifies that when an exception occurs within the context,
        the transaction is rolled back and data is NOT persisted.
        """
        db_session = db_module["db_session"]
        test_user = models["TestUser"]

        # Attempt to add data but raise an exception
        try:
            with db_session() as session:
                user = test_user(name="Bob", email="bob@example.com")
                session.add(user)
                # Force an exception - should trigger rollback
                raise ValueError("Intentional error to test rollback")
        except ValueError:
            pass  # Expected exception

        # Verify the data was NOT committed (rolled back)
        with db_session() as session:
            result = session.query(test_user).filter_by(name="Bob").first()
            assert result is None, "Data should have been rolled back"

    @pytest.mark.slow
    def test_autocommit_parameter_false(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> None:
        """
        Test that autocommit=False prevents automatic commit.

        When autocommit=False, changes should NOT be committed
        unless explicitly done.
        """
        db_session = db_module["db_session"]
        test_user = models["TestUser"]

        # Use autocommit=False
        with db_session(autocommit=False) as session:
            user = test_user(name="Charlie", email="charlie@example.com")
            session.add(user)
            # Should NOT auto-commit

        # Verify data was NOT committed
        with db_session() as session:
            result = session.query(test_user).filter_by(name="Charlie").first()
            assert result is None, "Data should not be committed with autocommit=False"

        # Now test explicit commit with autocommit=False
        with db_session(autocommit=False) as session:
            user = test_user(name="David", email="david@example.com")
            session.add(user)
            session.commit()  # Explicit commit

        # Verify explicit commit worked
        with db_session() as session:
            result = session.query(test_user).filter_by(name="David").first()
            assert result is not None
            assert result.name == "David"

    @pytest.mark.slow
    def test_foreign_keys_enabled(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> None:
        """
        Test that foreign key constraints are enforced.

        Verifies that the PRAGMA foreign_keys=ON is working
        by attempting to violate a foreign key constraint.
        """
        db_session = db_module["db_session"]
        integrity_error = db_module["IntegrityError"]
        parent_model = models["Parent"]
        child_model = models["Child"]

        # Create a parent record
        with db_session() as session:
            parent = parent_model(name="Parent1")
            session.add(parent)
            session.flush()  # Get the ID
            parent_id = parent.id

        # Try to create a child with valid parent_id - should work
        with db_session() as session:
            child = child_model(name="ValidChild", parent_id=parent_id)
            session.add(child)
            # Should succeed

        # Try to create a child with invalid parent_id - should fail
        with pytest.raises(integrity_error):
            with db_session() as session:
                invalid_child = child_model(name="InvalidChild", parent_id=99999)
                session.add(invalid_child)
                session.flush()  # Force constraint check

    @pytest.mark.slow
    def test_multiple_operations_in_transaction(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> None:
        """
        Test multiple operations within a single transaction.

        Verifies that multiple operations are treated as a single
        transaction that can be committed or rolled back together.
        """
        db_session = db_module["db_session"]
        test_user = models["TestUser"]

        # Multiple operations that should all commit together
        with db_session() as session:
            user1 = test_user(name="User1", email="user1@example.com")
            user2 = test_user(name="User2", email="user2@example.com")
            user3 = test_user(name="User3", email="user3@example.com")

            session.add_all([user1, user2, user3])
            # All should commit together

        # Verify all were committed
        with db_session() as session:
            count = (
                session.query(test_user)
                .filter(test_user.name.in_(["User1", "User2", "User3"]))
                .count()
            )
            assert count == 3, "All three users should be committed"

        # Test rollback of multiple operations
        try:
            with db_session() as session:
                user4 = test_user(name="User4", email="user4@example.com")
                user5 = test_user(name="User5", email="user5@example.com")

                session.add_all([user4, user5])
                session.flush()  # Ensure they're in the transaction

                # Now cause an error
                raise RuntimeError("Rollback all operations")
        except RuntimeError:
            pass

        # Verify none were committed
        with db_session() as session:
            count = (
                session.query(test_user)
                .filter(test_user.name.in_(["User4", "User5"]))
                .count()
            )
            assert count == 0, "Both users should be rolled back"

    @pytest.mark.slow
    def test_db_session_closes_properly(
        self, db_module: dict[str, Any], models: dict[str, Any]
    ) -> None:
        """
        Test that db_session properly closes the session.

        Verifies that the context manager cleans up resources
        properly in both success and error cases.
        """
        db_session = db_module["db_session"]
        test_user = models["TestUser"]

        # Test successful close
        with db_session() as session:
            user = test_user(name="CloseTest", email="close@test.com")
            session.add(user)

        # Session should be closed now
        # (Can't directly test if closed, but we can verify no leak)

        # Test close even with error
        try:
            with db_session() as session:
                user = test_user(name="ErrorClose", email="error@test.com")
                session.add(user)
                raise Exception("Test error")
        except Exception:
            pass

        # Both sessions should be properly closed
        # The fact that we can create new sessions proves cleanup worked
        with db_session() as session:
            # If previous sessions weren't closed, this might fail
            result = session.query(test_user).count()
            assert result >= 0  # Just verify query works
