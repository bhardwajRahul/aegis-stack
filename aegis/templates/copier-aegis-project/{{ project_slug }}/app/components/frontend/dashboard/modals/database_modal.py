"""
Database Detail Modal

Displays comprehensive database information including migration history,
table schemas, and database-specific settings using DataTable components.
Supports both SQLite (PRAGMA settings) and PostgreSQL (pg_settings).
"""

from datetime import datetime

import flet as ft
from app.components.frontend.controls import (
    DataTable,
    DataTableColumn,
    ExpandableDataTable,
    ExpandableRow,
    TableCellText,
    TableNameText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard


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
        self.content = ft.Row(
            [
                MetricCard("Total Tables", str(table_count), Theme.Colors.INFO),
                MetricCard("Total Rows", f"{total_rows:,}", Theme.Colors.SUCCESS),
                MetricCard("Database Size", db_size, Theme.Colors.INFO),
                MetricCard(version_label, version, Theme.Colors.SUCCESS),
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        )
        self.padding = Theme.Spacing.MD


def _build_migration_expanded_content(
    migration: dict, is_dark_mode: bool
) -> ft.Control:
    """Build expanded content for a migration showing the code.

    Args:
        migration: Migration metadata dict
        is_dark_mode: Whether the app is in dark mode

    Returns:
        Column with migration code
    """
    import re

    content = migration.get("content", "# Migration content not available")
    file_path = migration.get("file_path", "Unknown")

    # Normalize blank lines - collapse multiple newlines to single
    content = re.sub(r"\n\s*\n", "\n", content)

    # Styled markdown with code block
    code_style = ft.TextStyle(
        size=12,
        font_family="Roboto Mono",
        weight=ft.FontWeight.W_400,
        height=1.2,
    )
    codeblock_decoration = ft.BoxDecoration(
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=ft.border_radius.all(8),
    )
    code_theme = "ir-black" if is_dark_mode else "atom-one-light"

    return ft.Column(
        [
            ft.Text(
                file_path, size=11, color=ft.Colors.ON_SURFACE_VARIANT, italic=True
            ),
            ft.Container(height=4),
            ft.Markdown(
                f"```python\n{content}\n```",
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                code_theme=code_theme,
                md_style_sheet=ft.MarkdownStyleSheet(
                    code_text_style=code_style,
                    codeblock_decoration=codeblock_decoration,
                ),
            ),
        ],
        spacing=0,
    )


def _build_migration_row(migration: dict, is_dark_mode: bool) -> ExpandableRow:
    """Build expandable row for a single migration.

    Args:
        migration: Migration metadata dict
        is_dark_mode: Whether the app is in dark mode

    Returns:
        ExpandableRow with cells and expanded content
    """
    revision = migration.get("revision", "Unknown")
    description = migration.get("description", "No description")
    is_current = migration.get("is_current", False)
    file_mtime = migration.get("file_mtime", 0)

    # Format date from file modification time
    try:
        dt = datetime.fromtimestamp(file_mtime)
        date_str = dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError, TypeError):
        date_str = "Unknown"

    # Format revision (shortened) with current indicator
    short_revision = revision[:12] if len(revision) > 12 else revision
    revision_text = f"{short_revision} (current)" if is_current else short_revision
    revision_color = Theme.Colors.SUCCESS if is_current else None

    cells = [
        TableNameText(revision_text, color=revision_color),
        TableCellText(date_str),
        TableCellText(description),
    ]

    return ExpandableRow(
        cells=cells,
        expanded_content=_build_migration_expanded_content(migration, is_dark_mode),
    )


class MigrationHistorySection(ft.Container):
    """Migration history section using ExpandableDataTable."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize migration history section.

        Args:
            database_component: ComponentStatus containing database data
            page: Flet page for theme detection
        """
        super().__init__()
        metadata = database_component.metadata or {}
        migrations = metadata.get("migrations", [])

        # Detect current theme mode
        is_dark_mode = page.theme_mode == ft.ThemeMode.DARK

        # Define columns
        columns = [
            DataTableColumn("Revision", width=140),
            DataTableColumn("Date", width=130),
            DataTableColumn("Description"),  # expands
        ]

        # Build expandable rows
        rows = [_build_migration_row(m, is_dark_mode) for m in migrations]

        # Build expandable table
        table = ExpandableDataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No migrations found",
        )

        self.content = table
        self.padding = Theme.Spacing.MD


