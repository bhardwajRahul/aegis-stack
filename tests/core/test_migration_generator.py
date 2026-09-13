"""
Tests for dynamic migration generator module.

These tests validate the migration generation functionality that creates
Alembic migration files on-demand for services like auth and AI.
"""

import ast
from pathlib import Path
from typing import Any

import pytest

from aegis.core.migration_generator import (
    AI_MIGRATION,
    AUTH_MIGRATION,
    AUTH_RBAC_MIGRATION,
    AUTH_TOKENS_MIGRATION,
    BLOG_MIGRATION,
    INSIGHTS_MIGRATION,
    MIGRATION_SPECS,
    ORG_MIGRATION,
    SCHEDULER_MIGRATION,
    VOICE_MIGRATION,
    CheckConstraintSpec,
    ColumnSpec,
    ForeignKeySpec,
    IndexSpec,
    ServiceMigrationSpec,
    TableSpec,
    _build_insights_migration,
    _render_migration,
    get_existing_migrations,
    get_next_revision_id,
    get_previous_revision,
    get_services_needing_migrations,
    get_versions_dir,
    service_has_migration,
)


class TestGetServicesNeedingMigrations:
    """Test detection of which services need migrations based on context."""

    def test_auth_only(self) -> None:
        """Test auth service needs migrations."""
        context = {"include_auth": True, "include_ai": False, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == ["auth", "auth_tokens"]

    def test_auth_with_yes_string(self) -> None:
        """Test auth service with 'yes' string (cookiecutter format)."""
        context = {"include_auth": "yes", "include_ai": "no", "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == ["auth", "auth_tokens"]

    def test_ai_with_sqlite(self) -> None:
        """Test AI service with sqlite backend needs migrations."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert result == ["ai", "ai_agents", "ai_sentiment"]

    def test_ai_with_memory_no_migrations(self) -> None:
        """Test AI service with memory backend does NOT need migrations."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == []

    def test_both_services(self) -> None:
        """Test both auth and AI services need migrations."""
        context = {"include_auth": True, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert result == ["auth", "auth_tokens", "ai", "ai_agents", "ai_sentiment"]

    def test_neither_service(self) -> None:
        """Test no services need migrations."""
        context = {"include_auth": False, "include_ai": False, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == []

    def test_blog_needs_migration(self) -> None:
        """Blog service needs migrations when selected."""
        context = {"include_blog": True, "include_ai": False, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == ["blog"]

    def test_blog_needs_migration_with_yes_string(self) -> None:
        """Blog service supports Copier-style yes strings."""
        context = {"include_blog": "yes", "include_ai": False, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == ["blog"]

    def test_documents_needs_migration(self) -> None:
        """The document store owns two tables; a fresh stack must migrate them."""
        context = {
            "include_documents": True,
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert result == ["documents"]

    def test_finance_needs_migration(self) -> None:
        """Finance service needs migrations when selected."""
        context = {
            "include_finance": True,
            "include_ai": False,
            "ai_backend": "memory",
        }
        assert get_services_needing_migrations(context) == ["finance"]

    def test_finance_needs_migration_with_yes_string(self) -> None:
        """Finance service supports Copier-style yes strings."""
        context = {
            "include_finance": "yes",
            "include_ai": False,
            "ai_backend": "memory",
        }
        assert get_services_needing_migrations(context) == ["finance"]

    def test_finance_auth_link_when_both(self) -> None:
        """finance + auth emits the owner-FK link migration, after auth+finance."""
        context = {
            "include_auth": True,
            "include_finance": True,
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "finance_auth_link" in result
        # auth (user table) and finance base must precede the link.
        assert result.index("auth") < result.index("finance_auth_link")
        assert result.index("finance") < result.index("finance_auth_link")

    def test_no_finance_auth_link_without_auth(self) -> None:
        """Standalone finance emits no link migration."""
        context = {
            "include_finance": True,
            "include_ai": False,
            "ai_backend": "memory",
        }
        assert "finance_auth_link" not in get_services_needing_migrations(context)

    def test_auth_rbac_needs_migration(self) -> None:
        """Test auth_rbac migration needed when rbac level enabled."""
        context = {
            "include_auth": "yes",
            "include_auth_rbac": "yes",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_rbac" in result

    def test_auth_rbac_needs_migration_via_auth_level(self) -> None:
        """Test auth_rbac detected via auth_level fallback."""
        context = {
            "include_auth": "yes",
            "auth_level": "rbac",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_rbac" in result

    def test_auth_rbac_needs_migration_when_org(self) -> None:
        """Test auth_rbac also generated for org level (org implies rbac)."""
        context = {
            "include_auth": "yes",
            "auth_level": "org",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_rbac" in result
        assert "auth_org" in result

    def test_auth_rbac_not_needed_for_basic(self) -> None:
        """Test auth_rbac not generated for basic auth."""
        context = {
            "include_auth": "yes",
            "auth_level": "basic",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth" in result
        assert "auth_rbac" not in result

    def test_auth_org_needs_migration(self) -> None:
        """Test auth_org service needs migration when org level enabled."""
        context = {
            "include_auth": "yes",
            "include_auth_org": "yes",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_org" in result

    def test_auth_org_not_needed_without_org(self) -> None:
        """Test auth_org service not needed when org level disabled."""
        context = {
            "include_auth": "yes",
            "include_auth_org": "no",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_org" not in result

    def test_auth_org_needs_migration_via_auth_level(self) -> None:
        """Test auth_org detected via auth_level fallback when include_auth_org missing."""
        context = {
            "include_auth": "yes",
            "auth_level": "org",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_org" in result

    def test_auth_org_not_needed_without_auth(self) -> None:
        """Test auth_org service not needed when auth not included."""
        context = {
            "include_auth": False,
            "include_auth_org": "yes",
            "include_ai": False,
            "ai_backend": "memory",
        }
        result = get_services_needing_migrations(context)
        assert "auth_org" not in result


class TestGetVersionsDir:
    """Test getting the alembic versions directory."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        """Test that correct versions path is returned."""
        result = get_versions_dir(tmp_path)
        assert result == tmp_path / "alembic" / "versions"


class TestGetExistingMigrations:
    """Test detection of existing migration files."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test returns empty list when no migrations exist."""
        result = get_existing_migrations(tmp_path)
        assert result == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test returns empty list when versions dir doesn't exist."""
        result = get_existing_migrations(tmp_path / "nonexistent")
        assert result == []

    def test_finds_migrations(self, tmp_path: Path) -> None:
        """Test finds existing migration files."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)

        # Create some migration files
        (versions_dir / "001_auth.py").touch()
        (versions_dir / "002_ai.py").touch()
        (versions_dir / "__init__.py").touch()  # Should be ignored

        result = get_existing_migrations(tmp_path)
        assert result == ["001", "002"]

    def test_sorts_by_filename(self, tmp_path: Path) -> None:
        """Test migrations are sorted by filename."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)

        # Create in non-sorted order
        (versions_dir / "003_third.py").touch()
        (versions_dir / "001_first.py").touch()
        (versions_dir / "002_second.py").touch()

        result = get_existing_migrations(tmp_path)
        assert result == ["001", "002", "003"]


class TestGetNextRevisionId:
    """Test getting the next revision ID."""

    def test_first_migration(self, tmp_path: Path) -> None:
        """Test returns '001' for first migration."""
        result = get_next_revision_id(tmp_path)
        assert result == "001"

    def test_increments_existing(self, tmp_path: Path) -> None:
        """Test increments from existing migrations."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()
        (versions_dir / "002_ai.py").touch()

        result = get_next_revision_id(tmp_path)
        assert result == "003"


class TestGetPreviousRevision:
    """Test getting the previous revision ID."""

    def test_no_migrations(self, tmp_path: Path) -> None:
        """Test returns None when no migrations exist."""
        result = get_previous_revision(tmp_path)
        assert result is None

    def test_returns_last_revision(self, tmp_path: Path) -> None:
        """Test returns the most recent revision."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()
        (versions_dir / "002_ai.py").touch()

        result = get_previous_revision(tmp_path)
        assert result == "002"


class TestServiceHasMigration:
    """Test detection of existing service migrations."""

    def test_no_migrations(self, tmp_path: Path) -> None:
        """Test returns False when no migrations exist."""
        result = service_has_migration(tmp_path, "auth")
        assert result is False

    def test_migration_exists(self, tmp_path: Path) -> None:
        """Test returns True when service migration exists."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()

        result = service_has_migration(tmp_path, "auth")
        assert result is True

    def test_different_service(self, tmp_path: Path) -> None:
        """Test returns False for different service."""
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").touch()

        result = service_has_migration(tmp_path, "ai")
        assert result is False


class TestGenerateMigration:
    """Test individual migration generation."""

    def test_alter_add_index_renders_partial_predicate(self, tmp_path: Path) -> None:
        """``IndexSpec(..., where=...)`` inside an ``AlterTableSpec``
        must render the same predicate as the create_table path.
        Plugin authors hitting the alter branch otherwise get a silently
        full index."""
        from aegis.core.migration_generator import (
            AlterTableSpec,
            ServiceMigrationSpec,
            _render_migration,
        )

        spec = ServiceMigrationSpec(
            service_name="test_alter_partial",
            description="exercises IndexSpec.where in alter path",
            tables=[],
            alter_tables=[
                AlterTableSpec(
                    name="some_table",
                    add_indexes=[
                        IndexSpec(
                            "ix_some_table_email_active",
                            ["email"],
                            unique=True,
                            where="deleted_at IS NULL",
                        )
                    ],
                )
            ],
        )

        content = _render_migration(spec, revision="999", down_revision=None)
        assert "batch_op.create_index" in content
        assert 'sqlite_where=sa.text("deleted_at IS NULL")' in content
        assert 'postgresql_where=sa.text("deleted_at IS NULL")' in content


class TestMigrationSpecs:
    """Test migration specification definitions."""

    def test_auth_spec_exists(self) -> None:
        """Test auth migration spec is defined."""
        assert "auth" in MIGRATION_SPECS
        assert AUTH_MIGRATION.service_name == "auth"
        assert len(AUTH_MIGRATION.tables) == 2

        user_table = AUTH_MIGRATION.tables[0]
        assert user_table.name == "user"
        column_names = [col.name for col in user_table.columns]
        assert "email" in column_names
        assert "hashed_password" in column_names
        assert "is_verified" in column_names
        assert "last_login" in column_names
        assert "failed_login_attempts" in column_names
        assert "locked_until" in column_names
        # Soft-delete column (AUTH-029)
        assert "deleted_at" in column_names
        # Only role is in RBAC migration
        assert "role" not in column_names

        # OAuth identity table — links a user to a third-party identity
        # (GitHub, Google, etc.). Composite (provider, provider_user_id) is
        # unique to prevent identity hijacking across accounts.
        oauth_table = AUTH_MIGRATION.tables[1]
        assert oauth_table.name == "user_oauth_identity"
        oauth_cols = [col.name for col in oauth_table.columns]
        assert "user_id" in oauth_cols
        assert "provider" in oauth_cols
        assert "provider_user_id" in oauth_cols
        assert "provider_email" in oauth_cols
        assert oauth_table.foreign_keys[0].ref_table == "user"
        # Composite uniqueness on (provider, provider_user_id)
        unique_indexes = [idx for idx in oauth_table.indexes if idx.unique]
        assert any(
            idx.columns == ["provider", "provider_user_id"] for idx in unique_indexes
        )

    def test_auth_rbac_spec_exists(self) -> None:
        """Test auth RBAC migration spec is defined with alter_tables."""
        assert "auth_rbac" in MIGRATION_SPECS
        assert AUTH_RBAC_MIGRATION.service_name == "auth_rbac"
        assert len(AUTH_RBAC_MIGRATION.tables) == 0
        assert len(AUTH_RBAC_MIGRATION.alter_tables) == 1
        assert AUTH_RBAC_MIGRATION.alter_tables[0].name == "user"
        col_names = [c.name for c in AUTH_RBAC_MIGRATION.alter_tables[0].add_columns]
        assert "role" in col_names
        # is_verified and last_login are in base auth, not rbac
        assert "is_verified" not in col_names
        assert "last_login" not in col_names

    def test_insights_shared_spec_exists(self) -> None:
        """Shared-mode insights spec — base tables, no per-user columns.

        Default registry-facing variant (``insights_per_user=False``):
        just source/metric_type/metric/event/record. No project, no goal,
        no user FKs. A project can ship insights without auth.
        """
        assert "insights" in MIGRATION_SPECS
        assert INSIGHTS_MIGRATION.service_name == "insights"

        table_names = [t.name for t in INSIGHTS_MIGRATION.tables]
        assert table_names == [
            "insight_source",
            "insight_metric_type",
            "insight_metric",
            "insight_record",
            "insight_event",
        ]

        event_table = next(
            t for t in INSIGHTS_MIGRATION.tables if t.name == "insight_event"
        )
        event_cols = [c.name for c in event_table.columns]
        assert "origin" in event_cols
        # User/project columns are per-user mode only.
        assert "created_by_user_id" not in event_cols
        assert "project_id" not in event_cols

        metric_table = next(
            t for t in INSIGHTS_MIGRATION.tables if t.name == "insight_metric"
        )
        assert "project_id" not in [c.name for c in metric_table.columns]

    def test_insights_per_user_spec_adds_project_and_goals(self) -> None:
        """Per-user mode folds project + insight_goal + project_id FKs into one spec."""
        spec = _build_insights_migration(per_user=True)
        assert spec.service_name == "insights"

        table_names = [t.name for t in spec.tables]
        # ``project`` is first (FK target for everything below); ``insight_goal``
        # is last (per-user-only, FKs to project + user).
        assert table_names == [
            "project",
            "insight_source",
            "insight_metric_type",
            "insight_metric",
            "insight_record",
            "insight_event",
            "insight_goal",
        ]

        # insight_metric carries a NOT NULL project_id FK.
        metric_table = next(t for t in spec.tables if t.name == "insight_metric")
        metric_cols = {c.name: c for c in metric_table.columns}
        assert "project_id" in metric_cols
        assert metric_cols["project_id"].nullable is False
        assert any(fk.ref_table == "project" for fk in metric_table.foreign_keys)

        # insight_event carries project_id (NOT NULL) and created_by_user_id (nullable).
        event_table = next(t for t in spec.tables if t.name == "insight_event")
        event_cols = {c.name: c for c in event_table.columns}
        assert "project_id" in event_cols
        assert event_cols["project_id"].nullable is False
        assert "created_by_user_id" in event_cols
        assert event_cols["created_by_user_id"].nullable is True

        # insight_goal has both user_id + project_id FKs and no legacy
        # source_project_slug column (the fold drops it).
        goal_table = next(t for t in spec.tables if t.name == "insight_goal")
        goal_cols = {c.name for c in goal_table.columns}
        assert "user_id" in goal_cols
        assert "project_id" in goal_cols
        assert "source_project_slug" not in goal_cols
        fk_targets = {fk.ref_table for fk in goal_table.foreign_keys}
        assert fk_targets == {"user", "project"}

    def test_ai_spec_exists(self) -> None:
        """Test AI migration spec is defined."""
        assert "ai" in MIGRATION_SPECS
        assert AI_MIGRATION.service_name == "ai"
        table_names = [t.name for t in AI_MIGRATION.tables]
        assert len(AI_MIGRATION.tables) == len(set(table_names)), (
            "duplicate table in the AI spec"
        )
        # LLM catalog tables
        assert "llm_org" in table_names
        assert "large_language_model" in table_names
        assert "llm_deployment" in table_names
        assert "llm_modality" in table_names
        assert "llm_price" in table_names
        assert "llm_usage" in table_names
        assert "llm_active_selection" in table_names
        # Conversation tables
        assert "conversation" in table_names
        assert "conversation_message" in table_names

    def test_ai_has_foreign_key(self) -> None:
        """Test AI conversation_message has foreign key to conversation."""
        message_table = next(
            t for t in AI_MIGRATION.tables if t.name == "conversation_message"
        )
        assert len(message_table.foreign_keys) == 1
        assert message_table.foreign_keys[0].ref_table == "conversation"

    def test_blog_spec_exists(self) -> None:
        """Test blog migration spec is defined."""
        assert "blog" in MIGRATION_SPECS
        assert BLOG_MIGRATION.service_name == "blog"
        assert len(BLOG_MIGRATION.tables) == 3

        table_names = [t.name for t in BLOG_MIGRATION.tables]
        assert table_names == ["blog_post", "blog_tag", "blog_post_tag"]

        post_table = BLOG_MIGRATION.tables[0]
        post_columns = [col.name for col in post_table.columns]
        assert "title" in post_columns
        assert "slug" in post_columns
        assert "content" in post_columns
        assert "status" in post_columns

        index_names = [idx.name for idx in post_table.indexes]
        assert "ix_blog_post_slug" in index_names
        assert any(idx.unique for idx in post_table.indexes)

        link_table = BLOG_MIGRATION.tables[2]
        assert {fk.ref_table for fk in link_table.foreign_keys} == {
            "blog_post",
            "blog_tag",
        }

    def test_finance_spec_exists(self) -> None:
        """Test finance migration spec is defined (reference-data tables)."""
        from aegis.core.migration_generator import FINANCE_MIGRATION

        assert "finance" in MIGRATION_SPECS
        assert FINANCE_MIGRATION.service_name == "finance"
        # Public schema (SQLite + Postgres); no Postgres-only namespacing.
        assert FINANCE_MIGRATION.schema is None

        table_names = [t.name for t in FINANCE_MIGRATION.tables]
        assert "finance_currency" in table_names
        assert "finance_fx_rate" in table_names

        currency = next(
            t for t in FINANCE_MIGRATION.tables if t.name == "finance_currency"
        )
        assert {c.name for c in currency.columns} >= {"code", "decimals", "kind"}
        assert any(idx.unique for idx in currency.indexes)
        assert {ck.name for ck in currency.check_constraints} == {
            "ck_finance_currency_kind",
            "ck_finance_currency_decimals",
        }

        fx = next(t for t in FINANCE_MIGRATION.tables if t.name == "finance_fx_rate")
        # rate_e8 is a BigInteger scaled integer, not a float.
        rate_col = next(c for c in fx.columns if c.name == "rate_e8")
        assert rate_col.type == "sa.BigInteger()"
        assert {fk.ref_table for fk in fx.foreign_keys} == {"finance_currency"}


class TestOrgMigrationSpec:
    """Test organization migration specification."""

    def test_org_spec_exists(self) -> None:
        """Test org migration spec is defined in MIGRATION_SPECS."""
        assert "auth_org" in MIGRATION_SPECS
        assert ORG_MIGRATION.service_name == "auth_org"

    def test_org_has_three_tables(self) -> None:
        """Organization migration should have three tables."""
        assert len(ORG_MIGRATION.tables) == 3

    def test_organization_table_columns(self) -> None:
        """Organization table should have expected columns."""
        org_table = next(t for t in ORG_MIGRATION.tables if t.name == "organization")
        column_names = [col.name for col in org_table.columns]

        assert "name" in column_names
        assert "slug" in column_names
        assert "description" in column_names
        assert "is_active" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

    def test_org_member_table_columns(self) -> None:
        """Organization member table should have expected columns."""
        member_table = next(
            t for t in ORG_MIGRATION.tables if t.name == "organization_member"
        )
        column_names = [col.name for col in member_table.columns]

        assert "organization_id" in column_names
        assert "user_id" in column_names
        assert "role" in column_names
        assert "joined_at" in column_names

    def test_org_member_foreign_keys(self) -> None:
        """Organization member table should have foreign keys to org and user."""
        member_table = next(
            t for t in ORG_MIGRATION.tables if t.name == "organization_member"
        )
        assert len(member_table.foreign_keys) == 2

        ref_tables = {fk.ref_table for fk in member_table.foreign_keys}
        assert "organization" in ref_tables
        assert "user" in ref_tables


class TestAuthLockoutColumns:
    """Test auth migration lockout columns."""

    def test_auth_migration_has_lockout_columns(self) -> None:
        """Verify failed_login_attempts and locked_until in user table columns."""
        column_names = [col.name for col in AUTH_MIGRATION.tables[0].columns]
        assert "failed_login_attempts" in column_names
        assert "locked_until" in column_names

        # Check types and defaults
        lockout_col = next(
            c
            for c in AUTH_MIGRATION.tables[0].columns
            if c.name == "failed_login_attempts"
        )
        assert lockout_col.type == "sa.Integer()"
        assert lockout_col.nullable is False
        assert lockout_col.default == "0"

        locked_col = next(
            c for c in AUTH_MIGRATION.tables[0].columns if c.name == "locked_until"
        )
        assert locked_col.type == "sa.DateTime()"
        assert locked_col.nullable is True


class TestAuthTokensMigrationSpec:
    """Test auth_tokens migration specification."""

    def test_auth_tokens_spec_exists(self) -> None:
        """Verify auth_tokens is in MIGRATION_SPECS with all three
        auth-token tables (refresh_token added for issue #633)."""
        assert "auth_tokens" in MIGRATION_SPECS
        assert AUTH_TOKENS_MIGRATION.service_name == "auth_tokens"
        assert len(AUTH_TOKENS_MIGRATION.tables) == 3
        table_names = [t.name for t in AUTH_TOKENS_MIGRATION.tables]
        assert "password_reset_token" in table_names
        assert "email_verification_token" in table_names
        assert "refresh_token" in table_names

    def test_auth_tokens_refresh_token_table(self) -> None:
        """Verify refresh_token table has the session-metadata columns."""
        table = next(
            t for t in AUTH_TOKENS_MIGRATION.tables if t.name == "refresh_token"
        )
        column_names = [col.name for col in table.columns]
        assert "token" in column_names
        assert "user_id" in column_names
        assert "family_id" in column_names
        assert "source" in column_names
        assert "user_agent" in column_names
        assert "ip" in column_names
        assert "last_used_at" in column_names

    def test_auth_tokens_password_reset_table(self) -> None:
        """Verify password_reset_token table has correct columns."""
        table = next(
            t for t in AUTH_TOKENS_MIGRATION.tables if t.name == "password_reset_token"
        )
        column_names = [col.name for col in table.columns]
        assert "id" in column_names
        assert "user_id" in column_names
        assert "token" in column_names
        assert "created_at" in column_names
        assert "used" in column_names

    def test_auth_tokens_email_verification_table(self) -> None:
        """Verify email_verification_token table has correct columns."""
        table = next(
            t
            for t in AUTH_TOKENS_MIGRATION.tables
            if t.name == "email_verification_token"
        )
        column_names = [col.name for col in table.columns]
        assert "id" in column_names
        assert "user_id" in column_names
        assert "token" in column_names
        assert "created_at" in column_names
        assert "used" in column_names


class TestOrgInviteTable:
    """Test org_invite table in organization migration."""

    def test_org_invite_table_columns(self) -> None:
        """Verify org_invite table has correct columns."""
        invite_table = next(t for t in ORG_MIGRATION.tables if t.name == "org_invite")
        column_names = [col.name for col in invite_table.columns]
        assert "id" in column_names
        assert "organization_id" in column_names
        assert "email" in column_names
        assert "role" in column_names
        assert "invited_by" in column_names
        assert "status" in column_names
        assert "token" in column_names
        assert "created_at" in column_names

    def test_org_invite_foreign_keys(self) -> None:
        """Verify org_invite has FKs to organization and user."""
        invite_table = next(t for t in ORG_MIGRATION.tables if t.name == "org_invite")
        assert len(invite_table.foreign_keys) == 2
        ref_tables = {fk.ref_table for fk in invite_table.foreign_keys}
        assert "organization" in ref_tables
        assert "user" in ref_tables


class TestDataclasses:
    """Test dataclass definitions."""

    def test_column_spec_defaults(self) -> None:
        """Test ColumnSpec default values."""
        col = ColumnSpec("test", "sa.String()")
        assert col.nullable is True
        assert col.primary_key is False
        assert col.default is None

    def test_index_spec_defaults(self) -> None:
        """Test IndexSpec default values."""
        idx = IndexSpec("test_idx", ["col1"])
        assert idx.unique is False

    def test_table_spec_defaults(self) -> None:
        """Test TableSpec default values."""
        table = TableSpec("test", [ColumnSpec("id", "sa.Integer()")])
        assert table.indexes == []
        assert table.foreign_keys == []


class TestVoiceMigrationSpec:
    """Test AI voice migration specification.

    The voice migration creates the voice_usage table for tracking
    TTS (Text-to-Speech) and STT (Speech-to-Text) usage.
    """

    def test_ai_voice_spec_exists(self) -> None:
        """Test ai_voice migration spec is defined in MIGRATION_SPECS."""
        assert "ai_voice" in MIGRATION_SPECS
        assert VOICE_MIGRATION.service_name == "ai_voice"

    def test_voice_migration_has_one_table(self) -> None:
        """Voice migration should have a single voice_usage table."""
        assert len(VOICE_MIGRATION.tables) == 1
        assert VOICE_MIGRATION.tables[0].name == "voice_usage"

    def test_voice_usage_table_core_columns(self) -> None:
        """Voice usage table should have core columns for all usage types."""
        table = VOICE_MIGRATION.tables[0]
        column_names = [col.name for col in table.columns]

        # Core columns shared by TTS and STT
        assert "id" in column_names
        assert "usage_type" in column_names  # "tts" or "stt"
        assert "provider" in column_names
        assert "model" in column_names
        assert "user_id" in column_names
        assert "timestamp" in column_names
        assert "latency_ms" in column_names
        assert "total_cost" in column_names
        assert "success" in column_names
        assert "error_message" in column_names

    def test_voice_usage_table_tts_columns(self) -> None:
        """Voice usage table should have TTS-specific columns."""
        table = VOICE_MIGRATION.tables[0]
        column_names = [col.name for col in table.columns]

        # TTS-specific columns (null for STT records)
        assert "voice" in column_names
        assert "input_characters" in column_names
        assert "output_duration_seconds" in column_names
        assert "output_audio_bytes" in column_names

    def test_voice_usage_table_stt_columns(self) -> None:
        """Voice usage table should have STT-specific columns."""
        table = VOICE_MIGRATION.tables[0]
        column_names = [col.name for col in table.columns]

        # STT-specific columns (null for TTS records)
        assert "input_duration_seconds" in column_names
        assert "input_audio_bytes" in column_names
        assert "output_characters" in column_names
        assert "detected_language" in column_names

    def test_voice_usage_table_indexes(self) -> None:
        """Voice usage table should have appropriate indexes."""
        table = VOICE_MIGRATION.tables[0]
        index_names = [idx.name for idx in table.indexes]

        assert "ix_voice_usage_usage_type" in index_names
        assert "ix_voice_usage_provider" in index_names
        assert "ix_voice_usage_user_id" in index_names
        assert "ix_voice_usage_timestamp" in index_names

    def test_voice_migration_description(self) -> None:
        """Voice migration should have a descriptive description."""
        assert "voice" in VOICE_MIGRATION.description.lower()
        assert "tts" in VOICE_MIGRATION.description.lower()
        assert "stt" in VOICE_MIGRATION.description.lower()


class TestGetServicesNeedingMigrationsVoice:
    """Test detection of ai_voice service needing migrations."""

    def test_ai_voice_needs_migration_when_enabled(self) -> None:
        """AI voice should need migration when all conditions met."""
        context = {
            "include_auth": False,
            "include_ai": True,
            "ai_backend": "sqlite",
            "ai_voice": True,
        }
        result = get_services_needing_migrations(context)
        assert "ai_voice" in result

    def test_ai_voice_needs_migration_with_yes_string(self) -> None:
        """AI voice should work with 'yes' string (cookiecutter format)."""
        context = {
            "include_auth": False,
            "include_ai": "yes",
            "ai_backend": "sqlite",
            "ai_voice": "yes",
        }
        result = get_services_needing_migrations(context)
        assert "ai_voice" in result

    def test_ai_voice_not_needed_when_disabled(self) -> None:
        """AI voice should not need migration when voice disabled."""
        context = {
            "include_auth": False,
            "include_ai": True,
            "ai_backend": "sqlite",
            "ai_voice": False,
        }
        result = get_services_needing_migrations(context)
        assert "ai_voice" not in result

    def test_ai_voice_not_needed_without_persistence(self) -> None:
        """AI voice should not need migration with memory backend."""
        context = {
            "include_auth": False,
            "include_ai": True,
            "ai_backend": "memory",
            "ai_voice": True,
        }
        result = get_services_needing_migrations(context)
        assert "ai_voice" not in result

    def test_ai_voice_not_needed_without_ai(self) -> None:
        """AI voice should not need migration without AI service."""
        context = {
            "include_auth": False,
            "include_ai": False,
            "ai_backend": "sqlite",
            "ai_voice": True,
        }
        result = get_services_needing_migrations(context)
        assert "ai_voice" not in result

    def test_full_stack_with_voice(self) -> None:
        """Full stack with auth, AI, and voice should have all migrations."""
        context = {
            "include_auth": True,
            "include_ai": True,
            "ai_backend": "sqlite",
            "ai_voice": True,
        }
        result = get_services_needing_migrations(context)
        assert result == [
            "auth",
            "auth_tokens",
            "ai",
            "ai_agents",
            "ai_sentiment",
            "ai_voice",
        ]


class TestAgentsMigration:
    """The agent registry rides its own spec, gated exactly like ``ai``."""

    def test_ai_with_sqlite_includes_agents(self) -> None:
        """A persistence backend pulls in the agent registry migration."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert "ai_agents" in result
        # Chains directly after the ai catalog tables.
        assert result.index("ai_agents") == result.index("ai") + 1

    def test_ai_with_memory_excludes_agents(self) -> None:
        """Memory backend means no agent tables (code-fallback config)."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert "ai_agents" not in result

    def test_agents_in_migration_specs(self) -> None:
        """The spec is registered on the ai service."""
        from aegis.core.migration_generator import AGENTS_MIGRATION

        assert "ai_agents" in MIGRATION_SPECS
        assert AGENTS_MIGRATION.service_name == "ai_agents"


class TestKnowledgeMigration:
    """KB metadata tables gate on ai + persistence + the rag flag."""

    def test_ai_sqlite_with_rag_includes_knowledge(self) -> None:
        context = {
            "include_auth": False,
            "include_ai": True,
            "ai_backend": "sqlite",
            "ai_rag": True,
        }
        result = get_services_needing_migrations(context)
        assert "ai_knowledge" in result
        assert result.index("ai_knowledge") == result.index("ai_agents") + 1

    def test_no_rag_flag_excludes_knowledge(self) -> None:
        context = {"include_auth": False, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert "ai_knowledge" not in result

    def test_rag_with_memory_backend_excludes_knowledge(self) -> None:
        context = {
            "include_auth": False,
            "include_ai": True,
            "ai_backend": "memory",
            "ai_rag": True,
        }
        result = get_services_needing_migrations(context)
        assert "ai_knowledge" not in result


class TestSentimentMigration:
    """Sentiment rides its own spec, gated on ai + persistence."""

    def test_ai_with_sqlite_includes_sentiment(self) -> None:
        context = {"include_auth": False, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert "ai_sentiment" in result
        assert result.index("ai_sentiment") > result.index("ai_agents")

    def test_ai_with_memory_excludes_sentiment(self) -> None:
        context = {"include_auth": False, "include_ai": True, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert "ai_sentiment" not in result


class TestForeignKeyOnDeleteRendering:
    """``ForeignKeySpec.ondelete`` must reach the rendered migration.

    Without DB-level cascade, ``Project.metrics`` /
    ``Project.events`` / ``Project.goals`` relationships use
    ``passive_deletes=True`` but the database doesn't honour the cascade,
    so deleting a project with any child rows blows up at the FK. These
    tests pin the renderer behaviour so the failure mode can't sneak
    back in.
    """

    def test_spec_round_trips_ondelete(self) -> None:
        """ForeignKeySpec accepts and stores the ondelete option."""
        from aegis.core.migration_generator import ForeignKeySpec

        fk = ForeignKeySpec(["project_id"], "project", ["id"], ondelete="CASCADE")
        assert fk.ondelete == "CASCADE"
        # Default still None for back-compat with every other FK.
        assert ForeignKeySpec(["x"], "y", ["id"]).ondelete is None


class TestSchemaQualifiedRendering:
    """Schema support: a spec can render its tables into a Postgres schema."""

    def _schema_spec(self) -> ServiceMigrationSpec:
        """A spec exercising every schema-rendering path in one go:
        columns-only PK, intra-schema FK, cross-schema FK, index, check.
        """
        return ServiceMigrationSpec(
            service_name="widget",
            description="Widget tables",
            schema="widget",
            tables=[
                TableSpec(
                    name="parent",
                    columns=[
                        ColumnSpec(
                            "id", "sa.Integer()", nullable=False, primary_key=True
                        ),
                        ColumnSpec("name", "sa.String(64)", nullable=False),
                    ],
                    indexes=[IndexSpec("ix_parent_name", ["name"])],
                ),
                TableSpec(
                    name="child",
                    columns=[
                        ColumnSpec(
                            "id", "sa.Integer()", nullable=False, primary_key=True
                        ),
                        ColumnSpec("parent_id", "sa.Integer()", nullable=False),
                        ColumnSpec("user_id", "sa.Integer()", nullable=True),
                        ColumnSpec("status", "sa.String(8)", nullable=False),
                    ],
                    indexes=[IndexSpec("ix_child_parent", ["parent_id"])],
                    foreign_keys=[
                        # intra-schema: resolves to the spec's own schema
                        ForeignKeySpec(
                            ["parent_id"], "parent", ["id"], ondelete="CASCADE"
                        ),
                        # cross-schema: explicit ref_schema
                        ForeignKeySpec(["user_id"], "user", ["id"], ref_schema="auth"),
                    ],
                    check_constraints=[
                        CheckConstraintSpec("ck_child_status", "status IN ('a', 'b')"),
                    ],
                ),
            ],
        )

    def test_schema_spec_renders_valid_python(self) -> None:
        """A schema'd spec compiles and creates the schema first."""
        src = _render_migration(self._schema_spec(), "002", "001")
        ast.parse(src)  # raises SyntaxError on bad render
        assert 'CREATE SCHEMA IF NOT EXISTS "widget"' in src

    def test_tables_indexes_qualified(self) -> None:
        """create_table and create_index carry the schema kwarg."""
        src = _render_migration(self._schema_spec(), "002", "001")
        assert src.count("schema='widget'") >= 2  # both tables
        assert "schema='widget')" in src  # on create_index

    def test_fk_referents_qualified(self) -> None:
        """Intra-schema FKs use the spec schema; cross-schema use ref_schema."""
        src = _render_migration(self._schema_spec(), "002", "001")
        assert "['widget.parent.id']" in src  # intra-schema
        assert "['auth.user.id']" in src  # cross-schema

    def test_no_schema_spec_is_unqualified(self) -> None:
        """A spec without a schema renders no schema artifacts (back-compat)."""
        src = _render_migration(AUTH_MIGRATION, "001", None)
        ast.parse(src)
        assert "CREATE SCHEMA" not in src
        assert "schema=" not in src
        # FK referents stay bare (no leading schema)
        assert "['user.id']" in src


class TestSchedulerComponentMigration:
    """The scheduler component rides the service migration rail."""

    def test_scheduler_in_registry(self) -> None:
        """Component migration is collected alongside services."""
        assert "scheduler" in MIGRATION_SPECS
        assert MIGRATION_SPECS["scheduler"].schema == "scheduler"

    def test_spec_schema_and_table(self) -> None:
        assert SCHEDULER_MIGRATION.schema == "scheduler"
        assert [t.name for t in SCHEDULER_MIGRATION.tables] == ["job_execution"]

    def test_selected_for_postgres(self) -> None:
        """Postgres scheduler persistence selects the schema'd migration."""
        context = {"include_scheduler": True, "scheduler_backend": "postgres"}
        assert "scheduler" in get_services_needing_migrations(context)

    def test_selected_for_sqlite(self) -> None:
        """Any persistent job store gets its tables from a revision."""
        context = {"include_scheduler": True, "scheduler_backend": "sqlite"}
        assert "scheduler" in get_services_needing_migrations(context)

    def test_not_selected_for_memory(self) -> None:
        context = {"include_scheduler": True, "scheduler_backend": "memory"}
        assert "scheduler" not in get_services_needing_migrations(context)

    def test_not_selected_when_absent(self) -> None:
        context = {"include_auth": True}
        assert "scheduler" not in get_services_needing_migrations(context)


class TestPluginMigrations:
    """Third-party plugins ship ``PluginSpec.migrations``; ``aegis add
    <plugin>`` writes them through the same rail in-tree services use,
    without the plugin having to be in the static registry."""

    @staticmethod
    def _plugin_spec(schema: str | None = "crawler") -> Any:
        from types import SimpleNamespace

        migration = ServiceMigrationSpec(
            service_name="crawler",
            description="Crawler documents store",
            schema=schema,
            tables=[
                TableSpec(
                    name="documents",
                    columns=[
                        ColumnSpec(
                            "id", "sa.Integer()", nullable=False, primary_key=True
                        ),
                        ColumnSpec("source_url", "sa.Text()", nullable=False),
                    ],
                ),
            ],
        )
        return SimpleNamespace(name="crawl4ai", migrations=[migration])


class TestMigrationsAreIdempotentOnPrepopulatedSQLite:
    """SQLite projects run ``SQLModel.metadata.create_all`` at startup
    (``app/core/db.py``), so their database already holds every table the
    models define - ahead of any migration. A revision the project predates
    is then delivered by ``aegis update`` and its ``create_table`` collides
    with a table ``create_all`` already made (#1024: ``table
    password_reset_token already exists``).

    Postgres projects are migration-only and never hit this, so the guard
    is exactly what the ticket asked for: inspector-checked per table, one
    chain serving both a pre-populated and a fresh database.
    """

    def _apply(self, source: str, url: str) -> None:
        """Execute a rendered migration's ``upgrade()`` against ``url``."""
        import sys
        import types

        import sqlalchemy as sa
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        # Rendered migrations ``import sqlmodel`` (a generated-project
        # dependency the framework venv does not carry). Only ``upgrade()``
        # is under test, so a stub module satisfies the import.
        stub = types.ModuleType("sqlmodel")
        stub.sql = types.ModuleType("sqlmodel.sql")  # type: ignore[attr-defined]
        stub.sql.sqltypes = types.ModuleType("sqlmodel.sql.sqltypes")  # type: ignore[attr-defined]
        stub.sql.sqltypes.AutoString = sa.String  # type: ignore[attr-defined]
        saved = {
            k: sys.modules.get(k)
            for k in ("sqlmodel", "sqlmodel.sql", "sqlmodel.sql.sqltypes")
        }
        sys.modules["sqlmodel"] = stub
        sys.modules["sqlmodel.sql"] = stub.sql  # type: ignore[attr-defined]
        sys.modules["sqlmodel.sql.sqltypes"] = stub.sql.sqltypes  # type: ignore[attr-defined]
        try:
            engine = sa.create_engine(url)
            with engine.begin() as conn:
                ctx = MigrationContext.configure(conn)
                with Operations.context(ctx):
                    ns: dict = {}
                    exec(compile(source, "<migration>", "exec"), ns)
                    ns["upgrade"]()
            engine.dispose()
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_create_table_skips_tables_create_all_already_made(
        self, tmp_path: Path
    ) -> None:
        import sqlalchemy as sa

        url = f"sqlite:///{tmp_path / 'app.db'}"
        source = _render_migration(AUTH_TOKENS_MIGRATION, "004", "003")

        # First application: fresh DB, everything created.
        self._apply(source, url)
        engine = sa.create_engine(url)
        names = set(sa.inspect(engine).get_table_names())
        assert "password_reset_token" in names
        assert "email_verification_token" in names
        engine.dispose()

        # Second application against the SAME database: every table now
        # pre-exists, exactly the state ``create_all`` leaves a SQLite
        # project in. Must not raise "already exists".
        self._apply(source, url)

    def test_add_column_on_existing_table_still_fails_loudly(
        self, tmp_path: Path
    ) -> None:
        """The table guard must NOT extend to ``add_column``: a column that
        already exists is a real schema conflict (#1023-shaped), not
        ``create_all`` pre-creation, and hiding it would hide the bug."""
        import sqlalchemy as sa

        url = f"sqlite:///{tmp_path / 'app.db'}"
        engine = sa.create_engine(url)
        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)"))
        engine.dispose()

        source = (
            "from alembic import op\nimport sqlalchemy as sa\n"
            "def upgrade():\n"
            "    with op.batch_alter_table('t') as b:\n"
            "        b.add_column(sa.Column('x', sa.String(), nullable=True))\n"
        )
        with pytest.raises(Exception):
            self._apply(source, url)
