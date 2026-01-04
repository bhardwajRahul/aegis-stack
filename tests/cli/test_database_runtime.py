"""
Runtime tests for SQLite database functionality in generated projects.

These tests verify that the generated db.py module works correctly with SQLite
at runtime. Tests run inside the generated project using subprocess to avoid
module caching issues.

Run with: pytest tests/cli/test_database_runtime.py -v
"""

import textwrap

import pytest

from .test_utils import CLITestResult, run_project_command

# Mark all tests in this module as slow
pytestmark = pytest.mark.slow


def _run_db_test(
    generated_db_project: CLITestResult, test_script: str, test_name: str
) -> None:
    """Run a test script inside the generated project."""
    assert generated_db_project.project_path is not None
    result = run_project_command(
        ["uv", "run", "python", "-c", test_script],
        generated_db_project.project_path,
        step_name=test_name,
        timeout=60,
    )
    if not result.success:
        pytest.fail(
            f"{test_name} failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


class TestSQLiteRuntimeBehavior:
    """Test that generated SQLite database code works at runtime."""

    def test_db_session_commits_on_success(
        self, generated_db_project: CLITestResult
    ) -> None:
        """
        Test that db_session context manager commits on success.

        Verifies SQLite implementation commits data when
        the context exits without error.
        """
        test_script = textwrap.dedent("""
            import os
            os.makedirs("data", exist_ok=True)

            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUser(SQLModel, table=True):
                __tablename__ = "test_users_commit"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            # Add user with auto-commit
            with db_session() as session:
                user = TestUser(name="Alice", email="alice@example.com")
                session.add(user)

            # Verify in new session
            with db_session() as session:
                result = session.query(TestUser).filter_by(name="Alice").first()
                assert result is not None, "User should exist after commit"
                assert result.name == "Alice"
                assert result.email == "alice@example.com"

            # Cleanup
            SQLModel.metadata.drop_all(engine)
            print("TEST PASSED")
        """)
        _run_db_test(generated_db_project, test_script, "db_session commits on success")

    def test_db_session_rollback_on_error(
        self, generated_db_project: CLITestResult
    ) -> None:
        """
        Test that db_session rolls back on exception.

        Verifies that when an exception occurs within the context,
        the transaction is rolled back and data is NOT persisted.
        """
        test_script = textwrap.dedent("""
            import os
            os.makedirs("data", exist_ok=True)

            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUser(SQLModel, table=True):
                __tablename__ = "test_users_rollback"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            # Attempt to add but raise exception
            try:
                with db_session() as session:
                    user = TestUser(name="Bob", email="bob@example.com")
                    session.add(user)
                    raise ValueError("Intentional error to test rollback")
            except ValueError:
                pass

            # Verify data was NOT committed
            with db_session() as session:
                result = session.query(TestUser).filter_by(name="Bob").first()
                assert result is None, "Data should have been rolled back"

            # Cleanup
            SQLModel.metadata.drop_all(engine)
            print("TEST PASSED")
        """)
        _run_db_test(generated_db_project, test_script, "db_session rollback on error")

    def test_autocommit_parameter_false(
        self, generated_db_project: CLITestResult
    ) -> None:
        """
        Test that autocommit=False prevents automatic commit.

        When autocommit=False, changes should NOT be committed
        unless explicitly done.
        """
        test_script = textwrap.dedent("""
            import os
            os.makedirs("data", exist_ok=True)

            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUser(SQLModel, table=True):
                __tablename__ = "test_users_autocommit"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            # Use autocommit=False - should NOT persist
            with db_session(autocommit=False) as session:
                user = TestUser(name="Charlie", email="charlie@example.com")
                session.add(user)

            # Verify NOT committed
            with db_session() as session:
                result = session.query(TestUser).filter_by(name="Charlie").first()
                assert result is None, "Data should not be committed with autocommit=False"

            # Test explicit commit with autocommit=False
            with db_session(autocommit=False) as session:
                user = TestUser(name="David", email="david@example.com")
                session.add(user)
                session.commit()  # Explicit commit

            # Verify explicit commit worked
            with db_session() as session:
                result = session.query(TestUser).filter_by(name="David").first()
                assert result is not None, "Explicit commit should work"
                assert result.name == "David"

            # Cleanup
            SQLModel.metadata.drop_all(engine)
            print("TEST PASSED")
        """)
        _run_db_test(generated_db_project, test_script, "autocommit=False behavior")

    def test_foreign_keys_enabled(self, generated_db_project: CLITestResult) -> None:
        """
        Test that foreign key constraints are enforced.

        Verifies that the PRAGMA foreign_keys=ON is working
        by attempting to violate a foreign key constraint.
        """
        test_script = textwrap.dedent("""
            import os
            os.makedirs("data", exist_ok=True)

            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel
            from sqlalchemy.exc import IntegrityError

            class Parent(SQLModel, table=True):
                __tablename__ = "parents_fk"
                id: int | None = Field(default=None, primary_key=True)
                name: str

            class Child(SQLModel, table=True):
                __tablename__ = "children_fk"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                parent_id: int = Field(foreign_key="parents_fk.id")

            SQLModel.metadata.create_all(engine)

            # Create a parent
            with db_session() as session:
                parent = Parent(name="Parent1")
                session.add(parent)
                session.flush()
                parent_id = parent.id

            # Valid child - should work
            with db_session() as session:
                child = Child(name="ValidChild", parent_id=parent_id)
                session.add(child)

            # Invalid child - should fail with IntegrityError
            try:
                with db_session() as session:
                    invalid_child = Child(name="InvalidChild", parent_id=99999)
                    session.add(invalid_child)
                    session.flush()
                assert False, "Should have raised IntegrityError"
            except IntegrityError:
                pass  # Expected

            # Cleanup
            SQLModel.metadata.drop_all(engine)
            print("TEST PASSED")
        """)
        _run_db_test(generated_db_project, test_script, "foreign keys enabled")

    def test_multiple_operations_in_transaction(
        self, generated_db_project: CLITestResult
    ) -> None:
        """
        Test multiple operations within a single transaction.

        Verifies that multiple operations are treated as a single
        transaction that can be committed or rolled back together.
        """
        test_script = textwrap.dedent("""
            import os
            os.makedirs("data", exist_ok=True)

            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUser(SQLModel, table=True):
                __tablename__ = "test_users_multi"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            # Multiple adds that should all commit together
            with db_session() as session:
                user1 = TestUser(name="User1", email="user1@example.com")
                user2 = TestUser(name="User2", email="user2@example.com")
                user3 = TestUser(name="User3", email="user3@example.com")
                session.add_all([user1, user2, user3])

            # Verify all committed
            with db_session() as session:
                count = session.query(TestUser).filter(
                    TestUser.name.in_(["User1", "User2", "User3"])
                ).count()
                assert count == 3, f"Expected 3 users, got {count}"

            # Test rollback of multiple operations
            try:
                with db_session() as session:
                    user4 = TestUser(name="User4", email="user4@example.com")
                    user5 = TestUser(name="User5", email="user5@example.com")
                    session.add_all([user4, user5])
                    session.flush()
                    raise RuntimeError("Rollback all operations")
            except RuntimeError:
                pass

            # Verify none were committed
            with db_session() as session:
                count = session.query(TestUser).filter(
                    TestUser.name.in_(["User4", "User5"])
                ).count()
                assert count == 0, "Users should be rolled back"

            # Cleanup
            SQLModel.metadata.drop_all(engine)
            print("TEST PASSED")
        """)
        _run_db_test(
            generated_db_project, test_script, "multiple operations in transaction"
        )

    def test_db_session_closes_properly(
        self, generated_db_project: CLITestResult
    ) -> None:
        """
        Test that db_session properly closes the session.

        Verifies that the context manager cleans up resources
        properly in both success and error cases.
        """
        test_script = textwrap.dedent("""
            import os
            os.makedirs("data", exist_ok=True)

            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUser(SQLModel, table=True):
                __tablename__ = "test_users_close"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            # Test successful close
            with db_session() as session:
                user = TestUser(name="CloseTest", email="close@test.com")
                session.add(user)

            # Test close even with error
            try:
                with db_session() as session:
                    user = TestUser(name="ErrorClose", email="error@test.com")
                    session.add(user)
                    raise Exception("Test error")
            except Exception:
                pass

            # Verify we can still create new sessions (cleanup worked)
            with db_session() as session:
                result = session.query(TestUser).count()
                assert result >= 0

            # Cleanup
            SQLModel.metadata.drop_all(engine)
            print("TEST PASSED")
        """)
        _run_db_test(generated_db_project, test_script, "db_session closes properly")
