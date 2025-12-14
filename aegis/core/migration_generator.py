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
    """Specification for a foreign key constraint."""

    columns: list[str]
    ref_table: str
    ref_columns: list[str]


@dataclass
class TableSpec:
    """Specification for a database table."""

    name: str
    columns: list[ColumnSpec]
    indexes: list[IndexSpec] = field(default_factory=list)
    foreign_keys: list[ForeignKeySpec] = field(default_factory=list)


@dataclass
class ServiceMigrationSpec:
    """Migration specification for a service."""

    service_name: str
    tables: list[TableSpec]
    description: str


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
                ColumnSpec("hashed_password", "sa.String()", nullable=False),
                ColumnSpec("created_at", "sa.DateTime()", nullable=False),
                ColumnSpec("updated_at", "sa.DateTime()", nullable=True),
            ],
            indexes=[IndexSpec("ix_user_email", ["email"], unique=True)],
        ),
    ],
)

AI_MIGRATION = ServiceMigrationSpec(
    service_name="ai",
    description="AI conversation tables",
    tables=[
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

# Registry of all service migrations
MIGRATION_SPECS: dict[str, ServiceMigrationSpec] = {
    "auth": AUTH_MIGRATION,
    "ai": AI_MIGRATION,
}

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
    """Create {{ service_name }} service tables."""
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
        sa.PrimaryKeyConstraint({% for pk in table.primary_keys %}'{{ pk }}'{% if not loop.last %}, {% endif %}{% endfor %}){% if table.foreign_keys %},{% endif %}

{% endif %}
{% for fk in table.foreign_keys %}
        sa.ForeignKeyConstraint({{ fk.columns }}, ['{{ fk.ref_table }}.{{ fk.ref_columns[0] }}']){% if not loop.last %},{% endif %}

{% endfor %}
    )
{% for index in table.indexes %}
    op.create_index(op.f('{{ index.name }}'), '{{ table.name }}', {{ index.columns }}{% if index.unique %}, unique=True{% endif %})
{% endfor %}

{% endfor %}

def downgrade() -> None:
    """Drop {{ service_name }} service tables."""
{% for table in tables|reverse %}
{% for index in table.indexes %}
    op.drop_index(op.f('{{ index.name }}'), table_name='{{ table.name }}')
{% endfor %}
    op.drop_table('{{ table.name }}')
{% endfor %}
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
                    }
                    for fk in table.foreign_keys
                ],
                "primary_keys": primary_keys,
            }
        )

    return template.render(
        description=spec.description,
        service_name=spec.service_name,
        revision=revision,
        down_revision=down_revision,
        down_revision_repr=f"'{down_revision}'" if down_revision else "None",
        create_date=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
        tables=tables_data,
    )


def generate_migration(project_path: Path, service_name: str) -> Path | None:
    """
    Generate a migration file for a service.

    Args:
        project_path: Path to the project directory
        service_name: Name of the service (e.g., "auth", "ai")

    Returns:
        Path to the generated migration file, or None if service not found
    """
    if service_name not in MIGRATION_SPECS:
        return None

    spec = MIGRATION_SPECS[service_name]
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
    project_path: Path, services: list[str]
) -> list[Path]:
    """
    Generate migrations for multiple services in order.

    Args:
        project_path: Path to the project directory
        services: List of service names in desired order

    Returns:
        List of paths to generated migration files
    """
    generated = []

    for service_name in services:
        if service_name not in MIGRATION_SPECS:
            continue

        # Skip if migration already exists
        if service_has_migration(project_path, service_name):
            continue

        migration_path = generate_migration(project_path, service_name)
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

    # Auth service
    include_auth = context.get("include_auth")
    if include_auth == "yes" or include_auth is True:
        services.append("auth")

    # AI service (only with persistence backend)
    include_ai = context.get("include_ai")
    ai_backend = context.get("ai_backend", "memory")
    if (include_ai == "yes" or include_ai is True) and ai_backend != "memory":
        services.append("ai")

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
