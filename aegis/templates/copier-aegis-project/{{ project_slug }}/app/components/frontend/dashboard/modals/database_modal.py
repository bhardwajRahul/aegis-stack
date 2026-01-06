"""
Database Detail Modal

Displays comprehensive database information including migration history,
table schemas, indexes, foreign keys, and database-specific settings.
Supports both SQLite (PRAGMA settings) and PostgreSQL (pg_settings).
"""

from datetime import datetime

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    LabelText,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from .base_detail_popup import BaseDetailPopup
from .modal_constants import ModalLayout
from .modal_sections import MetricCard

# Table schema column widths (pixels)
COL_WIDTH_COLUMN_NAME = 200
COL_WIDTH_TYPE = 120
COL_WIDTH_NULLABLE = 80
COL_WIDTH_DEFAULT = 150
COL_WIDTH_PK = 60

# Index column widths (pixels)
COL_WIDTH_INDEX_NAME = 200
COL_WIDTH_UNIQUE = 100

# Migration history column widths (pixels)
COL_WIDTH_REVISION = 150
COL_WIDTH_DATE = 180
COL_WIDTH_DESCRIPTION = 400

# Foreign key column widths (pixels)
COL_WIDTH_FK_FROM = 150
COL_WIDTH_FK_TO = 200
COL_WIDTH_FK_ACTION = 100

# Statistics section layout
STAT_LABEL_WIDTH = 250

# Database efficiency thresholds
DB_EFFICIENCY_HEALTHY = 95  # % - Green (healthy)
DB_EFFICIENCY_WARNING = 85  # % - Yellow (warning)

# Display formatting
MAX_DB_URL_DISPLAY_LENGTH = 50


