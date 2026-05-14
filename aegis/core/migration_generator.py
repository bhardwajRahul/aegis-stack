"""
Dynamic migration generator for Aegis Stack services.

This module provides Django-style migration generation for services that require
database tables. It enables:
- Clean initial project generation with only needed migrations
- Adding services later via `aegis add` without migration conflicts
- DRY table definitions used for both scenarios

Usage:
    # During aegis init
    generate_migrations_for_services(project_path, ["auth", "ai"])

    # During aegis add
    if not service_has_migration(project_path, "ai"):
        generate_migration(project_path, "ai")
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, Template, TemplateNotFound


@dataclass
class ColumnSpec:
    """Specification for a database column."""

    name: str
    type: str  # SQLAlchemy type string, e.g., "sa.Integer()", "sa.String()"
    nullable: bool = True
    primary_key: bool = False
    default: str | None = None


@dataclass
class IndexSpec:
    """Specification for a database index."""

    name: str
    columns: list[str]
    unique: bool = False


@dataclass
class ForeignKeySpec:
    """Specification for a foreign key constraint.

    ``ondelete`` is the SQL ``ON DELETE`` referential action, passed
    straight through to ``sa.ForeignKeyConstraint`` /
    ``op.create_foreign_key``. Defaults to ``None`` (no cascade — the
    database's default behaviour, typically "RESTRICT"). Set to
    ``"CASCADE"`` for project-owned children that should die with
    their owner so SQLAlchemy ``passive_deletes=True`` relationships
    actually work end-to-end.
    """

    columns: list[str]
    ref_table: str
    ref_columns: list[str]
    ondelete: str | None = None


@dataclass
class CheckConstraintSpec:
    """Specification for a CHECK constraint on a table.

    Used to enforce enum-style allowed values without a native PG enum type.
    Rendered into ``op.create_table`` so it works on both SQLite and Postgres.
    """

    name: str
    sqltext: str  # e.g. "origin IN ('collector', 'user')"


@dataclass
class TableSpec:
    """Specification for a database table."""

    name: str
    columns: list[ColumnSpec]
    indexes: list[IndexSpec] = field(default_factory=list)
    foreign_keys: list[ForeignKeySpec] = field(default_factory=list)
    check_constraints: list[CheckConstraintSpec] = field(default_factory=list)


@dataclass
class AlterTableSpec:
    """Specification for altering an existing table.

    Add operations: ``add_columns``, ``add_foreign_keys``, ``add_indexes``.
    Drop operations: ``drop_columns``, ``drop_indexes``.

    All operations on a single ``AlterTableSpec`` run inside a single
    ``op.batch_alter_table`` block so they're atomic and SQLite-safe.
    Drop operations run BEFORE add operations within the block, since
    a common pattern is "replace this column / index with that one"
    and the new versions can reuse names.
    """

    name: str
    add_columns: list[ColumnSpec] = field(default_factory=list)
    add_foreign_keys: list[ForeignKeySpec] = field(default_factory=list)
    add_indexes: list[IndexSpec] = field(default_factory=list)
    drop_columns: list[str] = field(default_factory=list)
    drop_indexes: list[str] = field(default_factory=list)


@dataclass
class ServiceMigrationSpec:
    """Migration specification for a service.

    ``forward_only=True`` is for migrations that drop columns or merge
    schemas in non-recoverable ways. The generated ``downgrade()``
    raises ``NotImplementedError`` instead of trying to revert.
    """

    service_name: str
    tables: list[TableSpec]
    description: str
    alter_tables: list[AlterTableSpec] = field(default_factory=list)
    forward_only: bool = False


# ============================================================================
# Service Migration Definitions
# ============================================================================

AUTH_MIGRATION = ServiceMigrationSpec(
    service_name="auth",
    description="Auth service tables",
    tables=[
        TableSpec(
            name="user",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("email", "sa.String()", nullable=False),
                ColumnSpec("full_name", "sa.String()", nullable=True),
                ColumnSpec("is_active", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec(
                    "is_verified", "sa.Boolean()", nullable=False, default="False"
                ),
                ColumnSpec("hashed_password", "sa.String()", nullable=False),
                ColumnSpec("last_login", "sa.DateTime()", nullable=True),
                ColumnSpec(
                    "failed_login_attempts", "sa.Integer()", nullable=False, default="0"
                ),
                ColumnSpec("locked_until", "sa.DateTime()", nullable=True),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=True),
            ],
            indexes=[IndexSpec("ix_user_email", ["email"], unique=True)],
        ),
        # UserOAuthIdentity - links a user to a third-party identity.
        # One user can have many identities (GitHub + Google). The
        # (provider, provider_user_id) pair is unique to prevent identity
        # hijacking across accounts.
        TableSpec(
            name="user_oauth_identity",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("user_id", "sa.Integer()", nullable=False),
                ColumnSpec("provider", "sa.String(32)", nullable=False),
                # Stored as string to avoid caring whether the provider
                # uses int IDs (GitHub) or UUIDs (some others).
                ColumnSpec("provider_user_id", "sa.String(128)", nullable=False),
                ColumnSpec("provider_username", "sa.String(128)", nullable=True),
                ColumnSpec("provider_email", "sa.String(255)", nullable=True),
                ColumnSpec("avatar_url", "sa.String(512)", nullable=True),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec(
                    "uq_user_oauth_identity_provider_pid",
                    ["provider", "provider_user_id"],
                    unique=True,
                ),
                IndexSpec("ix_user_oauth_identity_user_id", ["user_id"]),
            ],
            foreign_keys=[
                ForeignKeySpec(["user_id"], "user", ["id"]),
            ],
            check_constraints=[
                CheckConstraintSpec(
                    name="ck_user_oauth_identity_provider",
                    sqltext="provider IN ('github', 'google')",
                ),
            ],
        ),
    ],
)

AUTH_RBAC_MIGRATION = ServiceMigrationSpec(
    service_name="auth_rbac",
    description="RBAC role column for user table",
    tables=[],
    alter_tables=[
        AlterTableSpec(
            name="user",
            add_columns=[
                ColumnSpec("role", "sa.String()", nullable=False, default="'user'"),
            ],
        ),
    ],
)

ORG_MIGRATION = ServiceMigrationSpec(
    service_name="auth_org",
    description="Organization and membership tables",
    tables=[
        TableSpec(
            name="organization",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("name", "sa.String()", nullable=False),
                ColumnSpec("slug", "sa.String()", nullable=False),
                ColumnSpec("description", "sa.String()", nullable=True),
                ColumnSpec("is_active", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=True),
            ],
            indexes=[
                IndexSpec("ix_organization_name", ["name"]),
                IndexSpec("ix_organization_slug", ["slug"], unique=True),
            ],
        ),
        TableSpec(
            name="organization_member",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("organization_id", "sa.Integer()", nullable=False),
                ColumnSpec("user_id", "sa.Integer()", nullable=False),
                ColumnSpec("role", "sa.String()", nullable=False, default="'member'"),
                ColumnSpec("joined_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec(
                    "ix_org_member_org_user",
                    ["organization_id", "user_id"],
                    unique=True,
                ),
                IndexSpec(
                    "ix_org_member_organization_id",
                    ["organization_id"],
                ),
                IndexSpec(
                    "ix_org_member_user_id",
                    ["user_id"],
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["organization_id"], "organization", ["id"]),
                ForeignKeySpec(["user_id"], "user", ["id"]),
            ],
        ),
        TableSpec(
            name="org_invite",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("organization_id", "sa.Integer()", nullable=False),
                ColumnSpec("email", "sa.String()", nullable=False),
                ColumnSpec("role", "sa.String()", nullable=False, default="'member'"),
                ColumnSpec("invited_by", "sa.Integer()", nullable=False),
                ColumnSpec(
                    "status", "sa.String()", nullable=False, default="'pending'"
                ),
                ColumnSpec("token", "sa.String()", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_org_invite_email", ["email"]),
                IndexSpec("ix_org_invite_org_id", ["organization_id"]),
                IndexSpec("ix_org_invite_token", ["token"], unique=True),
            ],
            foreign_keys=[
                ForeignKeySpec(["organization_id"], "organization", ["id"]),
                ForeignKeySpec(["invited_by"], "user", ["id"]),
            ],
        ),
    ],
)

AI_MIGRATION = ServiceMigrationSpec(
    service_name="ai",
    description="AI service tables (LLM catalog, usage tracking, conversations)",
    tables=[
        # LLM Vendor - no dependencies
        TableSpec(
            name="llm_vendor",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("name", "sa.String()", nullable=False),
                ColumnSpec("description", "sa.String()", nullable=True),
                ColumnSpec("color", "sa.String()", nullable=False, default="'#6B7280'"),
                ColumnSpec("icon_path", "sa.String()", nullable=False, default="''"),
                ColumnSpec("api_base", "sa.String()", nullable=True),
                ColumnSpec(
                    "auth_method", "sa.String()", nullable=False, default="'api-key'"
                ),
            ],
            indexes=[IndexSpec("ix_llm_vendor_name", ["name"], unique=True)],
        ),
        # Large Language Model - depends on llm_vendor
        TableSpec(
            name="large_language_model",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("model_id", "sa.String()", nullable=False),
                ColumnSpec("title", "sa.String()", nullable=False),
                ColumnSpec("description", "sa.String()", nullable=False, default="''"),
                ColumnSpec(
                    "context_window", "sa.Integer()", nullable=False, default="4096"
                ),
                ColumnSpec(
                    "training_data", "sa.String()", nullable=False, default="''"
                ),
                ColumnSpec(
                    "streamable", "sa.Boolean()", nullable=False, default="True"
                ),
                ColumnSpec("enabled", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec("color", "sa.String()", nullable=False, default="'#6B7280'"),
                ColumnSpec("icon_path", "sa.String()", nullable=False, default="''"),
                ColumnSpec("license", "sa.String()", nullable=True),
                ColumnSpec("source_url", "sa.String()", nullable=True),
                ColumnSpec("released_on", "sa.DateTime()", nullable=True),
                ColumnSpec("family", "sa.String()", nullable=True),
                ColumnSpec("llm_vendor_id", "sa.Integer()", nullable=True),
            ],
            indexes=[
                IndexSpec(
                    "ix_large_language_model_model_id", ["model_id"], unique=True
                ),
                IndexSpec("ix_large_language_model_llm_vendor_id", ["llm_vendor_id"]),
            ],
            foreign_keys=[ForeignKeySpec(["llm_vendor_id"], "llm_vendor", ["id"])],
        ),
        # LLM Deployment - depends on llm_vendor and large_language_model
        TableSpec(
            name="llm_deployment",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("llm_id", "sa.Integer()", nullable=False),
                ColumnSpec("llm_vendor_id", "sa.Integer()", nullable=False),
                ColumnSpec("speed", "sa.Integer()", nullable=False, default="50"),
                ColumnSpec(
                    "intelligence", "sa.Integer()", nullable=False, default="50"
                ),
                ColumnSpec("reasoning", "sa.Integer()", nullable=False, default="50"),
                ColumnSpec(
                    "output_max_tokens", "sa.Integer()", nullable=False, default="4096"
                ),
                ColumnSpec(
                    "function_calling", "sa.Boolean()", nullable=False, default="False"
                ),
                ColumnSpec(
                    "input_cache", "sa.Boolean()", nullable=False, default="False"
                ),
                ColumnSpec(
                    "structured_output", "sa.Boolean()", nullable=False, default="False"
                ),
            ],
            indexes=[
                IndexSpec("ix_llm_deployment_llm_id", ["llm_id"]),
                IndexSpec("ix_llm_deployment_llm_vendor_id", ["llm_vendor_id"]),
                IndexSpec(
                    "ix_llm_deployment_llm_vendor_unique",
                    ["llm_id", "llm_vendor_id"],
                    unique=True,
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["llm_id"], "large_language_model", ["id"]),
                ForeignKeySpec(["llm_vendor_id"], "llm_vendor", ["id"]),
            ],
        ),
        # LLM Modality - depends on large_language_model
        TableSpec(
            name="llm_modality",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("llm_id", "sa.Integer()", nullable=False),
                ColumnSpec("modality", "sa.String()", nullable=False),
                ColumnSpec("direction", "sa.String()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_llm_modality_llm_id", ["llm_id"]),
                IndexSpec(
                    "ix_llm_modality_unique",
                    ["llm_id", "modality", "direction"],
                    unique=True,
                ),
            ],
            foreign_keys=[ForeignKeySpec(["llm_id"], "large_language_model", ["id"])],
        ),
        # LLM Price - depends on llm_vendor and large_language_model
        TableSpec(
            name="llm_price",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("llm_vendor_id", "sa.Integer()", nullable=False),
                ColumnSpec("llm_id", "sa.Integer()", nullable=False),
                ColumnSpec("input_cost_per_token", "sa.Float()", nullable=False),
                ColumnSpec("output_cost_per_token", "sa.Float()", nullable=False),
                ColumnSpec("cache_input_cost_per_token", "sa.Float()", nullable=True),
                ColumnSpec("effective_date", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_llm_price_llm_vendor_id", ["llm_vendor_id"]),
                IndexSpec("ix_llm_price_llm_id", ["llm_id"]),
                IndexSpec("ix_llm_price_effective_date", ["effective_date"]),
            ],
            foreign_keys=[
                ForeignKeySpec(["llm_vendor_id"], "llm_vendor", ["id"]),
                ForeignKeySpec(["llm_id"], "large_language_model", ["id"]),
            ],
        ),
        # LLM Usage - uses model_id string (decoupled from catalog lifecycle)
        TableSpec(
            name="llm_usage",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("model_id", "sa.String()", nullable=False),
                ColumnSpec("user_id", "sa.String()", nullable=True),
                ColumnSpec("timestamp", "sa.DateTime()", nullable=False),
                ColumnSpec("input_tokens", "sa.Integer()", nullable=False),
                ColumnSpec("output_tokens", "sa.Integer()", nullable=False),
                ColumnSpec("total_cost", "sa.Float()", nullable=False),
                ColumnSpec("success", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec("error_message", "sa.String()", nullable=True),
                ColumnSpec("action", "sa.String()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_llm_usage_model_id", ["model_id"]),
                IndexSpec("ix_llm_usage_user_id", ["user_id"]),
                IndexSpec("ix_llm_usage_timestamp", ["timestamp"]),
                IndexSpec("ix_llm_usage_action", ["action"]),
            ],
            foreign_keys=[],
        ),
        # Conversation - no LLM dependencies
        TableSpec(
            name="conversation",
            columns=[
                ColumnSpec(
                    "id",
                    "sa.String()",
                    nullable=False,
                    primary_key=True,
                ),
                ColumnSpec("title", "sa.String()", nullable=True),
                ColumnSpec("user_id", "sa.String()", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
                ColumnSpec("meta_data", "sa.JSON()", nullable=False, default="{}"),
            ],
            indexes=[IndexSpec("ix_conversation_user_id", ["user_id"])],
        ),
        # Conversation Message - depends on conversation
        TableSpec(
            name="conversation_message",
            columns=[
                ColumnSpec(
                    "id",
                    "sa.String()",
                    nullable=False,
                    primary_key=True,
                ),
                ColumnSpec(
                    "conversation_id",
                    "sa.String()",
                    nullable=False,
                ),
                ColumnSpec("role", "sa.String()", nullable=False),
                ColumnSpec("content", "sa.String()", nullable=False),
                ColumnSpec("timestamp", "sa.DateTime()", nullable=False),
                ColumnSpec("meta_data", "sa.JSON()", nullable=False, default="{}"),
            ],
            indexes=[
                IndexSpec(
                    "ix_conversation_message_conversation_id", ["conversation_id"]
                ),
                IndexSpec("ix_conversation_message_timestamp", ["timestamp"]),
            ],
            foreign_keys=[ForeignKeySpec(["conversation_id"], "conversation", ["id"])],
        ),
    ],
)

AUTH_TOKENS_MIGRATION = ServiceMigrationSpec(
    service_name="auth_tokens",
    description="Auth token tables (password reset, email verification, refresh)",
    tables=[
        TableSpec(
            name="password_reset_token",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("user_id", "sa.Integer()", nullable=False),
                ColumnSpec("token", "sa.String()", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("used", "sa.Boolean()", nullable=False, default="'false'"),
            ],
            indexes=[
                IndexSpec("ix_password_reset_token_user_id", ["user_id"]),
                IndexSpec("ix_password_reset_token_token", ["token"], unique=True),
            ],
            foreign_keys=[
                ForeignKeySpec(["user_id"], "user", ["id"]),
            ],
        ),
        TableSpec(
            name="email_verification_token",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("user_id", "sa.Integer()", nullable=False),
                ColumnSpec("token", "sa.String()", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("used", "sa.Boolean()", nullable=False, default="'false'"),
            ],
            indexes=[
                IndexSpec("ix_email_verification_token_user_id", ["user_id"]),
                IndexSpec("ix_email_verification_token_token", ["token"], unique=True),
            ],
            foreign_keys=[
                ForeignKeySpec(["user_id"], "user", ["id"]),
            ],
        ),
        # Refresh token + session metadata. ``family_id`` groups all
        # rotations of one device's session; ``source``/``user_agent``/
        # ``ip``/``last_used_at`` power the active-sessions UI (#633).
        # SQLite-only deployments previously got this table via
        # ``SQLModel.metadata.create_all()``; Postgres deployments were
        # broken without this migration spec.
        TableSpec(
            name="refresh_token",
            columns=[
                ColumnSpec("token", "sa.String(64)", nullable=False, primary_key=True),
                ColumnSpec("user_id", "sa.Integer()", nullable=False),
                ColumnSpec("family_id", "sa.String(36)", nullable=False),
                ColumnSpec("expires_at", "sa.DateTime()", nullable=False),
                ColumnSpec("revoked_at", "sa.DateTime()", nullable=True),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("source", "sa.String(32)", nullable=True),
                ColumnSpec("user_agent", "sa.String(512)", nullable=True),
                ColumnSpec("ip", "sa.String(64)", nullable=True),
                ColumnSpec("last_used_at", "sa.DateTime()", nullable=True),
            ],
            indexes=[
                IndexSpec("ix_refresh_token_user_id", ["user_id"]),
                IndexSpec("ix_refresh_token_family_id", ["family_id"]),
                IndexSpec("ix_refresh_token_source", ["source"]),
            ],
            foreign_keys=[
                ForeignKeySpec(["user_id"], "user", ["id"]),
            ],
        ),
    ],
)

VOICE_MIGRATION = ServiceMigrationSpec(
    service_name="ai_voice",
    description="AI voice service table (TTS and STT usage tracking)",
    tables=[
        TableSpec(
            name="voice_usage",
            columns=[
                # === Core (all rows) ===
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec(
                    "usage_type", "sa.String()", nullable=False
                ),  # "tts" | "stt"
                ColumnSpec(
                    "provider", "sa.String()", nullable=False
                ),  # openai, groq, whisper_local
                ColumnSpec(
                    "model", "sa.String()", nullable=True
                ),  # tts-1, whisper-1, etc.
                ColumnSpec("user_id", "sa.String()", nullable=True),
                ColumnSpec("timestamp", "sa.DateTime(timezone=True)", nullable=False),
                ColumnSpec("latency_ms", "sa.Integer()", nullable=True),
                ColumnSpec("total_cost", "sa.Float()", nullable=False, default="0.0"),
                ColumnSpec("success", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec("error_message", "sa.String()", nullable=True),
                # === TTS-specific (null for STT) ===
                ColumnSpec("voice", "sa.String()", nullable=True),  # alloy, nova, etc.
                ColumnSpec(
                    "input_characters", "sa.Integer()", nullable=True
                ),  # text length
                ColumnSpec(
                    "output_duration_seconds", "sa.Float()", nullable=True
                ),  # audio length
                ColumnSpec(
                    "output_audio_bytes", "sa.Integer()", nullable=True
                ),  # audio size
                # === STT-specific (null for TTS) ===
                ColumnSpec(
                    "input_duration_seconds", "sa.Float()", nullable=True
                ),  # audio length
                ColumnSpec(
                    "input_audio_bytes", "sa.Integer()", nullable=True
                ),  # audio size
                ColumnSpec(
                    "output_characters", "sa.Integer()", nullable=True
                ),  # transcription length
                ColumnSpec(
                    "detected_language", "sa.String()", nullable=True
                ),  # en, es, etc.
            ],
            indexes=[
                IndexSpec("ix_voice_usage_usage_type", ["usage_type"]),
                IndexSpec("ix_voice_usage_provider", ["provider"]),
                IndexSpec("ix_voice_usage_user_id", ["user_id"]),
                IndexSpec("ix_voice_usage_timestamp", ["timestamp"]),
            ],
        ),
    ],
)


def _build_insights_migration(per_user: bool) -> ServiceMigrationSpec:
    """Build the insights migration spec.

    The insights service ships in two shapes, picked by ``insights_per_user``:

    * **Shared mode** (``per_user=False``): just the base tables — source,
      metric_type, metric, event, record. No tenancy. Single-tenant + env
      var driven. No goals (goals are per-user-scoped).
    * **Per-user mode** (``per_user=True``): adds the ``project`` table,
      stamps every metric/event row with a non-null ``project_id`` FK,
      adds ``created_by_user_id`` to events, and creates the user-scoped
      ``insight_goal`` table (with its own ``project_id`` FK).

    Folded into one migration per mode so a fresh DB gets a coherent
    schema in a single revision instead of three layered ones, and there's
    no destructive forward-only step needed for the per-user shape.
    """
    tables: list[TableSpec] = []

    if per_user:
        # `project` must come first — every insights table FKs to it.
        # Org-tenancy: every project belongs to an ``organization`` (auth-
        # shipped). ``owner_user_id`` stays as the implicit owner-membership
        # lookup; once v2 org-aware reads land, ownership transitions to
        # membership-based and ``owner_user_id`` can be dropped.
        tables.append(
            TableSpec(
                name="project",
                columns=[
                    ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                    ColumnSpec("slug", "sa.String(64)", nullable=False),
                    ColumnSpec("name", "sa.String(128)", nullable=False),
                    ColumnSpec("owner_user_id", "sa.Integer()", nullable=False),
                    ColumnSpec("organization_id", "sa.Integer()", nullable=False),
                    ColumnSpec("github_owner", "sa.String(64)", nullable=True),
                    ColumnSpec("github_repo", "sa.String(128)", nullable=True),
                    # github_token / plausible_api_key store ciphertext;
                    # encrypt/decrypt happens in ProjectService.
                    ColumnSpec("github_token", "sa.String(512)", nullable=True),
                    ColumnSpec("pypi_package", "sa.String(128)", nullable=True),
                    ColumnSpec("plausible_site", "sa.String(256)", nullable=True),
                    ColumnSpec("plausible_api_key", "sa.String(512)", nullable=True),
                    ColumnSpec("reddit_subreddits", "sa.String(256)", nullable=True),
                    ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                    ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
                ],
                indexes=[
                    IndexSpec("ix_project_owner_user_id", ["owner_user_id"]),
                    IndexSpec("ix_project_organization_id", ["organization_id"]),
                    IndexSpec("ix_project_slug", ["slug"]),
                    # Slug uniqueness follows the new ownership primitive:
                    # one slug per org, but two different orgs can each
                    # have a project named ``my-thing``.
                    IndexSpec(
                        "uq_project_organization_slug",
                        ["organization_id", "slug"],
                        unique=True,
                    ),
                ],
                foreign_keys=[
                    ForeignKeySpec(["owner_user_id"], "user", ["id"]),
                    ForeignKeySpec(["organization_id"], "organization", ["id"]),
                ],
            )
        )

    # InsightSource — lookup table for data sources.
    tables.append(
        TableSpec(
            name="insight_source",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("key", "sa.String(64)", nullable=False),
                ColumnSpec("display_name", "sa.String(128)", nullable=False),
                ColumnSpec("collection_interval_hours", "sa.Integer()", nullable=True),
                ColumnSpec(
                    "requires_auth", "sa.Boolean()", nullable=False, default="False"
                ),
                ColumnSpec("enabled", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec("last_collected_at", "sa.DateTime()", nullable=True),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_insight_source_key", ["key"], unique=True),
            ],
        )
    )

    # InsightMetricType — metric registry, FK to source.
    tables.append(
        TableSpec(
            name="insight_metric_type",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("source_id", "sa.Integer()", nullable=False),
                ColumnSpec("key", "sa.String(64)", nullable=False),
                ColumnSpec("display_name", "sa.String(128)", nullable=False),
                ColumnSpec("unit", "sa.String(32)", nullable=False),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_insight_metric_type_key", ["key"]),
                IndexSpec("ix_insight_metric_type_source_id", ["source_id"]),
                IndexSpec(
                    "uq_metric_type_source_key",
                    ["source_id", "key"],
                    unique=True,
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["source_id"], "insight_source", ["id"]),
            ],
        )
    )

    # InsightMetric — core time-series data. Per-user mode adds project_id.
    metric_columns = [
        ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
        ColumnSpec("date", "sa.DateTime()", nullable=False),
        ColumnSpec("metric_type_id", "sa.Integer()", nullable=False),
        ColumnSpec("value", "sa.Float()", nullable=False, default="0.0"),
        ColumnSpec("period", "sa.String(32)", nullable=False),
        ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
        ColumnSpec("created_at", "sa.DateTime()", nullable=False),
    ]
    metric_indexes = [
        IndexSpec("ix_insight_metric_type_date", ["metric_type_id", "date"]),
        IndexSpec("ix_insight_metric_date", ["date"]),
        IndexSpec("ix_insight_metric_metric_type_id", ["metric_type_id"]),
    ]
    metric_fks = [
        ForeignKeySpec(["metric_type_id"], "insight_metric_type", ["id"]),
    ]
    if per_user:
        metric_columns.append(ColumnSpec("project_id", "sa.Integer()", nullable=False))
        metric_indexes.extend(
            [
                IndexSpec("ix_insight_metric_project_id", ["project_id"]),
                IndexSpec("ix_insight_metric_project_date", ["project_id", "date"]),
            ]
        )
        # ON DELETE CASCADE so SQLAlchemy ``passive_deletes=True`` on
        # ``Project.metrics`` resolves end-to-end at the DB level.
        metric_fks.append(
            ForeignKeySpec(["project_id"], "project", ["id"], ondelete="CASCADE")
        )
    tables.append(
        TableSpec(
            name="insight_metric",
            columns=metric_columns,
            indexes=metric_indexes,
            foreign_keys=metric_fks,
        )
    )

    # InsightRecord — all-time records per metric type. Not per-project: a
    # record is the global high-water mark for a metric and lives in the
    # shared lookup space alongside metric_type.
    tables.append(
        TableSpec(
            name="insight_record",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("metric_type_id", "sa.Integer()", nullable=False),
                ColumnSpec("value", "sa.Float()", nullable=False, default="0.0"),
                ColumnSpec("date_achieved", "sa.DateTime()", nullable=False),
                ColumnSpec("previous_value", "sa.Float()", nullable=True),
                ColumnSpec("previous_date", "sa.DateTime()", nullable=True),
                ColumnSpec("context", "sa.String(512)", nullable=True),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec(
                    "ix_insight_record_metric_type_id",
                    ["metric_type_id"],
                    unique=True,
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["metric_type_id"], "insight_metric_type", ["id"]),
            ],
        )
    )

    # InsightEvent — contextual markers. Per-user mode adds project_id +
    # created_by_user_id; shared mode keeps just the base columns.
    event_columns = [
        ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
        ColumnSpec("date", "sa.DateTime()", nullable=False),
        ColumnSpec("event_type", "sa.String(64)", nullable=False),
        ColumnSpec("description", "sa.String(1024)", nullable=False),
        ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
        # `origin` distinguishes collector output from user-created
        # annotations so the API/UI only exposes user rows for editing.
        ColumnSpec("origin", "sa.String(16)", nullable=False, default="'collector'"),
        ColumnSpec("created_at", "sa.DateTime()", nullable=False),
    ]
    event_indexes = [
        IndexSpec("ix_insight_event_date", ["date"]),
        IndexSpec("ix_insight_event_type_date", ["event_type", "date"]),
        IndexSpec("ix_insight_event_origin", ["origin"]),
        IndexSpec("ix_insight_event_origin_date", ["origin", "date"]),
    ]
    event_fks: list[ForeignKeySpec] = []
    if per_user:
        event_columns.append(ColumnSpec("project_id", "sa.Integer()", nullable=False))
        event_columns.append(
            ColumnSpec("created_by_user_id", "sa.Integer()", nullable=True)
        )
        event_indexes.extend(
            [
                IndexSpec("ix_insight_event_project_id", ["project_id"]),
                IndexSpec("ix_insight_event_project_date", ["project_id", "date"]),
                IndexSpec(
                    "ix_insight_event_created_by_user_id", ["created_by_user_id"]
                ),
            ]
        )
        event_fks.extend(
            [
                # CASCADE on the project FK so deleting a project also
                # drops its events; the user FK stays a plain RESTRICT
                # so deleting a user with authored events errors loudly
                # instead of silently nuking history.
                ForeignKeySpec(["project_id"], "project", ["id"], ondelete="CASCADE"),
                ForeignKeySpec(["created_by_user_id"], "user", ["id"]),
            ]
        )
    tables.append(
        TableSpec(
            name="insight_event",
            columns=event_columns,
            indexes=event_indexes,
            foreign_keys=event_fks,
            check_constraints=[
                CheckConstraintSpec(
                    name="ck_insight_event_origin",
                    sqltext="origin IN ('collector', 'user')",
                ),
            ],
        )
    )

    if per_user:
        # InsightGoal — per-user goals scoped to a project. ``user_id`` is
        # the goal owner (today: project owner; v2 may differ for shared
        # projects). ``project_id`` is the FK that every read filters on.
        tables.append(
            TableSpec(
                name="insight_goal",
                columns=[
                    ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                    ColumnSpec("user_id", "sa.Integer()", nullable=False),
                    ColumnSpec("project_id", "sa.Integer()", nullable=False),
                    ColumnSpec("metric_key", "sa.String(64)", nullable=False),
                    ColumnSpec("kind", "sa.String(16)", nullable=False),
                    ColumnSpec("target_value", "sa.Float()", nullable=False),
                    ColumnSpec("window_days", "sa.Integer()", nullable=True),
                    ColumnSpec("target_date", "sa.Date()", nullable=True),
                    ColumnSpec(
                        "status",
                        "sa.String(16)",
                        nullable=False,
                        default="'active'",
                    ),
                    ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                    ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
                ],
                indexes=[
                    IndexSpec("ix_insight_goal_user_id", ["user_id"]),
                    IndexSpec("ix_insight_goal_project_id", ["project_id"]),
                    IndexSpec("ix_insight_goal_metric_key", ["metric_key"]),
                    IndexSpec("ix_insight_goal_user_status", ["user_id", "status"]),
                    IndexSpec(
                        "ix_insight_goal_project_metric",
                        ["project_id", "metric_key"],
                    ),
                ],
                foreign_keys=[
                    # User FK stays plain RESTRICT (deleting a user with
                    # goals errors loudly). Project FK cascades so
                    # deleting a project drops its goals along with the
                    # rest of its row tree.
                    ForeignKeySpec(["user_id"], "user", ["id"]),
                    ForeignKeySpec(
                        ["project_id"], "project", ["id"], ondelete="CASCADE"
                    ),
                ],
                check_constraints=[
                    CheckConstraintSpec(
                        name="ck_insight_goal_kind",
                        sqltext="kind IN ('absolute', 'delta', 'rate')",
                    ),
                    CheckConstraintSpec(
                        name="ck_insight_goal_status",
                        sqltext="status IN ('active', 'achieved', 'abandoned')",
                    ),
                    CheckConstraintSpec(
                        name="ck_insight_goal_metric_key",
                        sqltext=(
                            "metric_key IN ("
                            "'github.stars', 'github.clones', 'github.unique_cloners', "
                            "'github.views', 'github.unique_visitors', 'github.forks', "
                            "'github.releases', 'pypi.downloads', 'docs.visitors', "
                            "'docs.pageviews'"
                            ")"
                        ),
                    ),
                ],
            )
        )

    description = (
        "Per-user insights tables (project, source/metric_type/metric/event/record, goal)"
        if per_user
        else "Insights service tables (sources, metrics, records, events)"
    )
    return ServiceMigrationSpec(
        service_name="insights",
        description=description,
        tables=tables,
    )


# Default registry-facing variant is the shared-mode shape. Per-user mode
# rebuilds the spec at generation time via _build_insights_migration(True).
INSIGHTS_MIGRATION = _build_insights_migration(per_user=False)


PAYMENT_MIGRATION = ServiceMigrationSpec(
    service_name="payment",
    description="Payment service tables (providers, customers, transactions, subscriptions, disputes)",
    tables=[
        TableSpec(
            name="payment_provider",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("key", "sa.String(32)", nullable=False),
                ColumnSpec("display_name", "sa.String(64)", nullable=False),
                ColumnSpec("enabled", "sa.Boolean()", nullable=False, default="True"),
                ColumnSpec(
                    "is_test_mode", "sa.Boolean()", nullable=False, default="True"
                ),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_payment_provider_key", ["key"], unique=True),
            ],
        ),
        TableSpec(
            name="payment_customer",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                # user_id is nullable: anonymous checkouts (guest carts,
                # donations, pre-signup SaaS trials) have no app user yet.
                # An FK to `user.id` is added by the `payment_auth_link`
                # migration when both services are included.
                ColumnSpec("user_id", "sa.Integer()", nullable=True),
                ColumnSpec("provider_id", "sa.Integer()", nullable=False),
                ColumnSpec("provider_customer_id", "sa.String(128)", nullable=False),
                ColumnSpec("email", "sa.String(255)", nullable=True),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_payment_customer_user_id", ["user_id"]),
                IndexSpec("ix_payment_customer_provider_id", ["provider_id"]),
                IndexSpec(
                    "ix_payment_customer_provider_customer_id",
                    ["provider_customer_id"],
                ),
                IndexSpec(
                    "uq_provider_customer",
                    ["provider_id", "provider_customer_id"],
                    unique=True,
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["provider_id"], "payment_provider", ["id"]),
            ],
        ),
        TableSpec(
            name="payment_transaction",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("provider_id", "sa.Integer()", nullable=False),
                ColumnSpec("customer_id", "sa.Integer()", nullable=True),
                ColumnSpec("provider_transaction_id", "sa.String(128)", nullable=False),
                ColumnSpec("type", "sa.String(32)", nullable=False),
                ColumnSpec("status", "sa.String(32)", nullable=False),
                ColumnSpec("amount", "sa.Integer()", nullable=False, default="0"),
                ColumnSpec("currency", "sa.String(3)", nullable=False, default="'usd'"),
                ColumnSpec("description", "sa.String(512)", nullable=True),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec(
                    "ix_payment_transaction_provider_transaction_id",
                    ["provider_transaction_id"],
                    unique=True,
                ),
                IndexSpec("ix_payment_transaction_provider_id", ["provider_id"]),
                IndexSpec("ix_payment_transaction_customer_id", ["customer_id"]),
                IndexSpec("ix_payment_transaction_status", ["status"]),
                IndexSpec("ix_payment_txn_status_created", ["status", "created_at"]),
                IndexSpec(
                    "ix_payment_txn_provider_created",
                    ["provider_id", "created_at"],
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["provider_id"], "payment_provider", ["id"]),
                ForeignKeySpec(["customer_id"], "payment_customer", ["id"]),
            ],
        ),
        TableSpec(
            name="payment_subscription",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("customer_id", "sa.Integer()", nullable=False),
                ColumnSpec(
                    "provider_subscription_id", "sa.String(128)", nullable=False
                ),
                ColumnSpec("plan_name", "sa.String(64)", nullable=False),
                ColumnSpec("status", "sa.String(32)", nullable=False),
                ColumnSpec("current_period_start", "sa.DateTime()", nullable=False),
                ColumnSpec("current_period_end", "sa.DateTime()", nullable=False),
                ColumnSpec(
                    "cancel_at_period_end",
                    "sa.Boolean()",
                    nullable=False,
                    default="False",
                ),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec(
                    "ix_payment_subscription_provider_subscription_id",
                    ["provider_subscription_id"],
                    unique=True,
                ),
                IndexSpec("ix_payment_subscription_customer_id", ["customer_id"]),
                IndexSpec("ix_payment_subscription_status", ["status"]),
            ],
            foreign_keys=[
                ForeignKeySpec(["customer_id"], "payment_customer", ["id"]),
            ],
        ),
        TableSpec(
            name="payment_dispute",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("transaction_id", "sa.Integer()", nullable=False),
                ColumnSpec("provider_dispute_id", "sa.String(128)", nullable=False),
                ColumnSpec("status", "sa.String(32)", nullable=False),
                ColumnSpec("reason", "sa.String(64)", nullable=True),
                ColumnSpec("amount", "sa.Integer()", nullable=False, default="0"),
                ColumnSpec("currency", "sa.String(3)", nullable=False, default="'usd'"),
                ColumnSpec("evidence_due_by", "sa.DateTime()", nullable=True),
                ColumnSpec("event_type", "sa.String(64)", nullable=True),
                ColumnSpec("metadata", "sa.JSON()", nullable=False, default="{}"),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec(
                    "ix_payment_dispute_provider_dispute_id",
                    ["provider_dispute_id"],
                    unique=True,
                ),
                IndexSpec("ix_payment_dispute_transaction_id", ["transaction_id"]),
                IndexSpec("ix_payment_dispute_status", ["status"]),
                IndexSpec(
                    "ix_payment_dispute_status_created",
                    ["status", "created_at"],
                ),
                IndexSpec(
                    "ix_payment_dispute_txn_created",
                    ["transaction_id", "created_at"],
                ),
            ],
            foreign_keys=[
                ForeignKeySpec(["transaction_id"], "payment_transaction", ["id"]),
            ],
        ),
    ],
)

PAYMENT_AUTH_LINK_MIGRATION = ServiceMigrationSpec(
    service_name="payment_auth_link",
    description="Link payment_customer.user_id to user.id (auth + payment)",
    tables=[],
    alter_tables=[
        AlterTableSpec(
            name="payment_customer",
            add_foreign_keys=[
                ForeignKeySpec(["user_id"], "user", ["id"]),
            ],
        ),
    ],
)


BLOG_MIGRATION = ServiceMigrationSpec(
    service_name="blog",
    description="Blog service tables (posts, tags, post/tag links)",
    tables=[
        TableSpec(
            name="blog_post",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("title", "sa.String(200)", nullable=False),
                ColumnSpec("slug", "sa.String(220)", nullable=False),
                ColumnSpec("excerpt", "sa.String(500)", nullable=True),
                ColumnSpec("content", "sa.Text()", nullable=False),
                ColumnSpec(
                    "status", "sa.String(16)", nullable=False, default="'draft'"
                ),
                ColumnSpec("author_id", "sa.Integer()", nullable=True),
                ColumnSpec("author_name", "sa.String(200)", nullable=True),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=False),
                ColumnSpec("published_at", "sa.DateTime()", nullable=True),
                ColumnSpec("seo_title", "sa.String(200)", nullable=True),
                ColumnSpec("seo_description", "sa.String(320)", nullable=True),
                ColumnSpec("hero_image_url", "sa.String(1024)", nullable=True),
            ],
            indexes=[
                IndexSpec("ix_blog_post_slug", ["slug"], unique=True),
                IndexSpec("ix_blog_post_status", ["status"]),
                IndexSpec("ix_blog_post_author_id", ["author_id"]),
                IndexSpec("ix_blog_post_created_at", ["created_at"]),
                IndexSpec("ix_blog_post_published_at", ["published_at"]),
            ],
            check_constraints=[
                CheckConstraintSpec(
                    name="ck_blog_post_status",
                    sqltext="status IN ('draft', 'published', 'archived')",
                ),
            ],
        ),
        TableSpec(
            name="blog_tag",
            columns=[
                ColumnSpec("id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("name", "sa.String(80)", nullable=False),
                ColumnSpec("slug", "sa.String(100)", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_blog_tag_name", ["name"], unique=True),
                IndexSpec("ix_blog_tag_slug", ["slug"], unique=True),
            ],
        ),
        TableSpec(
            name="blog_post_tag",
            columns=[
                ColumnSpec("post_id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("tag_id", "sa.Integer()", nullable=False, primary_key=True),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
            ],
            indexes=[
                IndexSpec("ix_blog_post_tag_post_id", ["post_id"]),
                IndexSpec("ix_blog_post_tag_tag_id", ["tag_id"]),
            ],
            foreign_keys=[
                ForeignKeySpec(["post_id"], "blog_post", ["id"], ondelete="CASCADE"),
                ForeignKeySpec(["tag_id"], "blog_tag", ["id"], ondelete="CASCADE"),
            ],
        ),
    ],
)

# Registry of all service migrations.
#
# R4-A: derived lazily from each ``PluginSpec.migrations`` list (see
# ``aegis/core/services.py`` for the in-tree declarations and
# ``aegis/core/migration_spec.py`` for the plugin-author-facing facade).
# Pre-R4 this was a literal ``dict[str, ServiceMigrationSpec]`` here;
# moving it onto the specs lets third-party plugins ship their own
# migrations without forking core, while preserving the same
# ``MIGRATION_SPECS["auth"]`` lookup shape for existing callers
# (``copier_manager.py``, ``add_service.py``, the test suite).
#
# Lazy because ``services.py`` imports the named ``*_MIGRATION``
# constants from this module — eager construction here would create a
# circular import at module load time. ``__getattr__`` defers the
# ``services`` import until first access of ``MIGRATION_SPECS``, by
# which point the services registry is fully built.

_MIGRATION_SPECS_CACHE: dict[str, ServiceMigrationSpec] | None = None


def _get_migration_specs() -> dict[str, ServiceMigrationSpec]:
    """Return the (lazily built) migration registry.

    Plugins discovered via entry points (Phase B of the plugin system)
    will need to invalidate ``_MIGRATION_SPECS_CACHE`` after registering
    new specs; for R4-A the in-tree registry is static, so the dict is
    built once and reused.
    """
    global _MIGRATION_SPECS_CACHE
    if _MIGRATION_SPECS_CACHE is None:
        from .migration_spec import collect_migrations
        from .services import SERVICES

        _MIGRATION_SPECS_CACHE = collect_migrations(SERVICES.values())
    return _MIGRATION_SPECS_CACHE


def __getattr__(name: str) -> Any:
    """Module-level lazy access for ``MIGRATION_SPECS``.

    Used when callers do ``from migration_generator import MIGRATION_SPECS``;
    code inside this module references the cache via ``_get_migration_specs()``
    instead, since module-level ``__getattr__`` does not fire for internal
    name lookups.
    """
    if name == "MIGRATION_SPECS":
        return _get_migration_specs()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ============================================================================
# Migration File Template
# ============================================================================

MIGRATION_TEMPLATE = '''"""{{ description }}

Revision ID: {{ revision }}
Revises: {{ down_revision }}
Create Date: {{ create_date }}

"""
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision = '{{ revision }}'
down_revision = {{ down_revision_repr }}
branch_labels = None
depends_on = None


def upgrade() -> None:
    """{{ upgrade_description }}"""
{% for table in tables %}
    # Create {{ table.name }} table
    op.create_table(
        '{{ table.name }}',
{% for column in table.columns %}
{% set pk_attr = ", primary_key=True" if column.primary_key else "" %}
{% set default_attr = ", default=" ~ column.default if column.default else "" %}
        sa.Column('{{ column.name }}', {{ column.type }}, nullable={{ column.nullable }}{{ pk_attr }}{{ default_attr }}),
{% endfor %}
{% if table.primary_keys %}
        sa.PrimaryKeyConstraint({% for pk in table.primary_keys %}'{{ pk }}'{% if not loop.last %}, {% endif %}{% endfor %}){% if table.foreign_keys or table.check_constraints %},{% endif %}

{% endif %}
{% for fk in table.foreign_keys %}
        sa.ForeignKeyConstraint({{ fk.columns }}, ['{{ fk.ref_table }}.{{ fk.ref_columns[0] }}']{% if fk.ondelete %}, ondelete='{{ fk.ondelete }}'{% endif %}){% if not loop.last or table.check_constraints %},{% endif %}

{% endfor %}
{% for chk in table.check_constraints %}
        sa.CheckConstraint("{{ chk.sqltext }}", name='{{ chk.name }}'){% if not loop.last %},{% endif %}

{% endfor %}
    )
{% for index in table.indexes %}
    op.create_index(op.f('{{ index.name }}'), '{{ table.name }}', {{ index.columns }}{% if index.unique %}, unique=True{% endif %})
{% endfor %}

{% endfor %}
{% for alter in alter_tables %}
    # Alter {{ alter.name }} table — batch_alter_table is required for
    # SQLite, which doesn't support ALTER for FK constraints. Postgres
    # treats it as plain ALTER, so this is portable across both backends.
    # Drops run before adds so names can be reused (e.g. swap an index
    # from one column set to another with the same name).
    with op.batch_alter_table('{{ alter.name }}') as batch_op:
{% for index_name in alter.drop_indexes %}
        batch_op.drop_index('{{ index_name }}')
{% endfor %}
{% for column_name in alter.drop_columns %}
        batch_op.drop_column('{{ column_name }}')
{% endfor %}
{% for column in alter.add_columns %}
        batch_op.add_column(sa.Column('{{ column.name }}', {{ column.type }}, nullable={{ column.nullable }}{% if column.server_default %}, server_default={{ column.server_default }}{% endif %}))
{% endfor %}
{% for fk in alter.add_foreign_keys %}
        batch_op.create_foreign_key('fk_{{ alter.name }}_{{ fk.columns[0] }}_{{ fk.ref_table }}', '{{ fk.ref_table }}', {{ fk.columns }}, {{ fk.ref_columns }}{% if fk.ondelete %}, ondelete='{{ fk.ondelete }}'{% endif %})
{% endfor %}
{% for index in alter.add_indexes %}
        batch_op.create_index('{{ index.name }}', {{ index.columns }}{% if index.unique %}, unique=True{% endif %})
{% endfor %}

{% endfor %}

def downgrade() -> None:
    """Reverse {{ service_name }} migration."""
{% if forward_only %}
    raise NotImplementedError(
        "Migration {{ service_name }} is forward-only — it drops columns "
        "or merges schemas in non-recoverable ways. Restore from backup "
        "to roll back."
    )
{% else %}
{% for alter in alter_tables|reverse %}
    with op.batch_alter_table('{{ alter.name }}') as batch_op:
{% for index in alter.add_indexes|reverse %}
        batch_op.drop_index('{{ index.name }}')
{% endfor %}
{% for fk in alter.add_foreign_keys|reverse %}
        batch_op.drop_constraint('fk_{{ alter.name }}_{{ fk.columns[0] }}_{{ fk.ref_table }}', type_='foreignkey')
{% endfor %}
{% for column in alter.add_columns|reverse %}
        batch_op.drop_column('{{ column.name }}')
{% endfor %}
{% endfor %}
{% for table in tables|reverse %}
{% for index in table.indexes %}
    op.drop_index(op.f('{{ index.name }}'), table_name='{{ table.name }}')
{% endfor %}
    op.drop_table('{{ table.name }}')
{% endfor %}
{% endif %}
'''


# ============================================================================
# Core Functions
# ============================================================================


def get_versions_dir(project_path: Path) -> Path:
    """Get the alembic versions directory for a project."""
    return project_path / "alembic" / "versions"


def get_existing_migrations(project_path: Path) -> list[str]:
    """
    Get list of existing migration revision IDs in a project.

    Returns revision IDs sorted by filename (which determines order).
    """
    versions_dir = get_versions_dir(project_path)
    if not versions_dir.exists():
        return []

    migrations = []
    for f in sorted(versions_dir.glob("*.py")):
        if f.name.startswith("__"):
            continue
        # Extract revision from filename (e.g., "001_auth.py" -> "001")
        parts = f.stem.split("_")
        if parts and parts[0].isdigit():
            migrations.append(parts[0])

    return migrations


def get_next_revision_id(project_path: Path) -> str:
    """
    Get the next revision ID for a new migration.

    Uses simple numeric IDs: 001, 002, 003, etc.
    """
    existing = get_existing_migrations(project_path)
    if not existing:
        return "001"

    # Find highest existing revision number
    max_rev = max(int(rev) for rev in existing)
    return f"{max_rev + 1:03d}"


def get_previous_revision(project_path: Path) -> str | None:
    """Get the most recent revision ID, or None if no migrations exist."""
    existing = get_existing_migrations(project_path)
    if not existing:
        return None
    return existing[-1]


def service_has_migration(project_path: Path, service_name: str) -> bool:
    """
    Check if a service already has a migration in the project.

    Looks for migration files containing the service name.
    """
    versions_dir = get_versions_dir(project_path)
    if not versions_dir.exists():
        return False

    # Look for files with service name in filename
    for _f in versions_dir.glob(f"*_{service_name}.py"):
        return True

    return False


def _render_migration(
    spec: ServiceMigrationSpec,
    revision: str,
    down_revision: str | None,
) -> str:
    """Render a migration file from a service spec."""
    template = Template(MIGRATION_TEMPLATE)

    # Prepare table data for template
    tables_data = []
    for table in spec.tables:
        # Find primary key columns
        primary_keys = [col.name for col in table.columns if col.primary_key]

        tables_data.append(
            {
                "name": table.name,
                "columns": [
                    {
                        "name": col.name,
                        "type": col.type,
                        "nullable": col.nullable,
                        "primary_key": col.primary_key,
                        "default": col.default,
                    }
                    for col in table.columns
                ],
                "indexes": [
                    {
                        "name": idx.name,
                        "columns": idx.columns,
                        "unique": idx.unique,
                    }
                    for idx in table.indexes
                ],
                "foreign_keys": [
                    {
                        "columns": fk.columns,
                        "ref_table": fk.ref_table,
                        "ref_columns": fk.ref_columns,
                        "ondelete": fk.ondelete,
                    }
                    for fk in table.foreign_keys
                ],
                "check_constraints": [
                    {"name": chk.name, "sqltext": chk.sqltext}
                    for chk in table.check_constraints
                ],
                "primary_keys": primary_keys,
            }
        )

    # Prepare alter table data for template
    alter_tables_data = []
    for alter in spec.alter_tables:
        cols = []
        for col in alter.add_columns:
            # For add_column, server_default needs sa.text() wrapper
            server_default = None
            if col.default is not None:
                server_default = f'sa.text("{col.default}")'
            cols.append(
                {
                    "name": col.name,
                    "type": col.type,
                    "nullable": col.nullable,
                    "server_default": server_default,
                }
            )
        fks = [
            {
                "columns": fk.columns,
                "ref_table": fk.ref_table,
                "ref_columns": fk.ref_columns,
                "ondelete": fk.ondelete,
            }
            for fk in alter.add_foreign_keys
        ]
        add_idxs = [
            {
                "name": idx.name,
                "columns": idx.columns,
                "unique": idx.unique,
            }
            for idx in alter.add_indexes
        ]
        alter_tables_data.append(
            {
                "name": alter.name,
                "add_columns": cols,
                "add_foreign_keys": fks,
                "add_indexes": add_idxs,
                "drop_columns": list(alter.drop_columns),
                "drop_indexes": list(alter.drop_indexes),
            }
        )

    # Build upgrade description
    if spec.tables and spec.alter_tables:
        upgrade_description = f"Create and alter {spec.service_name} service tables."
    elif spec.alter_tables:
        upgrade_description = f"Add {spec.service_name} columns."
    else:
        upgrade_description = f"Create {spec.service_name} service tables."

    return template.render(
        description=spec.description,
        service_name=spec.service_name,
        upgrade_description=upgrade_description,
        revision=revision,
        down_revision=down_revision,
        down_revision_repr=f"'{down_revision}'" if down_revision else "None",
        create_date=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
        tables=tables_data,
        alter_tables=alter_tables_data,
        forward_only=spec.forward_only,
    )


def _resolve_spec(
    service_name: str,
    context: dict[str, Any] | None,
) -> ServiceMigrationSpec | None:
    """Look up a migration spec, applying any context-driven overrides.

    The ``insights`` spec ships in two shapes — shared mode (default) and
    per-user mode (``insights_per_user=true``). Both render to a single
    ``00X_insights.py`` migration file; only the shape changes. Other
    services pass through to the static spec unchanged.
    """
    migration_specs = _get_migration_specs()
    if service_name not in migration_specs:
        return None

    if service_name == "insights" and context is not None:
        flag = context.get("insights_per_user")
        per_user = flag == "yes" or flag is True
        if per_user:
            return _build_insights_migration(per_user=True)

    return migration_specs[service_name]


def generate_migration(
    project_path: Path,
    service_name: str,
    context: dict[str, Any] | None = None,
) -> Path | None:
    """
    Generate a migration file for a service.

    Args:
        project_path: Path to the project directory
        service_name: Name of the service (e.g., "auth", "ai")
        context: Optional generation context (copier flags). Used to pick
            between spec variants — e.g. ``insights_per_user`` toggles the
            insights spec between shared and per-user shape.

    Returns:
        Path to the generated migration file, or None if service not found
    """
    spec = _resolve_spec(service_name, context)
    if spec is None:
        return None

    versions_dir = get_versions_dir(project_path)

    # Ensure versions directory exists
    versions_dir.mkdir(parents=True, exist_ok=True)

    # Get revision info
    revision = get_next_revision_id(project_path)
    down_revision = get_previous_revision(project_path)

    # Render migration content
    content = _render_migration(spec, revision, down_revision)

    # Write migration file
    filename = f"{revision}_{service_name}.py"
    migration_path = versions_dir / filename

    migration_path.write_text(content)

    return migration_path


def generate_migrations_for_services(
    project_path: Path,
    services: list[str],
    context: dict[str, Any] | None = None,
) -> list[Path]:
    """
    Generate migrations for multiple services in order.

    Args:
        project_path: Path to the project directory
        services: List of service names in desired order
        context: Optional generation context forwarded to ``generate_migration``
            so spec variants (e.g. insights per-user) pick the right shape.

    Returns:
        List of paths to generated migration files
    """
    generated = []
    migration_specs = _get_migration_specs()

    for service_name in services:
        if service_name not in migration_specs:
            continue

        # Skip if migration already exists
        if service_has_migration(project_path, service_name):
            continue

        migration_path = generate_migration(project_path, service_name, context)
        if migration_path:
            generated.append(migration_path)

    return generated


def get_services_needing_migrations(context: dict[str, Any]) -> list[str]:
    """
    Determine which services need migrations based on context.

    Args:
        context: Dictionary with service flags (e.g., from cookiecutter/copier)

    Returns:
        List of service names that need migrations
    """
    services = []

    # Auth service (base user table)
    include_auth = context.get("include_auth")
    if include_auth == "yes" or include_auth is True:
        services.append("auth")

    # Auth token tables (password reset, email verification) - always with auth
    if include_auth == "yes" or include_auth is True:
        services.append("auth_tokens")

    # Auth RBAC columns (rbac or org level)
    include_auth_rbac = context.get("include_auth_rbac")
    auth_level = context.get("auth_level")
    rbac_enabled = (
        include_auth_rbac == "yes"
        or include_auth_rbac is True
        or (isinstance(auth_level, str) and auth_level.lower() in ("rbac", "org"))
    )
    if (include_auth == "yes" or include_auth is True) and rbac_enabled:
        services.append("auth_rbac")

    # Auth org tables (only with org-level auth)
    include_auth_org = context.get("include_auth_org")
    org_enabled = (
        include_auth_org == "yes"
        or include_auth_org is True
        or (isinstance(auth_level, str) and auth_level.lower() == "org")
    )
    if (include_auth == "yes" or include_auth is True) and org_enabled:
        services.append("auth_org")

    # AI service (only with persistence backend)
    include_ai = context.get("include_ai")
    ai_backend = context.get("ai_backend", "memory")
    if (include_ai == "yes" or include_ai is True) and ai_backend != "memory":
        services.append("ai")

    # AI Voice service (only if AI with persistence and voice enabled)
    ai_voice = context.get("ai_voice")
    if (
        (include_ai == "yes" or include_ai is True)
        and ai_backend != "memory"
        and (ai_voice == "yes" or ai_voice is True)
    ):
        services.append("ai_voice")

    # Insights service (always needs database)
    include_insights = context.get("include_insights")
    include_insights_on = include_insights == "yes" or include_insights is True
    if include_insights_on:
        services.append("insights")

    # Payment service (always needs database)
    include_payment = context.get("include_payment")
    include_payment_on = include_payment == "yes" or include_payment is True
    if include_payment_on:
        services.append("payment")

    # Payment + Auth: add FK from payment_customer.user_id -> user.id.
    # Only meaningful when BOTH services are included; runs after both
    # base migrations so the `user` table exists when the FK is created.
    include_auth_on = include_auth == "yes" or include_auth is True
    if include_payment_on and include_auth_on:
        services.append("payment_auth_link")

    # Blog service (always needs database)
    include_blog = context.get("include_blog")
    include_blog_on = include_blog == "yes" or include_blog is True
    if include_blog_on:
        services.append("blog")

    # Per-user vs shared insights is one folded migration — generation
    # picks the shape from the context flag (see ``generate_migration``).

    return services


# ============================================================================
# Alembic Bootstrap
# ============================================================================

# Files to create when bootstrapping alembic infrastructure
ALEMBIC_TEMPLATE_FILES = [
    "alembic/alembic.ini",
    "alembic/env.py",
    "alembic/script.py.mako",
]


def bootstrap_alembic(
    project_path: Path, jinja_env: Environment, context: dict[str, Any]
) -> list[str]:
    """
    Bootstrap alembic infrastructure by rendering template files.

    This is called when adding a service that needs migrations to a project
    that doesn't yet have alembic set up.

    Args:
        project_path: Path to the project directory
        jinja_env: Jinja2 environment configured for the template directory
        context: Template context (copier answers)

    Returns:
        List of created file paths (relative to project)
    """
    created_files: list[str] = []
    project_slug_placeholder = "{{ project_slug }}"

    for file_path in ALEMBIC_TEMPLATE_FILES:
        # Try with .jinja extension first
        template_name = f"{project_slug_placeholder}/{file_path}.jinja"
        try:
            template = jinja_env.get_template(template_name)
            content = template.render(context)

            output_path = project_path / file_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            created_files.append(file_path)
            continue
        except TemplateNotFound:
            # Expected: try loading without .jinja extension (for files like script.py.mako)
            pass

        # Try without .jinja extension (for script.py.mako which is not templated)
        template_name_no_ext = f"{project_slug_placeholder}/{file_path}"
        try:
            template = jinja_env.get_template(template_name_no_ext)
            content = template.render(context)

            output_path = project_path / file_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            created_files.append(file_path)
        except TemplateNotFound:
            # Template not found with either extension - file may be optional or not templated
            pass

    # Create versions directory with .gitkeep
    versions_dir = get_versions_dir(project_path)
    versions_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = versions_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

    return created_files