def _build_table_expanded_content(table_schema: dict, is_dark_mode: bool) -> ft.Control:
    """Build expanded content showing table schema as full CREATE TABLE SQL.

    Args:
        table_schema: Table schema metadata dict with columns, indexes, foreign_keys
        is_dark_mode: Whether the app is in dark mode

    Returns:
        Markdown control with formatted CREATE TABLE statement
    """
    name = table_schema.get("name", "Unknown")
    columns = table_schema.get("columns", [])
    indexes = table_schema.get("indexes", [])
    foreign_keys = table_schema.get("foreign_keys", [])

    lines: list[str] = []

    # Build CREATE TABLE statement
    lines.append(f"CREATE TABLE IF NOT EXISTS {name} (")

    # Column definitions
    col_definitions: list[str] = []
    pk_columns: list[str] = []

    for col in columns:
        col_name = col.get("name", "?")
        col_type = col.get("type", "?")
        nullable = col.get("nullable", True)
        pk = col.get("primary_key", False)

        # Build column definition
        col_def = f"    {col_name} {col_type}"
        if not nullable:
            col_def += " NOT NULL"

        col_definitions.append(col_def)

        if pk:
            pk_columns.append(col_name)

    # Add column definitions
    if col_definitions:
        # Join with commas, but last one might need PRIMARY KEY after
        for i, col_def in enumerate(col_definitions):
            if i < len(col_definitions) - 1 or pk_columns:
                lines.append(col_def + ",")
            else:
                lines.append(col_def)

    # Add PRIMARY KEY constraint
    if pk_columns:
        lines.append(f"    PRIMARY KEY ({', '.join(pk_columns)})")

    lines.append(");")

    # Add CREATE INDEX statements
    if indexes:
        lines.append("")
        lines.append("-- Indexes")
        for idx in indexes:
            idx_name = idx.get("name", "?")
            idx_cols = idx.get("columns", [])
            unique = idx.get("unique", False)
            unique_str = "UNIQUE " if unique else ""
            lines.append(
                f"CREATE {unique_str}INDEX {idx_name} ON {name} ({', '.join(idx_cols)});"
            )

    # Add foreign key comments
    if foreign_keys:
        lines.append("")
        lines.append("-- Foreign Keys")
        for fk in foreign_keys:
            fk_col = fk.get("column", "?")
            ref_table = fk.get("referred_table", "?")
            ref_col = fk.get("referred_column", "?")
            lines.append(f"-- {fk_col} REFERENCES {ref_table}({ref_col})")

    schema_text = "\n".join(lines)

    # Styled markdown with code block decoration (matching ee-toolset)
    code_style = ft.TextStyle(
        size=13,
        font_family="Roboto Mono",
        weight=ft.FontWeight.W_400,
        height=1.4,
    )
    codeblock_decoration = ft.BoxDecoration(
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,  # Theme-aware elevated surface
        border_radius=ft.border_radius.all(8),
    )

    # Use appropriate code theme based on current mode
    code_theme = "monokai" if is_dark_mode else "atom-one-light"

    return ft.Markdown(
        f"```sql\n{schema_text}\n```",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
        code_theme=code_theme,
        md_style_sheet=ft.MarkdownStyleSheet(
            code_text_style=code_style,
            codeblock_decoration=codeblock_decoration,
        ),
    )


def _build_table_row(table_schema: dict, is_dark_mode: bool) -> ExpandableRow:
    """Build expandable row for a single table.

    Args:
        table_schema: Table schema metadata dict
        is_dark_mode: Whether the app is in dark mode

    Returns:
        ExpandableRow with cells and schema expanded content
    """
    name = table_schema.get("name", "Unknown")
    rows = table_schema.get("rows", 0)
    columns = table_schema.get("columns", [])
    indexes = table_schema.get("indexes", [])
    foreign_keys = table_schema.get("foreign_keys", [])

    cells = [
        TableNameText(name),
        TableCellText(f"{rows:,}"),
        TableCellText(str(len(columns))),
        TableCellText(str(len(indexes))),
        TableCellText(str(len(foreign_keys))),
    ]

    return ExpandableRow(
        cells=cells,
        expanded_content=_build_table_expanded_content(table_schema, is_dark_mode),
    )


class TableDetailsSection(ft.Container):
    """Table details section using ExpandableDataTable with schema details."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize table details section.

        Args:
            database_component: ComponentStatus containing database data
            page: Flet page for theme detection
        """
        super().__init__()
        metadata = database_component.metadata or {}
        table_schemas = metadata.get("table_schemas", [])

        # Detect current theme mode
        is_dark_mode = page.theme_mode == ft.ThemeMode.DARK

        # Define columns
        columns = [
            DataTableColumn("Table"),  # expands
            DataTableColumn("Rows", width=80, alignment="right"),
            DataTableColumn("Columns", width=70, alignment="right"),
            DataTableColumn("Indexes", width=70, alignment="right"),
            DataTableColumn("FKs", width=50, alignment="right"),
        ]

        # Build expandable rows with schema details
        rows = [_build_table_row(t, is_dark_mode) for t in table_schemas]

        # Build expandable table
        table = ExpandableDataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No tables found",
        )

        self.content = table
        self.padding = Theme.Spacing.MD