class OverviewSection(ft.Container):
    """Database overview section with key metrics."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize overview section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}
        implementation = metadata.get("implementation", "sqlite")

        # Extract metrics
        table_count = metadata.get("table_count", 0)
        total_rows = metadata.get("total_rows", 0)

        if implementation == "postgresql":
            # PostgreSQL-specific metrics
            db_size = metadata.get("database_size_human", "Unknown")
            version = metadata.get("version_short", "Unknown")
            if version == "Unknown" and "version" in metadata:
                # Extract from full version string
                full_version = metadata["version"]
                if isinstance(full_version, str) and "PostgreSQL" in full_version:
                    parts = full_version.split()
                    if len(parts) >= 2:
                        version = parts[1]
            version_label = "PostgreSQL"
        else:
            # SQLite-specific metrics
            db_size = metadata.get("file_size_human", "0 B")
            version = metadata.get("version", "Unknown")
            version_label = "SQLite Version"

        # Create metric cards
        metrics_row = ft.Row(
            [
                MetricCard("Total Tables", str(table_count), Theme.Colors.INFO),
                MetricCard("Total Rows", f"{total_rows:,}", Theme.Colors.SUCCESS),
                MetricCard("Database Size", db_size, Theme.Colors.INFO),
                MetricCard(version_label, version, Theme.Colors.SUCCESS),
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        )

        self.content = metrics_row
        self.padding = Theme.Spacing.MD


class MigrationRow(ft.Container):
    """Single migration row component."""

    def __init__(self, migration: dict) -> None:
        """
        Initialize migration row.

        Args:
            migration: Migration metadata dict
        """
        super().__init__()

        revision = migration.get("revision", "Unknown")
        description = migration.get("description", "No description")
        is_current = migration.get("is_current", False)
        file_mtime = migration.get("file_mtime", 0)

        # Format date from file modification time
        try:
            dt = datetime.fromtimestamp(file_mtime)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError, OverflowError, TypeError):
            date_str = "Unknown"

        # Truncate long descriptions
        if len(description) > 100:
            description = description[:97] + "..."

        # Color code current migration
        revision_color = Theme.Colors.SUCCESS if is_current else ft.Colors.ON_SURFACE
        revision_text = f"{revision} {'(current)' if is_current else ''}"

        self.content = ft.Row(
            [
                ft.Container(
                    content=PrimaryText(revision_text, color=revision_color),
                    width=COL_WIDTH_REVISION,
                ),
                ft.Container(
                    content=SecondaryText(date_str),
                    width=COL_WIDTH_DATE,
                ),
                ft.Container(
                    content=BodyText(description),
                    width=COL_WIDTH_DESCRIPTION,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class MigrationHistorySection(ft.Container):
    """Migration history section displaying Alembic migrations."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize migration history section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}
        migrations = metadata.get("migrations", [])
        migration_count = len(migrations)

        # Create header
        header = ft.Row(
            [
                H3Text(f"Migration History ({migration_count} migrations)"),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Create table header
        table_header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=LabelText("Revision", weight=ft.FontWeight.BOLD),
                        width=COL_WIDTH_REVISION,
                    ),
                    ft.Container(
                        content=LabelText("Date", weight=ft.FontWeight.BOLD),
                        width=COL_WIDTH_DATE,
                    ),
                    ft.Container(
                        content=LabelText("Description", weight=ft.FontWeight.BOLD),
                        width=COL_WIDTH_DESCRIPTION,
                    ),
                ],
                spacing=Theme.Spacing.SM,
            ),
            padding=ft.padding.symmetric(vertical=Theme.Spacing.SM),
            bgcolor=ft.Colors.SURFACE,
            border_radius=8,
        )

        # Create migration rows or empty placeholder
        if migrations:
            migration_rows = [MigrationRow(migration) for migration in migrations]
            migrations_list = ft.Column(
                migration_rows,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            )
        else:
            migrations_list = ft.Container(
                content=SecondaryText(
                    "No migrations found - database may not be using Alembic"
                ),
                padding=ft.padding.all(Theme.Spacing.MD),
                alignment=ft.alignment.center,
            )

        self.content = ft.Column(
            [
                header,
                table_header,
                migrations_list,
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD


class ColumnRow(ft.Container):
    """Single column row for table schema display."""

    def __init__(self, column: dict) -> None:
        """
        Initialize column row.

        Args:
            column: Column metadata dict
        """
        super().__init__()

        name = column.get("name", "Unknown")
        col_type = column.get("type", "Unknown")
        notnull = column.get("notnull", False)
        default_value = column.get("default_value")
        pk = column.get("pk", False)

        # Format nullable display
        nullable_text = "NOT NULL" if notnull else "NULL"
        nullable_color = (
            Theme.Colors.WARNING if notnull else ft.Colors.ON_SURFACE_VARIANT
        )

        # Format default value
        default_text = str(default_value) if default_value is not None else "-"

        # Format primary key indicator
        pk_text = "PK" if pk else ""
        pk_color = Theme.Colors.SUCCESS if pk else ft.Colors.ON_SURFACE_VARIANT

        self.content = ft.Row(
            [
                ft.Container(
                    content=PrimaryText(name),
                    width=COL_WIDTH_COLUMN_NAME,
                ),
                ft.Container(
                    content=SecondaryText(col_type),
                    width=COL_WIDTH_TYPE,
                ),
                ft.Container(
                    content=LabelText(nullable_text, color=nullable_color),
                    width=COL_WIDTH_NULLABLE,
                ),
                ft.Container(
                    content=SecondaryText(default_text),
                    width=COL_WIDTH_DEFAULT,
                ),
                ft.Container(
                    content=LabelText(pk_text, color=pk_color),
                    width=COL_WIDTH_PK,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class IndexRow(ft.Container):
    """Single index row for table schema display."""

    def __init__(self, index: dict) -> None:
        """
        Initialize index row.

        Args:
            index: Index metadata dict
        """
        super().__init__()

        name = index.get("name", "Unknown")
        unique = index.get("unique", False)
        columns = index.get("columns", [])

        # Format unique indicator
        unique_text = "UNIQUE" if unique else "NON-UNIQUE"
        unique_color = Theme.Colors.SUCCESS if unique else ft.Colors.ON_SURFACE_VARIANT

        # Format column names (columns is a list of strings, not dicts)
        column_names = ", ".join(columns) if columns else ""

        self.content = ft.Row(
            [
                ft.Container(
                    content=PrimaryText(name),
                    width=COL_WIDTH_INDEX_NAME,
                ),
                ft.Container(
                    content=LabelText(unique_text, color=unique_color),
                    width=COL_WIDTH_UNIQUE,
                ),
                ft.Container(
                    content=SecondaryText(column_names),
                    expand=True,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class ForeignKeyRow(ft.Container):
    """Single foreign key row for table schema display."""

    def __init__(self, fk: dict) -> None:
        """
        Initialize foreign key row.

        Args:
            fk: Foreign key metadata dict
        """
        super().__init__()

        from_col = fk.get("from_column", "Unknown")
        to_table = fk.get("table", "Unknown")
        to_col = fk.get("to_column", "Unknown")
        on_update = fk.get("on_update", "NO ACTION")
        on_delete = fk.get("on_delete", "NO ACTION")

        self.content = ft.Row(
            [
                ft.Container(
                    content=PrimaryText(from_col),
                    width=COL_WIDTH_FK_FROM,
                ),
                ft.Container(
                    content=SecondaryText(f"{to_table}.{to_col}"),
                    width=COL_WIDTH_FK_TO,
                ),
                ft.Container(
                    content=LabelText(f"ON UPDATE: {on_update}"),
                    width=COL_WIDTH_FK_ACTION,
                ),
                ft.Container(
                    content=LabelText(f"ON DELETE: {on_delete}"),
                    width=COL_WIDTH_FK_ACTION,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class TableSchemaCard(ft.Container):
    """Expandable card for a single table's schema details."""

    def __init__(self, table_schema: dict) -> None:
        """
        Initialize table schema card.

        Args:
            table_schema: Table schema metadata dict
        """
        super().__init__()

        self.table_name = table_schema.get("name", "Unknown")
        self.row_count = table_schema.get("rows", 0)
        self.columns = table_schema.get("columns", [])
        self.indexes = table_schema.get("indexes", [])
        self.foreign_keys = table_schema.get("foreign_keys", [])

        self.is_expanded = False
        self.details_container: ft.Container | None = None

        # Create header (using GestureDetector for click handling)
        self.header = ft.GestureDetector(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_RIGHT, size=16),
                        PrimaryText(self.table_name),
                        SecondaryText(f"({self.row_count:,} rows)"),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.all(Theme.Spacing.SM),
                bgcolor=ft.Colors.SURFACE,
                border_radius=8,
            ),
            on_tap=self._toggle_expand,
            mouse_cursor=ft.MouseCursor.CLICK,
        )

        # Create expandable details (initially hidden)
        self.details_container = ft.Container(
            content=self._create_details(),
            visible=False,
            padding=ft.padding.all(Theme.Spacing.SM),
        )

        self.content = ft.Column(
            [
                self.header,
                self.details_container,
            ],
            spacing=0,
        )

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        """Toggle table schema expansion."""
        if self.details_container is None:
            return

        self.is_expanded = not self.is_expanded
        self.details_container.visible = self.is_expanded

        # Update arrow icon (header wraps Container which wraps Row)
        if (
            self.header.content
            and isinstance(self.header.content, ft.Container)
            and self.header.content.content
            and isinstance(self.header.content.content, ft.Row)
        ):
            icon = self.header.content.content.controls[0]
            if isinstance(icon, ft.Icon):
                icon.name = (
                    ft.Icons.ARROW_DROP_DOWN
                    if self.is_expanded
                    else ft.Icons.ARROW_RIGHT
                )

        self.header.update()
        self.details_container.update()

    def _create_details(self) -> ft.Column:
        """Create detailed table schema view."""
        sections = []

        # Columns section
        if self.columns:
            column_header = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=LabelText("Column", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_COLUMN_NAME,
                        ),
                        ft.Container(
                            content=LabelText("Type", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_TYPE,
                        ),
                        ft.Container(
                            content=LabelText("Nullable", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_NULLABLE,
                        ),
                        ft.Container(
                            content=LabelText("Default", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_DEFAULT,
                        ),
                        ft.Container(
                            content=LabelText("PK", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_PK,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.symmetric(vertical=Theme.Spacing.XS),
                bgcolor=ft.Colors.SURFACE,
            )

            column_rows = [ColumnRow(col) for col in self.columns]
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Columns"),
                        column_header,
                        ft.Column(column_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.XS,
                )
            )

        # Indexes section
        if self.indexes:
            index_header = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=LabelText("Index Name", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_INDEX_NAME,
                        ),
                        ft.Container(
                            content=LabelText("Type", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_UNIQUE,
                        ),
                        ft.Container(
                            content=LabelText("Columns", weight=ft.FontWeight.BOLD),
                            expand=True,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.symmetric(vertical=Theme.Spacing.XS),
                bgcolor=ft.Colors.SURFACE,
            )

            index_rows = [IndexRow(idx) for idx in self.indexes]
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Indexes"),
                        index_header,
                        ft.Column(index_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.XS,
                )
            )

        # Foreign keys section
        if self.foreign_keys:
            fk_header = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=LabelText("From", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_FK_FROM,
                        ),
                        ft.Container(
                            content=LabelText("To", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_FK_TO,
                        ),
                        ft.Container(
                            content=LabelText("On Update", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_FK_ACTION,
                        ),
                        ft.Container(
                            content=LabelText("On Delete", weight=ft.FontWeight.BOLD),
                            width=COL_WIDTH_FK_ACTION,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.symmetric(vertical=Theme.Spacing.XS),
                bgcolor=ft.Colors.SURFACE,
            )

            fk_rows = [ForeignKeyRow(fk) for fk in self.foreign_keys]
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Foreign Keys"),
                        fk_header,
                        ft.Column(fk_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.XS,
                )
            )

        if not sections:
            sections.append(SecondaryText("No schema details available"))

        return ft.Column(sections, spacing=Theme.Spacing.MD)


class TableDetailsSection(ft.Container):
    """Table details section with expandable schema cards."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize table details section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}
        table_schemas = metadata.get("table_schemas", [])
        table_count = len(table_schemas)

        # Create header
        header = H3Text(f"Tables ({table_count} tables)")

        # Create table schema cards or empty placeholder
        if table_schemas:
            schema_cards = [TableSchemaCard(schema) for schema in table_schemas]
            tables_list = ft.Column(
                schema_cards,
                spacing=Theme.Spacing.SM,
                scroll=ft.ScrollMode.AUTO,
            )
        else:
            tables_list = ft.Container(
                content=SecondaryText("No tables found in database"),
                padding=ft.padding.all(Theme.Spacing.MD),
                alignment=ft.alignment.center,
            )

        self.content = ft.Column(
            [
                header,
                tables_list,
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD


class PragmaSettingRow(ft.Container):
    """Single PRAGMA setting row with explanation."""

    def __init__(
        self, name: str, value: str | int, explanation: str, recommendation: str = ""
    ) -> None:
        """
        Initialize PRAGMA setting row.

        Args:
            name: PRAGMA setting name
            value: Current value
            explanation: Explanation of what this setting does
            recommendation: Optional recommendation text
        """
        super().__init__()

        # Format value
        if isinstance(value, bool):
            value_text = "Enabled" if value else "Disabled"
            value_color = Theme.Colors.SUCCESS if value else Theme.Colors.WARNING
        elif isinstance(value, int | float):
            value_text = f"{value:,}"
            value_color = ft.Colors.ON_SURFACE
        else:
            value_text = str(value)
            value_color = ft.Colors.ON_SURFACE

        rows = [
            ft.Row(
                [
                    ft.Container(
                        content=PrimaryText(name),
                        width=STAT_LABEL_WIDTH,
                    ),
                    LabelText(value_text, color=value_color),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=SecondaryText(explanation),
                padding=ft.padding.only(left=Theme.Spacing.MD),
            ),
        ]

        if recommendation:
            rows.append(
                ft.Container(
                    content=BodyText(recommendation, color=Theme.Colors.INFO),
                    padding=ft.padding.only(left=Theme.Spacing.MD),
                )
            )

        self.content = ft.Column(rows, spacing=Theme.Spacing.XS)
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.SM)


class PragmaSettingsSection(ft.Container):
    """PRAGMA settings section with comprehensive database configuration."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize PRAGMA settings section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}
        pragma_settings = metadata.get("pragma_settings", {})
        comprehensive_pragma = metadata.get("comprehensive_pragma", {})

        # Create header
        header = H3Text("PRAGMA Settings")

        # Combine basic and comprehensive PRAGMA settings
        all_pragma = {**pragma_settings, **comprehensive_pragma}

        # Create categorized PRAGMA rows
        performance_rows = []
        integrity_rows = []
        storage_rows = []
        statistics_rows = []

        # Performance settings
        if "cache_size" in all_pragma:
            cache = all_pragma["cache_size"]
            performance_rows.append(
                PragmaSettingRow(
                    "cache_size",
                    cache,
                    (
                        "Number of database pages to cache in memory. "
                        "Negative values are in KiB."
                    ),
                    "Higher values improve performance but use more memory"
                    if cache < 2000
                    else "",
                )
            )

        if "mmap_size" in all_pragma:
            mmap = all_pragma["mmap_size"]
            performance_rows.append(
                PragmaSettingRow(
                    "mmap_size",
                    mmap,
                    "Maximum number of bytes of the database file mapped to memory.",
                    "Memory-mapped I/O can improve performance for large databases"
                    if mmap == 0
                    else "",
                )
            )

        if "temp_store" in all_pragma:
            temp = all_pragma["temp_store"]
            temp_desc = {0: "DEFAULT", 1: "FILE", 2: "MEMORY"}.get(temp, str(temp))
            performance_rows.append(
                PragmaSettingRow(
                    "temp_store",
                    temp_desc,
                    "Where temporary tables and indexes are stored.",
                )
            )

        if "busy_timeout" in all_pragma:
            timeout = all_pragma["busy_timeout"]
            performance_rows.append(
                PragmaSettingRow(
                    "busy_timeout",
                    f"{timeout}ms",
                    (
                        "How long to wait when database is locked "
                        "before returning SQLITE_BUSY."
                    ),
                )
            )

        # Integrity settings
        if "foreign_keys" in all_pragma:
            fk = all_pragma["foreign_keys"]
            integrity_rows.append(
                PragmaSettingRow(
                    "foreign_keys",
                    fk,
                    "Enable or disable foreign key constraint enforcement.",
                    "Recommended: Enable for data integrity" if not fk else "",
                )
            )

        if "synchronous" in all_pragma:
            sync = all_pragma["synchronous"]
            sync_desc = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}.get(
                sync, str(sync)
            )
            integrity_rows.append(
                PragmaSettingRow(
                    "synchronous",
                    sync_desc,
                    (
                        "How aggressively SQLite syncs data to disk. "
                        "Higher = safer but slower."
                    ),
                )
            )

        if "auto_vacuum" in all_pragma:
            auto_vac = all_pragma["auto_vacuum"]
            auto_vac_desc = {0: "NONE", 1: "FULL", 2: "INCREMENTAL"}.get(
                auto_vac, str(auto_vac)
            )
            integrity_rows.append(
                PragmaSettingRow(
                    "auto_vacuum",
                    auto_vac_desc,
                    "Whether database file shrinks automatically when data is deleted.",
                )
            )

        # Storage settings
        if "journal_mode" in all_pragma:
            journal = all_pragma["journal_mode"]
            storage_rows.append(
                PragmaSettingRow(
                    "journal_mode",
                    journal.upper(),
                    (
                        "How SQLite implements atomic commit and rollback. "
                        "WAL is recommended for concurrency."
                    ),
                    "Consider WAL mode for better concurrency"
                    if journal.lower() != "wal"
                    else "",
                )
            )

        wal_enabled = metadata.get("wal_enabled", False)
        storage_rows.append(
            PragmaSettingRow(
                "wal_enabled",
                wal_enabled,
                "Write-Ahead Logging mode provides better concurrency and performance.",
                "Recommended for production" if not wal_enabled else "",
            )
        )

        if "page_size" in all_pragma:
            page_size = all_pragma["page_size"]
            storage_rows.append(
                PragmaSettingRow(
                    "page_size",
                    f"{page_size} bytes",
                    "Size of database pages. Must be power of 2 between 512 and 65536.",
                )
            )

        # Statistics
        if "page_count" in all_pragma:
            page_count = all_pragma["page_count"]
            statistics_rows.append(
                PragmaSettingRow(
                    "page_count",
                    page_count,
                    "Total number of pages in the database file.",
                )
            )

        if "freelist_count" in all_pragma:
            freelist = all_pragma["freelist_count"]
            statistics_rows.append(
                PragmaSettingRow(
                    "freelist_count",
                    freelist,
                    "Number of unused pages available for reuse.",
                    "Consider VACUUM to reclaim space" if freelist > 100 else "",
                )
            )

        if "db_efficiency" in all_pragma:
            efficiency = all_pragma["db_efficiency"]
            statistics_rows.append(
                PragmaSettingRow(
                    "db_efficiency",
                    f"{efficiency:.2f}%",
                    "Database space efficiency (100% = no wasted space).",
                    "Run VACUUM to improve efficiency"
                    if efficiency < DB_EFFICIENCY_WARNING
                    else "",
                )
            )

        # Create categorized sections
        sections = []

        if performance_rows:
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Performance"),
                        ft.Column(performance_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        if integrity_rows:
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Integrity"),
                        ft.Column(integrity_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        if storage_rows:
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Storage"),
                        ft.Column(storage_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        if statistics_rows:
            sections.append(
                ft.Column(
                    [
                        PrimaryText("Statistics"),
                        ft.Column(statistics_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        if not sections:
            sections.append(
                ft.Container(
                    content=SecondaryText("No PRAGMA settings available"),
                    padding=ft.padding.all(Theme.Spacing.MD),
                    alignment=ft.alignment.center,
                )
            )

        self.content = ft.Column(
            [
                header,
                ft.Column(sections, spacing=Theme.Spacing.MD),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD


class PostgresSettingsSection(ft.Container):
    """PostgreSQL settings section with server configuration."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize PostgreSQL settings section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}
        pg_settings = metadata.get("pg_settings", {})

        # Create header
        header = H3Text("PostgreSQL Settings")

        # Create settings rows
        settings_rows = []

        # Connection settings
        connection_rows = []
        if "max_connections" in pg_settings:
            connection_rows.append(
                PragmaSettingRow(
                    "max_connections",
                    pg_settings["max_connections"],
                    "Maximum number of concurrent connections to the database.",
                )
            )

        active_connections = metadata.get("active_connections", 0)
        connection_rows.append(
            PragmaSettingRow(
                "active_connections",
                active_connections,
                "Current number of active connections to this database.",
            )
        )

        if connection_rows:
            settings_rows.append(
                ft.Column(
                    [
                        PrimaryText("Connections"),
                        ft.Column(connection_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        # Memory settings
        memory_rows = []
        if "shared_buffers" in pg_settings:
            memory_rows.append(
                PragmaSettingRow(
                    "shared_buffers",
                    pg_settings["shared_buffers"],
                    "Amount of memory for shared memory buffers.",
                )
            )

        if "work_mem" in pg_settings:
            memory_rows.append(
                PragmaSettingRow(
                    "work_mem",
                    pg_settings["work_mem"],
                    "Memory used for internal sort operations and hash tables.",
                )
            )

        if "effective_cache_size" in pg_settings:
            memory_rows.append(
                PragmaSettingRow(
                    "effective_cache_size",
                    pg_settings["effective_cache_size"],
                    "Planner's estimate of available disk cache.",
                )
            )

        if "maintenance_work_mem" in pg_settings:
            memory_rows.append(
                PragmaSettingRow(
                    "maintenance_work_mem",
                    pg_settings["maintenance_work_mem"],
                    "Memory for maintenance operations (VACUUM, CREATE INDEX).",
                )
            )

        if memory_rows:
            settings_rows.append(
                ft.Column(
                    [
                        PrimaryText("Memory"),
                        ft.Column(memory_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        # WAL settings
        wal_rows = []
        if "wal_level" in pg_settings:
            wal_rows.append(
                PragmaSettingRow(
                    "wal_level",
                    pg_settings["wal_level"],
                    "Level of information written to the WAL.",
                )
            )

        if wal_rows:
            settings_rows.append(
                ft.Column(
                    [
                        PrimaryText("Write-Ahead Log"),
                        ft.Column(wal_rows, spacing=0),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        if not settings_rows:
            settings_rows.append(
                ft.Container(
                    content=SecondaryText("No PostgreSQL settings available"),
                    padding=ft.padding.all(Theme.Spacing.MD),
                    alignment=ft.alignment.center,
                )
            )

        self.content = ft.Column(
            [
                header,
                ft.Column(settings_rows, spacing=Theme.Spacing.MD),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD


class StatisticsSection(ft.Container):
    """Database infrastructure statistics section."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize statistics section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}

        # Extract statistics
        db_url = metadata.get("url", "Unknown")
        if len(db_url) > MAX_DB_URL_DISPLAY_LENGTH:
            db_url = db_url[:MAX_DB_URL_DISPLAY_LENGTH] + "..."

        pool_size = metadata.get("connection_pool_size", 0)
        total_indexes = metadata.get("total_indexes", 0)
        total_foreign_keys = metadata.get("total_foreign_keys", 0)

        largest_table = metadata.get("largest_table", {})
        largest_table_name = largest_table.get("name", "None")
        largest_table_rows = largest_table.get("rows", 0)

        # Create statistics rows
        stats_rows = [
            ft.Row(
                [
                    ft.Container(
                        content=SecondaryText("Database URL:"),
                        width=STAT_LABEL_WIDTH,
                    ),
                    LabelText(db_url),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Row(
                [
                    ft.Container(
                        content=SecondaryText("Connection Pool Size:"),
                        width=STAT_LABEL_WIDTH,
                    ),
                    LabelText(str(pool_size)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Row(
                [
                    ft.Container(
                        content=SecondaryText("Total Indexes:"),
                        width=STAT_LABEL_WIDTH,
                    ),
                    LabelText(str(total_indexes)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Row(
                [
                    ft.Container(
                        content=SecondaryText("Total Foreign Keys:"),
                        width=STAT_LABEL_WIDTH,
                    ),
                    LabelText(str(total_foreign_keys)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Row(
                [
                    ft.Container(
                        content=SecondaryText("Largest Table:"),
                        width=STAT_LABEL_WIDTH,
                    ),
                    LabelText(f"{largest_table_name} ({largest_table_rows:,} rows)"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ]

        self.content = ft.Column(
            [
                H3Text("Statistics"),
                ft.Column(stats_rows, spacing=Theme.Spacing.SM),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD


class DatabaseDetailDialog(BaseDetailPopup):
    """Database detail popup dialog."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize database detail popup.

        Args:
            database_component: ComponentStatus containing database health and metrics
        """
        metadata = database_component.metadata or {}
        implementation = metadata.get("implementation", "sqlite")

        # Choose the appropriate settings section based on implementation
        if implementation == "postgresql":
            settings_section = PostgresSettingsSection(database_component, page)
        else:
            settings_section = PragmaSettingsSection(database_component, page)

        # Build sections
        sections = [
            OverviewSection(database_component, page),
            MigrationHistorySection(database_component, page),
            ft.Divider(
                height=ModalLayout.SECTION_DIVIDER_HEIGHT,
                color=ft.Colors.OUTLINE_VARIANT,
            ),
            TableDetailsSection(database_component, page),
            ft.Divider(
                height=ModalLayout.SECTION_DIVIDER_HEIGHT,
                color=ft.Colors.OUTLINE_VARIANT,
            ),
            settings_section,
            ft.Divider(
                height=ModalLayout.SECTION_DIVIDER_HEIGHT,
                color=ft.Colors.OUTLINE_VARIANT,
            ),
            StatisticsSection(database_component, page),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=database_component,
            title_text="Database",
            sections=sections,
        )
