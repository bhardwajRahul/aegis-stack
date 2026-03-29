"""
Tests for schema migration fix detection.

Verifies that when a database has an old schema (missing columns/tables),
Alembic's compare_metadata correctly detects the differences that
migrate_fix.py would use to generate additive migrations.
"""

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine


class TestMigrateFixDetection:
    """Test that schema diffs are correctly detected for migrate-fix scenarios."""

    def _create_old_user_table(self, engine: sa.engine.Engine) -> None:
        """Create the v0.6.7 user table (without lockout columns)."""
        metadata = sa.MetaData()
        sa.Table(
            "user",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("is_verified", sa.Boolean(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("last_login", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        metadata.create_all(engine)

    def _get_new_metadata(self) -> sa.MetaData:
        """Build metadata that includes lockout columns."""
        metadata = sa.MetaData()
        sa.Table(
            "user",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("is_verified", sa.Boolean(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("last_login", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            # NEW columns
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("locked_until", sa.DateTime(), nullable=True),
        )
        return metadata

    def test_detects_missing_lockout_columns(self) -> None:
        """Old user table without lockout columns -> diff detects them."""
        engine = create_engine("sqlite:///:memory:")
        self._create_old_user_table(engine)
        new_metadata = self._get_new_metadata()

        with engine.connect() as conn:
            migration_ctx = MigrationContext.configure(conn)
            diffs = compare_metadata(migration_ctx, new_metadata)

        # Filter to just add_column ops on the user table
        add_column_diffs = [d for d in diffs if d[0] == "add_column" and d[2] == "user"]
        added_col_names = {d[3].name for d in add_column_diffs}

        assert "failed_login_attempts" in added_col_names
        assert "locked_until" in added_col_names

    def test_no_diff_when_schema_matches(self) -> None:
        """When DB matches metadata exactly -> no diffs."""
        engine = create_engine("sqlite:///:memory:")
        new_metadata = self._get_new_metadata()
        # Create the full schema directly
        new_metadata.create_all(engine)

        with engine.connect() as conn:
            migration_ctx = MigrationContext.configure(conn)
            diffs = compare_metadata(migration_ctx, new_metadata)

        # Filter to add_column only (ignore index diffs etc)
        add_column_diffs = [d for d in diffs if d[0] == "add_column"]
        assert len(add_column_diffs) == 0

    def test_detects_missing_table(self) -> None:
        """Missing password_reset_token table -> diff detects it."""
        engine = create_engine("sqlite:///:memory:")
        # Create only the user table, not the token tables
        self._create_old_user_table(engine)

        metadata = self._get_new_metadata()
        # Add password_reset_token table to expected metadata
        sa.Table(
            "password_reset_token",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False),
        )

        with engine.connect() as conn:
            migration_ctx = MigrationContext.configure(conn)
            diffs = compare_metadata(migration_ctx, metadata)

        # Should detect the missing table
        add_table_diffs = [d for d in diffs if d[0] == "add_table"]
        added_table_names = {d[1].name for d in add_table_diffs}
        assert "password_reset_token" in added_table_names

    def test_detects_only_additive_changes(self) -> None:
        """Extra DB columns should not produce add_column diffs (migrate-fix filters drops)."""
        engine = create_engine("sqlite:///:memory:")

        # Create DB with an EXTRA column (simulating someone added a custom field)
        old_metadata = sa.MetaData()
        sa.Table(
            "user",
            old_metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("custom_field", sa.String(), nullable=True),  # extra
        )
        old_metadata.create_all(engine)

        # New metadata doesn't have custom_field
        new_metadata = sa.MetaData()
        sa.Table(
            "user",
            new_metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
        )

        with engine.connect() as conn:
            migration_ctx = MigrationContext.configure(conn)
            diffs = compare_metadata(migration_ctx, new_metadata)

        # Should have remove_column diffs but NO add_column diffs
        add_column_diffs = [d for d in diffs if d[0] == "add_column"]
        assert len(add_column_diffs) == 0

    def test_upgrade_scenario_basic_to_current(self) -> None:
        """Full upgrade scenario: v0.6.7 basic auth -> current."""
        engine = create_engine("sqlite:///:memory:")

        # v0.6.7 schema: just user table, no lockout, no tokens
        self._create_old_user_table(engine)

        # Current schema: user with lockout + token tables
        current = self._get_new_metadata()
        sa.Table(
            "password_reset_token",
            current,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False),
        )
        sa.Table(
            "email_verification_token",
            current,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False),
        )

        with engine.connect() as conn:
            migration_ctx = MigrationContext.configure(conn)
            diffs = compare_metadata(migration_ctx, current)

        add_columns = [d for d in diffs if d[0] == "add_column"]
        add_tables = [d for d in diffs if d[0] == "add_table"]

        added_col_names = {d[3].name for d in add_columns}
        added_table_names = {d[1].name for d in add_tables}

        # Missing columns on user table
        assert "failed_login_attempts" in added_col_names
        assert "locked_until" in added_col_names

        # Missing tables
        assert "password_reset_token" in added_table_names
        assert "email_verification_token" in added_table_names
