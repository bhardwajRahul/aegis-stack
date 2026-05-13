"""
Tests for dynamic migration generator module.

These tests validate the migration generation functionality that creates
Alembic migration files on-demand for services like auth and AI.
"""

from pathlib import Path

from aegis.core.migration_generator import (
    AI_MIGRATION,
    AUTH_MIGRATION,
    AUTH_RBAC_MIGRATION,
    AUTH_TOKENS_MIGRATION,
    BLOG_MIGRATION,
    INSIGHTS_MIGRATION,
    MIGRATION_SPECS,
    ORG_MIGRATION,
    VOICE_MIGRATION,
    ColumnSpec,
    IndexSpec,
    TableSpec,
    _build_insights_migration,
    generate_migration,
    generate_migrations_for_services,
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
        assert result == ["ai"]

    def test_ai_with_memory_no_migrations(self) -> None:
        """Test AI service with memory backend does NOT need migrations."""
        context = {"include_auth": False, "include_ai": True, "ai_backend": "memory"}
        result = get_services_needing_migrations(context)
        assert result == []

    def test_both_services(self) -> None:
        """Test both auth and AI services need migrations."""
        context = {"include_auth": True, "include_ai": True, "ai_backend": "sqlite"}
        result = get_services_needing_migrations(context)
        assert result == ["auth", "auth_tokens", "ai"]

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

    def test_unknown_service(self, tmp_path: Path) -> None:
        """Test returns None for unknown service."""
        result = generate_migration(tmp_path, "unknown")
        assert result is None

    def test_generates_auth_migration(self, tmp_path: Path) -> None:
        """Test generates auth migration file."""
        result = generate_migration(tmp_path, "auth")

        assert result is not None
        assert result.exists()
        assert result.name == "001_auth.py"

        # Verify content
        content = result.read_text()
        assert "revision = '001'" in content
        assert "down_revision = None" in content
        assert "op.create_table" in content
        assert "'user'" in content
        assert "'email'" in content
        assert "'is_verified'" in content
        assert "'last_login'" in content
        # Only role is in auth_rbac migration, not base
        assert "'role'" not in content

    def test_generates_auth_rbac_migration(self, tmp_path: Path) -> None:
        """Test generates auth_rbac migration with ALTER TABLE."""
        # Generate base auth first so rbac gets correct revision chain
        generate_migration(tmp_path, "auth")
        result = generate_migration(tmp_path, "auth_rbac")

        assert result is not None
        assert result.exists()
        assert result.name == "002_auth_rbac.py"

        content = result.read_text()
        assert "revision = '002'" in content
        assert "down_revision = '001'" in content
        # Should use add_column, NOT create_table
        assert "op.add_column" in content
        assert "op.create_table" not in content
        assert "'role'" in content
        # is_verified and last_login are in base auth, not rbac
        assert "'is_verified'" not in content
        assert "'last_login'" not in content
        # Downgrade should use drop_column
        assert "op.drop_column" in content

    def test_generates_ai_migration(self, tmp_path: Path) -> None:
        """Test generates AI migration file."""
        result = generate_migration(tmp_path, "ai")

        assert result is not None
        assert result.exists()
        assert result.name == "001_ai.py"

        # Verify content
        content = result.read_text()
        assert "'conversation'" in content
        assert "'conversation_message'" in content
        assert "op.create_index" in content

    def test_generates_blog_migration(self, tmp_path: Path) -> None:
        """Test generates blog migration file."""
        result = generate_migration(tmp_path, "blog")

        assert result is not None
        assert result.exists()
        assert result.name == "001_blog.py"

        content = result.read_text()
        assert "'blog_post'" in content
        assert "'blog_tag'" in content
        assert "'blog_post_tag'" in content
        assert "ck_blog_post_status" in content
        assert "ondelete='CASCADE'" in content

    def test_creates_versions_directory(self, tmp_path: Path) -> None:
        """Test creates versions directory if it doesn't exist."""
        assert not (tmp_path / "alembic" / "versions").exists()

        generate_migration(tmp_path, "auth")

        assert (tmp_path / "alembic" / "versions").exists()


class TestGenerateMigrationsForServices:
    """Test batch migration generation."""

    def test_generates_in_order(self, tmp_path: Path) -> None:
        """Test generates migrations in specified order."""
        result = generate_migrations_for_services(tmp_path, ["auth", "ai"])

        assert len(result) == 2
        assert result[0].name == "001_auth.py"
        assert result[1].name == "002_ai.py"

        # Verify down_revision chain
        auth_content = result[0].read_text()
        ai_content = result[1].read_text()

        assert "down_revision = None" in auth_content
        assert "down_revision = '001'" in ai_content

    def test_skips_existing_migrations(self, tmp_path: Path) -> None:
        """Test skips services that already have migrations."""
        # Create existing auth migration
        versions_dir = tmp_path / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "001_auth.py").write_text("# existing")

        result = generate_migrations_for_services(tmp_path, ["auth", "ai"])

        # Should only generate AI
        assert len(result) == 1
        assert result[0].name == "002_ai.py"

    def test_skips_unknown_services(self, tmp_path: Path) -> None:
        """Test skips unknown services without error."""
        result = generate_migrations_for_services(tmp_path, ["unknown", "auth"])

        assert len(result) == 1
        assert result[0].name == "001_auth.py"

    def test_empty_list(self, tmp_path: Path) -> None:
        """Test handles empty service list."""
        result = generate_migrations_for_services(tmp_path, [])
        assert result == []


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
        assert len(AI_MIGRATION.tables) == 8

        table_names = [t.name for t in AI_MIGRATION.tables]
        # LLM catalog tables
        assert "llm_vendor" in table_names
        assert "large_language_model" in table_names
        assert "llm_deployment" in table_names
        assert "llm_modality" in table_names
        assert "llm_price" in table_names
        assert "llm_usage" in table_names
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