def _build_postgres_setting_row(
    name: str, value: str, category: str
) -> list[ft.Control]:
    """Build row cells for a PostgreSQL setting.

    Args:
        name: Setting name
        value: Setting value
        category: Setting category

    Returns:
        List of controls for each column in the row
    """
    return [
        TableNameText(name),
        TableCellText(str(value)),
        TableCellText(category),
    ]


class PostgresSettingsSection(ft.Container):
    """PostgreSQL settings section using DataTable."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize PostgreSQL settings section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        metadata = database_component.metadata or {}
        pg_settings = metadata.get("pg_settings", {})
        active_connections = metadata.get("active_connections", 0)

        # Define columns
        columns = [
            DataTableColumn("Setting"),  # expands
            DataTableColumn("Value", width=120),
            DataTableColumn("Category", width=120),
        ]

        # Build rows from settings
        rows: list[list[ft.Control]] = []

        # Connection settings
        if "max_connections" in pg_settings:
            rows.append(
                _build_postgres_setting_row(
                    "max_connections", pg_settings["max_connections"], "Connections"
                )
            )
        rows.append(
            _build_postgres_setting_row(
                "active_connections", str(active_connections), "Connections"
            )
        )

        # Memory settings
        if "shared_buffers" in pg_settings:
            rows.append(
                _build_postgres_setting_row(
                    "shared_buffers", pg_settings["shared_buffers"], "Memory"
                )
            )
        if "work_mem" in pg_settings:
            rows.append(
                _build_postgres_setting_row(
                    "work_mem", pg_settings["work_mem"], "Memory"
                )
            )
        if "effective_cache_size" in pg_settings:
            rows.append(
                _build_postgres_setting_row(
                    "effective_cache_size",
                    pg_settings["effective_cache_size"],
                    "Memory",
                )
            )
        if "maintenance_work_mem" in pg_settings:
            rows.append(
                _build_postgres_setting_row(
                    "maintenance_work_mem",
                    pg_settings["maintenance_work_mem"],
                    "Memory",
                )
            )

        # WAL settings
        if "wal_level" in pg_settings:
            rows.append(
                _build_postgres_setting_row(
                    "wal_level", pg_settings["wal_level"], "WAL"
                )
            )

        # Build table
        table = DataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No PostgreSQL settings available",
        )

        self.content = table
        self.padding = Theme.Spacing.MD


def _build_pragma_setting_row(
    name: str, value: str | int, category: str
) -> list[ft.Control]:
    """Build row cells for a PRAGMA setting.

    Args:
        name: Setting name
        value: Setting value
        category: Setting category

    Returns:
        List of controls for each column in the row
    """
    # Format value
    if isinstance(value, bool):
        value_text = "Enabled" if value else "Disabled"
    elif isinstance(value, int | float):
        value_text = f"{value:,}"
    else:
        value_text = str(value)

    return [
        TableNameText(name),
        TableCellText(value_text),
        TableCellText(category),
    ]


class PragmaSettingsSection(ft.Container):
    """SQLite PRAGMA settings section using DataTable."""

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
        all_pragma = {**pragma_settings, **comprehensive_pragma}

        # Define columns
        columns = [
            DataTableColumn("Setting"),  # expands
            DataTableColumn("Value", width=120),
            DataTableColumn("Category", width=120),
        ]

        # Build rows from settings
        rows: list[list[ft.Control]] = []

        # Performance settings
        if "cache_size" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "cache_size", all_pragma["cache_size"], "Performance"
                )
            )
        if "mmap_size" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "mmap_size", all_pragma["mmap_size"], "Performance"
                )
            )
        if "temp_store" in all_pragma:
            temp = all_pragma["temp_store"]
            temp_desc = {0: "DEFAULT", 1: "FILE", 2: "MEMORY"}.get(temp, str(temp))
            rows.append(
                _build_pragma_setting_row("temp_store", temp_desc, "Performance")
            )
        if "busy_timeout" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "busy_timeout", f"{all_pragma['busy_timeout']}ms", "Performance"
                )
            )

        # Integrity settings
        if "foreign_keys" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "foreign_keys", all_pragma["foreign_keys"], "Integrity"
                )
            )
        if "synchronous" in all_pragma:
            sync = all_pragma["synchronous"]
            sync_desc = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}.get(
                sync, str(sync)
            )
            rows.append(
                _build_pragma_setting_row("synchronous", sync_desc, "Integrity")
            )
        if "auto_vacuum" in all_pragma:
            auto_vac = all_pragma["auto_vacuum"]
            auto_vac_desc = {0: "NONE", 1: "FULL", 2: "INCREMENTAL"}.get(
                auto_vac, str(auto_vac)
            )
            rows.append(
                _build_pragma_setting_row("auto_vacuum", auto_vac_desc, "Integrity")
            )

        # Storage settings
        if "journal_mode" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "journal_mode", all_pragma["journal_mode"].upper(), "Storage"
                )
            )
        wal_enabled = metadata.get("wal_enabled", False)
        rows.append(_build_pragma_setting_row("wal_enabled", wal_enabled, "Storage"))
        if "page_size" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "page_size", f"{all_pragma['page_size']} bytes", "Storage"
                )
            )

        # Statistics
        if "page_count" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "page_count", all_pragma["page_count"], "Statistics"
                )
            )
        if "freelist_count" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "freelist_count", all_pragma["freelist_count"], "Statistics"
                )
            )
        if "db_efficiency" in all_pragma:
            rows.append(
                _build_pragma_setting_row(
                    "db_efficiency",
                    f"{all_pragma['db_efficiency']:.2f}%",
                    "Statistics",
                )
            )

        # Build table
        table = DataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No PRAGMA settings available",
        )

        self.content = table
        self.padding = Theme.Spacing.MD


class StatisticsSection(ft.Container):
    """Database statistics section using DataTable with clickable URL."""

    def __init__(self, database_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize statistics section.

        Args:
            database_component: ComponentStatus containing database data
        """
        super().__init__()
        self.page = page
        metadata = database_component.metadata or {}

        # Extract and convert database URL to localhost
        db_url = metadata.get("url", "Unknown")
        self.db_url_local = self._convert_to_localhost(db_url)

        pool_size = metadata.get("connection_pool_size", 0)
        total_indexes = metadata.get("total_indexes", 0)
        total_foreign_keys = metadata.get("total_foreign_keys", 0)

        largest_table = metadata.get("largest_table", {})
        largest_table_name = largest_table.get("name", "None")
        largest_table_rows = largest_table.get("rows", 0)

        # Define columns
        columns = [
            DataTableColumn("Statistic"),  # expands
            DataTableColumn("Value", width=250),
        ]

        # Build URL row with clickable text and copy button
        url_row = [
            TableNameText("Database URL"),
            ft.Row(
                [
                    ft.GestureDetector(
                        content=ft.Text(
                            self.db_url_local,
                            size=11,
                            color=Theme.Colors.INFO,
                            style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
                        ),
                        on_tap=self._copy_url,
                        mouse_cursor=ft.MouseCursor.CLICK,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.COPY,
                        icon_size=14,
                        tooltip="Copy URL",
                        on_click=self._copy_url,
                    ),
                ],
                spacing=4,
            ),
        ]

        # Build other rows
        rows: list[list[ft.Control]] = [
            url_row,
            [TableNameText("Connection Pool Size"), TableCellText(str(pool_size))],
            [TableNameText("Total Indexes"), TableCellText(str(total_indexes))],
            [
                TableNameText("Total Foreign Keys"),
                TableCellText(str(total_foreign_keys)),
            ],
            [
                TableNameText("Largest Table"),
                TableCellText(f"{largest_table_name} ({largest_table_rows:,} rows)"),
            ],
        ]

        # Build table
        table = DataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No statistics available",
        )

        self.content = table
        self.padding = Theme.Spacing.MD

    def _convert_to_localhost(self, url: str) -> str:
        """Convert docker service names to localhost in URL.

        Args:
            url: Database URL potentially containing docker service names

        Returns:
            URL with localhost substituted for common docker service names
        """
        # Common docker service name replacements
        replacements = {
            "@db:": "@localhost:",
            "@postgres:": "@localhost:",
            "@postgresql:": "@localhost:",
            "@database:": "@localhost:",
            "@redis:": "@localhost:",
        }
        result = url
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _copy_url(self, _e: ft.ControlEvent) -> None:
        """Copy database URL to clipboard."""
        self.page.set_clipboard(self.db_url_local)
        self.page.open(ft.SnackBar(content=ft.Text("URL copied to clipboard")))
        self.page.update()


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

        # Build sections (no dividers)
        sections = [
            OverviewSection(database_component, page),
            MigrationHistorySection(database_component, page),
            TableDetailsSection(database_component, page),
            settings_section,
            StatisticsSection(database_component, page),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=database_component,
            title_text="Database",
            sections=sections,
        )
