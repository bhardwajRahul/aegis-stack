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

    def test_fk_ref_columns_resolved_in_diff_context(self) -> None:
        """FK referenced columns are accessible from add_table diffs."""
        engine = create_engine("sqlite:///:memory:")

        # Create only the user table (referenced by FK)
        old_metadata = sa.MetaData()
        sa.Table(
            "user",
            old_metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
        )
        old_metadata.create_all(engine)

        # New metadata adds a table with FK to user
        new_metadata = sa.MetaData()
        sa.Table(
            "user",
            new_metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
        )
        sa.Table(
            "password_reset_token",
            new_metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("user.id"),
                nullable=False,
            ),
            sa.Column("token", sa.String(), nullable=False),
        )

        with engine.connect() as conn:
            migration_ctx = MigrationContext.configure(conn)
            diffs = compare_metadata(migration_ctx, new_metadata)

        # Get the add_table diff
        add_table_diffs = [d for d in diffs if d[0] == "add_table"]
        assert len(add_table_diffs) == 1

        table = add_table_diffs[0][1]
        assert table.name == "password_reset_token"

        # Verify FK ref columns are resolvable (the bug was empty ref_cols)
        fks = list(table.foreign_key_constraints)
        assert len(fks) == 1
        fk = fks[0]

        # Try element-based extraction (our fix)
        ref_cols = [
            el.column.name
            for el in fk.elements
            if hasattr(el, "column") and el.column is not None
        ]
        assert ref_cols == ["id"], f"FK ref_cols should be ['id'], got {ref_cols}"


class TestMigrateFixMigrationRendering:
    """Test that add_table diffs render correct migration content."""

    def _render_add_table_upgrade(self, table: sa.Table) -> tuple[list[str], list[str]]:
        """Simulate the migration rendering logic from migrate_fix.py."""

        def _sa_type_str(col_type: object) -> str:
            type_name = type(col_type).__name__
            return f"sa.{type_name}()"

        upgrade_lines: list[str] = []
        downgrade_lines: list[str] = []

        items = []
        for col in table.columns:
            col_str = f"sa.Column('{col.name}', {_sa_type_str(col.type)}"
            col_str += f", nullable={col.nullable}"
            if col.primary_key:
                col_str += ", primary_key=True"
            if col.server_default is not None:
                col_str += f", server_default=sa.text('{col.server_default.arg}')"  # type: ignore[union-attr]
            col_str += ")"
            items.append(f"        {col_str},")
        # Inline FK constraints
        for fk in table.foreign_key_constraints:
            local_cols = [c.name for c in fk.columns]
            ref_table = fk.referred_table.name
            # Match production: prefer fk.elements, fall back to PK
            ref_cols = [
                el.column.name
                for el in fk.elements
                if hasattr(el, "column") and el.column is not None
            ]
            if not ref_cols:
                ref_cols = [c.name for c in fk.referred_table.primary_key.columns]
            ref_col_strs = [f"'{ref_table}.{rc}'" for rc in ref_cols]
            local_col_strs = [f"'{lc}'" for lc in local_cols]
            items.append(
                f"        sa.ForeignKeyConstraint([{', '.join(local_col_strs)}], [{', '.join(ref_col_strs)}]),"
            )
        items_block = "\n".join(items)
        upgrade_lines.append(
            f"    op.create_table(\n        '{table.name}',\n{items_block}\n    )"
        )

        for idx in table.indexes:
            idx_cols = [c.name for c in idx.columns]
            unique_str = ", unique=True" if idx.unique else ""
            upgrade_lines.append(
                f"    op.create_index('{idx.name}', '{table.name}', {idx_cols}{unique_str})"
            )

        downgrade_lines.append(f"    op.drop_table('{table.name}')")

        return upgrade_lines, downgrade_lines

    def test_renders_create_table(self) -> None:
        """add_table diff renders op.create_table with all columns."""
        metadata = sa.MetaData()
        table = sa.Table(
            "password_reset_token",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column(
                "used", sa.Boolean(), nullable=False, server_default=sa.text("0")
            ),
        )

        upgrade, downgrade = self._render_add_table_upgrade(table)

        # Should have create_table
        create_line = upgrade[0]
        assert "op.create_table(" in create_line
        assert "'password_reset_token'" in create_line
        assert "'id'" in create_line
        assert "'user_id'" in create_line
        assert "'token'" in create_line
        assert "'used'" in create_line
        assert "primary_key=True" in create_line
        assert "server_default=sa.text('0')" in create_line

        # Downgrade drops the table
        assert "op.drop_table('password_reset_token')" in downgrade[-1]

    def test_renders_foreign_keys_inline(self) -> None:
        """add_table diff with FKs renders inline sa.ForeignKeyConstraint."""
        metadata = sa.MetaData()
        sa.Table(
            "user",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
        )
        sa.Table(
            "password_reset_token",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("user.id"),
                nullable=False,
            ),
            sa.Column("token", sa.String(), nullable=False),
        )

        token_table = metadata.tables["password_reset_token"]
        upgrade, downgrade = self._render_add_table_upgrade(token_table)

        # FK should be inline in create_table, not separate
        create_line = upgrade[0]
        assert "ForeignKeyConstraint" in create_line
        assert "'user_id'" in create_line
        assert "'user.id'" in create_line

        # No separate create_foreign_key calls
        fk_lines = [line for line in upgrade if "create_foreign_key" in line]
        assert len(fk_lines) == 0

    def test_renders_indexes(self) -> None:
        """add_table diff with indexes renders op.create_index."""
        metadata = sa.MetaData()
        table = sa.Table(
            "org_invite",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
        )
        sa.Index("ix_org_invite_token", table.c.token, unique=True)

        upgrade, _ = self._render_add_table_upgrade(table)

        idx_lines = [line for line in upgrade if "create_index" in line]
        assert len(idx_lines) == 1
        assert "'ix_org_invite_token'" in idx_lines[0]
        assert "'org_invite'" in idx_lines[0]
        assert "unique=True" in idx_lines[0]

    def test_empty_table_renders(self) -> None:
        """Table with only a PK column still renders correctly."""
        metadata = sa.MetaData()
        table = sa.Table(
            "simple",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
        )

        upgrade, downgrade = self._render_add_table_upgrade(table)

        assert "op.create_table(" in upgrade[0]
        assert "'simple'" in upgrade[0]
        assert len(upgrade) == 1  # No FKs or indexes
        assert "op.drop_table('simple')" in downgrade[-1]
