"""
Migration spec — plugin-author-facing facade for ``ServiceMigrationSpec``.

R4-A of the plugin system refactor. ``PluginSpec.migrations`` is a list of
``ServiceMigrationSpec`` objects. The canonical dataclass lives in
``aegis/core/migration_generator.py`` (alongside the table-spec helpers it
shares —  ``TableSpec``, ``ColumnSpec``, etc.); this module exposes them
under a stable import path so plugin authors don't have to know the
historical filename.

Intended usage (in a third-party plugin's ``get_spec()``)::

    from aegis.core.migration_spec import (
        MigrationSpec,           # alias of ServiceMigrationSpec
        TableSpec, ColumnSpec, IndexSpec, ForeignKeySpec,
    )

    PluginSpec(
        name="scraper",
        ...
        migrations=[
            MigrationSpec(
                service_name="scraper",
                description="Scraper tables",
                tables=[
                    TableSpec(name="scrape_targets", columns=[...]),
                    TableSpec(name="scrape_runs",    columns=[...]),
                ],
            ),
        ],
    )

A future refactor may rename ``ServiceMigrationSpec`` → ``MigrationSpec``
in the generator itself; this alias makes that rename a no-op for callers
that already use the new name.
"""

from collections.abc import Iterable

from .migration_generator import (
    AlterTableSpec,
    CheckConstraintSpec,
    ColumnSpec,
    ForeignKeySpec,
    IndexSpec,
    ServiceMigrationSpec,
    TableSpec,
)

# Plugin-system-shape alias. Same class; preferred name in PluginSpec.migrations.
MigrationSpec = ServiceMigrationSpec


def collect_migrations(
    specs: Iterable[object],
) -> dict[str, ServiceMigrationSpec]:
    """Build the legacy ``MIGRATION_SPECS`` dict from ``PluginSpec.migrations``.

    Iterates an iterable of ``PluginSpec`` objects, flattens each spec's
    ``migrations`` list, and keys the result by ``ServiceMigrationSpec.service_name``
    (matching the pre-R4 dict shape so callers ``add_service.py``,
    ``copier_manager.py``, and the test suite continue to work unchanged).

    Args:
        specs: An iterable of ``PluginSpec``-like objects (anything with a
            ``.migrations`` attribute holding ``ServiceMigrationSpec`` items).
            Typed as ``Iterable[object]`` rather than a concrete protocol so
            duck-typed test fakes / future plugin classes pass without
            inheriting from ``PluginSpec``.

    Returns:
        ``{service_name: ServiceMigrationSpec}`` for every migration declared
        across the iterable.
    """
    out: dict[str, ServiceMigrationSpec] = {}
    for spec in specs:
        for migration in getattr(spec, "migrations", None) or []:
            out[migration.service_name] = migration
    return out


__all__ = [
    "AlterTableSpec",
    "CheckConstraintSpec",
    "ColumnSpec",
    "ForeignKeySpec",
    "IndexSpec",
    "MigrationSpec",
    "ServiceMigrationSpec",
    "TableSpec",
    "collect_migrations",
]
