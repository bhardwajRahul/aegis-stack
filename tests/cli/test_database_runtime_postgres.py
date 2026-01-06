"""
Runtime tests for PostgreSQL database functionality in generated projects.

These tests verify that the generated db.py module works correctly with PostgreSQL
at runtime. Tests are skipped if PostgreSQL is not available on localhost:5432.

Tests run inside the generated project using subprocess to avoid module caching
issues when running with SQLite tests.

Run with: pytest tests/cli/test_database_runtime_postgres.py -v -m postgres
"""

import os
import textwrap

import pytest

from .test_utils import CLITestResult, run_project_command

# PostgreSQL test configuration (password can be overridden via environment)
POSTGRES_TEST_PASSWORD = os.environ.get("POSTGRES_TEST_PASSWORD", "postgres")

# Mark all tests in this module as postgres and slow
pytestmark = [pytest.mark.postgres, pytest.mark.slow]


def _postgres_available() -> bool:
    """Check if PostgreSQL is available on localhost:5432."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 5432))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all tests if PostgreSQL is not available
if not _postgres_available():
    pytest.skip(
        "PostgreSQL not available on localhost:5432",
        allow_module_level=True,
    )


DB_NAME = "test-database-postgres-runtime"
DATABASE_URL = (
    f"postgresql://postgres:{POSTGRES_TEST_PASSWORD}@localhost:5432/{DB_NAME}"
)


def _run_db_test(
    generated_db_project_postgres: CLITestResult | None,
    test_script: str,
    test_name: str,
) -> None:
    """Run a test script inside the generated PostgreSQL project."""
    if generated_db_project_postgres is None:
        pytest.skip("PostgreSQL project not available")

    assert generated_db_project_postgres.project_path is not None
    result = run_project_command(
        ["uv", "run", "python", "-c", test_script],
        generated_db_project_postgres.project_path,
        step_name=test_name,
        timeout=60,
        # Override both DATABASE_URL and DATABASE_URL_LOCAL (config uses LOCAL when not in Docker)
        env_overrides={
            "DATABASE_URL": DATABASE_URL,
            "DATABASE_URL_LOCAL": DATABASE_URL,
            "VIRTUAL_ENV": "",
        },
    )
    if not result.success:
        pytest.fail(
            f"{test_name} failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


class TestPostgreSQLRuntimeBehavior:
    """Test that generated PostgreSQL database code works at runtime."""

    def test_db_session_commits_on_success(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test that db_session context manager commits on success.

        Verifies PostgreSQL implementation commits data when
        the context exits without error.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUserPg(SQLModel, table=True):
                __tablename__ = "test_users_pg_commit"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            try:
                # Add user with auto-commit
                with db_session() as session:
                    user = TestUserPg(name="Alice", email="alice@example.com")
                    session.add(user)

                # Verify in new session
                with db_session() as session:
                    result = session.query(TestUserPg).filter_by(name="Alice").first()
                    assert result is not None, "User should exist after commit"
                    assert result.name == "Alice"
                    assert result.email == "alice@example.com"
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(
            generated_db_project_postgres, test_script, "db_session commits on success"
        )

    def test_db_session_rollback_on_error(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test that db_session rolls back on exception.

        Verifies that when an exception occurs within the context,
        the transaction is rolled back and data is NOT persisted.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUserPg(SQLModel, table=True):
                __tablename__ = "test_users_pg_rollback"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            try:
                # Attempt to add but raise exception
                try:
                    with db_session() as session:
                        user = TestUserPg(name="Bob", email="bob@example.com")
                        session.add(user)
                        raise ValueError("Intentional error to test rollback")
                except ValueError:
                    pass

                # Verify data was NOT committed
                with db_session() as session:
                    result = session.query(TestUserPg).filter_by(name="Bob").first()
                    assert result is None, "Data should have been rolled back"
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(
            generated_db_project_postgres, test_script, "db_session rollback on error"
        )

    def test_autocommit_parameter_false(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test that autocommit=False prevents automatic commit.

        When autocommit=False, changes should NOT be committed
        unless explicitly done.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUserPg(SQLModel, table=True):
                __tablename__ = "test_users_pg_autocommit"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            try:
                # Use autocommit=False - should NOT persist
                with db_session(autocommit=False) as session:
                    user = TestUserPg(name="Charlie", email="charlie@example.com")
                    session.add(user)

                # Verify NOT committed
                with db_session() as session:
                    result = session.query(TestUserPg).filter_by(name="Charlie").first()
                    assert result is None, "Data should not be committed with autocommit=False"

                # Test explicit commit with autocommit=False
                with db_session(autocommit=False) as session:
                    user = TestUserPg(name="David", email="david@example.com")
                    session.add(user)
                    session.commit()  # Explicit commit

                # Verify explicit commit worked
                with db_session() as session:
                    result = session.query(TestUserPg).filter_by(name="David").first()
                    assert result is not None, "Explicit commit should work"
                    assert result.name == "David"
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(
            generated_db_project_postgres, test_script, "autocommit=False behavior"
        )

    def test_foreign_keys_enforced(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test that foreign key constraints are enforced in PostgreSQL.

        PostgreSQL enforces foreign keys by default (unlike SQLite which
        requires PRAGMA foreign_keys=ON).
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel
            from sqlalchemy.exc import IntegrityError

            class ParentPg(SQLModel, table=True):
                __tablename__ = "parents_pg_fk"
                id: int | None = Field(default=None, primary_key=True)
                name: str

            class ChildPg(SQLModel, table=True):
                __tablename__ = "children_pg_fk"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                parent_id: int = Field(foreign_key="parents_pg_fk.id")

            SQLModel.metadata.create_all(engine)

            try:
                # Create a parent
                with db_session() as session:
                    parent = ParentPg(name="Parent1")
                    session.add(parent)
                    session.flush()
                    parent_id = parent.id

                # Valid child - should work
                with db_session() as session:
                    child = ChildPg(name="ValidChild", parent_id=parent_id)
                    session.add(child)

                # Invalid child - should fail with IntegrityError
                try:
                    with db_session() as session:
                        invalid_child = ChildPg(name="InvalidChild", parent_id=99999)
                        session.add(invalid_child)
                        session.flush()
                    assert False, "Should have raised IntegrityError"
                except IntegrityError:
                    pass  # Expected
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(
            generated_db_project_postgres, test_script, "foreign keys enforced"
        )

    def test_multiple_operations_in_transaction(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test multiple operations within a single transaction.

        Verifies that multiple operations are treated as a single
        transaction that can be committed or rolled back together.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUserPg(SQLModel, table=True):
                __tablename__ = "test_users_pg_multi"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            try:
                # Multiple adds that should all commit together
                with db_session() as session:
                    user1 = TestUserPg(name="User1", email="user1@example.com")
                    user2 = TestUserPg(name="User2", email="user2@example.com")
                    user3 = TestUserPg(name="User3", email="user3@example.com")
                    session.add_all([user1, user2, user3])

                # Verify all committed
                with db_session() as session:
                    count = session.query(TestUserPg).filter(
                        TestUserPg.name.in_(["User1", "User2", "User3"])
                    ).count()
                    assert count == 3, f"Expected 3 users, got {count}"

                # Test rollback of multiple operations
                try:
                    with db_session() as session:
                        user4 = TestUserPg(name="User4", email="user4@example.com")
                        user5 = TestUserPg(name="User5", email="user5@example.com")
                        session.add_all([user4, user5])
                        session.flush()
                        raise RuntimeError("Rollback all operations")
                except RuntimeError:
                    pass

                # Verify none were committed
                with db_session() as session:
                    count = session.query(TestUserPg).filter(
                        TestUserPg.name.in_(["User4", "User5"])
                    ).count()
                    assert count == 0, "Users should be rolled back"
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(
            generated_db_project_postgres,
            test_script,
            "multiple operations in transaction",
        )

    def test_db_session_closes_properly(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test that db_session properly closes the session.

        Verifies that the context manager cleans up resources
        properly in both success and error cases.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUserPg(SQLModel, table=True):
                __tablename__ = "test_users_pg_close"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            try:
                # Test successful close
                with db_session() as session:
                    user = TestUserPg(name="CloseTest", email="close@test.com")
                    session.add(user)

                # Test close even with error
                try:
                    with db_session() as session:
                        user = TestUserPg(name="ErrorClose", email="error@test.com")
                        session.add(user)
                        raise Exception("Test error")
                except Exception:
                    pass

                # Verify we can still create new sessions (cleanup worked)
                with db_session() as session:
                    result = session.query(TestUserPg).count()
                    assert result >= 0
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(
            generated_db_project_postgres, test_script, "db_session closes properly"
        )

    def test_postgresql_specific_features(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test PostgreSQL-specific features work correctly.

        Verifies that PostgreSQL-specific behavior is working as expected.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session
            from sqlalchemy import text

            # Test PostgreSQL version query
            with db_session() as session:
                result = session.execute(text("SELECT version()")).fetchone()
                assert result is not None
                assert "PostgreSQL" in result[0]
            print("TEST PASSED")
        """)
        _run_db_test(
            generated_db_project_postgres,
            test_script,
            "PostgreSQL-specific features",
        )

    def test_concurrent_sessions(
        self, generated_db_project_postgres: CLITestResult | None
    ) -> None:
        """
        Test that multiple concurrent sessions work correctly.

        PostgreSQL handles concurrent sessions better than SQLite,
        so we can test this behavior.
        """
        test_script = textwrap.dedent("""
            from app.core.db import db_session, engine
            from sqlmodel import Field, SQLModel

            class TestUserPg(SQLModel, table=True):
                __tablename__ = "test_users_pg_concurrent"
                id: int | None = Field(default=None, primary_key=True)
                name: str
                email: str | None = None

            SQLModel.metadata.create_all(engine)

            try:
                # Create data in one session
                with db_session() as session1:
                    user = TestUserPg(name="ConcurrentTest", email="concurrent@test.com")
                    session1.add(user)
                    session1.commit()

                    # Open another session while first is still open
                    with db_session() as session2:
                        result = session2.query(TestUserPg).filter_by(
                            name="ConcurrentTest"
                        ).first()
                        assert result is not None
                        assert result.name == "ConcurrentTest"
                print("TEST PASSED")
            finally:
                SQLModel.metadata.drop_all(engine)
        """)
        _run_db_test(generated_db_project_postgres, test_script, "concurrent sessions")