class TestGenerateAuthTokensMigration:
    """Test auth_tokens migration file generation."""

    def test_generates_auth_tokens_migration(self, tmp_path: Path) -> None:
        """Generate auth_tokens migration, verify file content has both tables."""
        result = generate_migration(tmp_path, "auth_tokens")

        assert result is not None
        assert result.exists()
        assert result.name == "001_auth_tokens.py"

        content = result.read_text()
        assert "'password_reset_token'" in content
        assert "'email_verification_token'" in content
        assert "op.create_table" in content
        assert "op.create_index" in content

    def test_auth_rbac_org_full_chain(self, tmp_path: Path) -> None:
        """Generate auth + auth_tokens + auth_rbac + auth_org, verify 4 files with correct revision chain."""
        result = generate_migrations_for_services(
            tmp_path, ["auth", "auth_tokens", "auth_rbac", "auth_org"]
        )

        assert len(result) == 4
        assert result[0].name == "001_auth.py"
        assert result[1].name == "002_auth_tokens.py"
        assert result[2].name == "003_auth_rbac.py"
        assert result[3].name == "004_auth_org.py"

        # Verify revision chain
        content_0 = result[0].read_text()
        content_1 = result[1].read_text()
        content_2 = result[2].read_text()
        content_3 = result[3].read_text()

        assert "down_revision = None" in content_0
        assert "down_revision = '001'" in content_1
        assert "down_revision = '002'" in content_2
        assert "down_revision = '003'" in content_3


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
        assert result == ["auth", "auth_tokens", "ai", "ai_voice"]


class TestGenerateVoiceMigration:
    """Test voice migration file generation."""

    def test_generates_voice_migration(self, tmp_path: Path) -> None:
        """Test generates ai_voice migration file."""
        result = generate_migration(tmp_path, "ai_voice")

        assert result is not None
        assert result.exists()
        assert result.name == "001_ai_voice.py"

        # Verify content
        content = result.read_text()
        assert "'voice_usage'" in content
        assert "'usage_type'" in content
        assert "op.create_index" in content

    def test_voice_migration_after_ai(self, tmp_path: Path) -> None:
        """Test voice migration chains correctly after AI migration."""
        result = generate_migrations_for_services(tmp_path, ["ai", "ai_voice"])

        assert len(result) == 2
        assert result[0].name == "001_ai.py"
        assert result[1].name == "002_ai_voice.py"

        # Verify down_revision chain
        ai_content = result[0].read_text()
        voice_content = result[1].read_text()

        assert "down_revision = None" in ai_content
        assert "down_revision = '001'" in voice_content

    def test_full_migration_chain(self, tmp_path: Path) -> None:
        """Test full migration chain with auth, AI, and voice."""
        result = generate_migrations_for_services(tmp_path, ["auth", "ai", "ai_voice"])

        assert len(result) == 3
        assert result[0].name == "001_auth.py"
        assert result[1].name == "002_ai.py"
        assert result[2].name == "003_ai_voice.py"

        # Verify chain
        voice_content = result[2].read_text()
        assert "down_revision = '002'" in voice_content


class TestCheckConstraintRendering:
    """Test that ``CheckConstraintSpec`` entries make it into the
    rendered migration output.

    The auth spec defines a CHECK constraint on the
    ``user_oauth_identity.provider`` column to keep the column locked
    to the supported provider list at the database level (project
    convention is VARCHAR + CHECK rather than native Postgres enums,
    for SQLite parity).
    """

    def test_auth_migration_includes_oauth_provider_check(self, tmp_path: Path) -> None:
        """Generated auth migration must render the OAuth provider check."""
        from aegis.core.migration_generator import generate_migration

        migration_path = generate_migration(tmp_path, "auth")
        assert migration_path is not None
        content = migration_path.read_text()

        # The CHECK constraint goes through the new template branch in
        # ``migration_generator.py`` — assert the rendered output.
        assert "sa.CheckConstraint(" in content
        assert "ck_user_oauth_identity_provider" in content
        assert "provider IN ('github', 'google')" in content

    def test_specs_without_check_constraints_skip_block(self, tmp_path: Path) -> None:
        """Specs without CHECK constraints render no ``sa.CheckConstraint``.

        Guards against the ``{% for chk %}`` loop accidentally emitting
        empty / malformed output for tables that don't declare any.
        """
        from aegis.core.migration_generator import generate_migration

        # AI migration uses no CHECK constraints (yet) — sanity-check it.
        migration_path = generate_migration(tmp_path, "ai")
        assert migration_path is not None
        content = migration_path.read_text()

        assert "sa.CheckConstraint(" not in content


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

    def test_per_user_insights_renders_cascade(self, tmp_path: Path) -> None:
        """Per-user insights migration emits ondelete='CASCADE' on the
        three project_id FKs (metric, event, goal).

        Drives ``generate_migration`` with ``insights_per_user=true``
        context so the spec swaps to the per-user variant.
        """
        from aegis.core.migration_generator import generate_migration

        migration_path = generate_migration(
            tmp_path, "insights", {"insights_per_user": True}
        )
        assert migration_path is not None
        content = migration_path.read_text()

        # The cascade marker should appear once per project_id FK.
        assert content.count("ondelete='CASCADE'") == 3
        # And it should sit on FKs that point to ``project``, not
        # accidentally on the user FKs.
        assert (
            "['project.id'], ondelete='CASCADE'" in content
            or "['project.id'],ondelete='CASCADE'" in content
        )

    def test_per_user_insights_user_fk_has_no_cascade(self, tmp_path: Path) -> None:
        """``created_by_user_id`` and ``user_id`` FKs must NOT cascade —
        deleting a user shouldn't nuke insights data, just error.
        """
        from aegis.core.migration_generator import generate_migration

        migration_path = generate_migration(
            tmp_path, "insights", {"insights_per_user": True}
        )
        assert migration_path is not None
        content = migration_path.read_text()

        # Find every line that references user.id and verify none of
        # them carry ondelete=. (Substring scan over the rendered text
        # is enough — the spec only uses two user-targeting FKs.)
        for line in content.splitlines():
            if "['user.id']" in line:
                assert "ondelete" not in line, (
                    f"User FK should not cascade, got: {line!r}"
                )

    def test_shared_insights_renders_no_cascade(self, tmp_path: Path) -> None:
        """Shared-mode insights has no project_id FKs at all, so the
        rendered output must not mention CASCADE anywhere.
        """
        from aegis.core.migration_generator import generate_migration

        migration_path = generate_migration(tmp_path, "insights")
        assert migration_path is not None
        content = migration_path.read_text()

        assert "ondelete=" not in content
        assert "CASCADE" not in content
