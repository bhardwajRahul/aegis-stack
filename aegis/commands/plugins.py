"""
``aegis plugins`` CLI commands (#769).

Inspection surface for the plugin system. Built on ``discover_plugins``
(#768) and ``check_compat`` (this PR), so the same metadata declared on
every ``PluginSpec`` (R1-R4-A) renders into a useful pre-flight tool —
not just a passive list of names.

Commands:

* ``aegis plugins list``   tabular view of in-tree + external plugins,
                            with per-row compat status when invoked in
                            an Aegis project (or via ``--project-path``).
* ``aegis plugins info``   detailed view of one plugin: options,
                            migrations, files, CLI surface, and (in a
                            project) what adding it would do.
* ``aegis plugins search``  registry search — stub until #773 ships
                            the official registry.

There is intentionally no ``aegis plugins install``. Putting an external
plugin's bytes on disk is ``pip install aegis-plugin-<name>`` (or ``uv
pip install …``) — wrapping that adds no value, and the meaningful work
of integrating a plugin into a *project* (rendering files, running
migrations, updating answers, wiring config / DI / routes) lives in the
unified ``aegis add`` verb (#771). Project-configuration is the product;
disk-install is a precondition external plugins happen to need.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markup import escape as _escape

from ..core.components import COMPONENTS
from ..core.plugin_compat import CompatStatus, check_compat
from ..core.plugin_discovery import discover_plugin_cli_apps, discover_plugins
from ..core.plugin_spec import PluginKind, PluginSpec
from ..core.services import SERVICES

plugins_app = typer.Typer(
    name="plugins",
    help="Inspect installed Aegis plugins and search the registry",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------


def _all_specs() -> tuple[list[PluginSpec], list[PluginSpec]]:
    """Return ``(in_tree_specs, external_specs)``.

    Both groups are sorted alphabetically by ``spec.name`` so CLI output
    stays deterministic across invocations and across machines (entry-
    point discovery order is install-order-dependent and not stable).
    """
    in_tree = sorted(
        list(SERVICES.values()) + list(COMPONENTS.values()),
        key=lambda s: s.name,
    )
    external = sorted(discover_plugins(), key=lambda s: s.name)
    return in_tree, external


def _resolve_answers(project_path: Path | None) -> dict | None:
    """Load ``.copier-answers.yml`` for the given project, or ``None``.

    Auto-detects a project at the cwd when ``project_path`` is None and
    a ``.copier-answers.yml`` exists there. Otherwise returns ``None``
    (compat checks degrade to ``NOT_IN_PROJECT``).

    Exception handling is narrow: ``FileNotFoundError`` returns ``None``
    silently (the existence check above usually catches this, but
    ``load_copier_answers`` may raise it on race). Genuine read or
    parse failures (``OSError``, ``yaml.YAMLError``) emit a stderr
    warning so the user knows compat checks were skipped — but we
    don't bail with a non-zero exit, since this is an inspection
    command and the rest of the listing is still useful.
    """
    import yaml

    candidate = project_path or Path.cwd()
    answers_file = candidate / ".copier-answers.yml"
    if not answers_file.exists():
        return None
    try:
        from ..core.copier_manager import load_copier_answers

        return load_copier_answers(candidate)
    except FileNotFoundError:
        return None
    except (OSError, yaml.YAMLError) as exc:
        typer.secho(
            f"Could not read {answers_file}: {exc}. Compat checks will be skipped.",
            err=True,
            fg=typer.colors.YELLOW,
        )
        return None


def _status_marker(status: CompatStatus) -> str:
    """Single-character glyph for each compat status."""
    return {
        CompatStatus.IN_TREE: "[green]●[/green]",
        CompatStatus.READY: "[green]✓[/green]",
        CompatStatus.ALREADY_INSTALLED: "[cyan]●[/cyan]",
        CompatStatus.MISSING_COMPONENT: "[yellow]⚠[/yellow]",
        CompatStatus.MISSING_SERVICE: "[yellow]⚠[/yellow]",
        CompatStatus.MISSING_PLUGIN: "[yellow]⚠[/yellow]",
        CompatStatus.CONFLICT: "[red]✗[/red]",
        CompatStatus.NOT_IN_PROJECT: "[dim]·[/dim]",
    }.get(status, "?")


def _kind_label(spec: PluginSpec) -> str:
    return spec.kind.value if isinstance(spec.kind, PluginKind) else str(spec.kind)


def _core_command_reserved_names() -> set[str]:
    """Names already taken by core CLI commands and groups.

    Mirrors the reserved set passed at mount time in
    ``aegis/__main__.py:_mount_plugin_cli_apps`` so that ``aegis plugins
    info``'s ``CLI: yes/no`` indicator matches what would actually
    happen if the plugin's CLI sub-app were mounted. Lazy-imports
    ``aegis.__main__`` to avoid a circular at module load — by the time
    any CLI command runs, ``__main__`` is fully imported.
    """
    from aegis.__main__ import app

    reserved = {cmd.name for cmd in app.registered_commands if cmd.name}
    reserved.update(grp.name for grp in app.registered_groups if grp.name)
    return reserved


# ---------------------------------------------------------------------
# `aegis plugins list`
# ---------------------------------------------------------------------


@plugins_app.command("list")
def plugins_list_command(
    project_path: Path | None = typer.Option(
        None,
        "--project-path",
        "-p",
        help="Project to evaluate compat against (defaults to cwd if "
        "it's an Aegis project).",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show description column."
    ),
) -> None:
    """List installed plugins and their compatibility with this project."""
    from rich.console import Console
    from rich.table import Table

    in_tree, external = _all_specs()
    answers = _resolve_answers(project_path)
    discovered_names = {s.name for s in external}
    console = Console()

    def _add_section(title: str, specs: list[PluginSpec], in_tree_flag: bool) -> None:
        if not specs:
            return
        table = Table(title=title, show_lines=False, expand=False)
        table.add_column("", style="bold", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Kind")
        if verbose:
            table.add_column("Description", overflow="fold")
        table.add_column("Status", overflow="fold")

        for spec in specs:
            report = check_compat(
                spec,
                answers,
                is_in_tree=in_tree_flag,
                discovered_plugin_names=discovered_names,
            )
            # Plugin-supplied strings (name/description/detail) get escaped
            # because Rich treats literal ``[...]`` as markup tags. Status
            # markers are core-controlled and stay raw so their colour
            # markup still applies.
            row = [
                _status_marker(report.status),
                _escape(spec.name),
                _escape(spec.version),
                _escape(_kind_label(spec)),
            ]
            if verbose:
                row.append(_escape(spec.description))
            row.append(_escape(report.detail))
            table.add_row(*row)
        console.print(table)

    _add_section("In-tree (first-party)", in_tree, in_tree_flag=True)
    _add_section("External plugins", external, in_tree_flag=False)

    if not external:
        console.print(
            "\n[dim]No external plugins installed. "
            "Install one with: pip install aegis-plugin-<name>[/dim]"
        )


# ---------------------------------------------------------------------
# `aegis plugins info`
# ---------------------------------------------------------------------


@plugins_app.command("info")
def plugins_info_command(
    name: str = typer.Argument(..., help="Plugin name (e.g. 'auth', 'scraper')"),
    project_path: Path | None = typer.Option(
        None, "--project-path", "-p", help="Project to evaluate compat against."
    ),
) -> None:
    """Show detailed information about a single plugin."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    in_tree, external = _all_specs()

    is_in_tree = False
    spec: PluginSpec | None = None
    for s in in_tree:
        if s.name == name:
            spec, is_in_tree = s, True
            break
    if spec is None:
        for s in external:
            if s.name == name:
                spec = s
                break

    if spec is None:
        console.print(f"[red]No plugin named {name!r} is installed.[/red]")
        all_names = sorted(s.name for s in in_tree + external)
        if all_names:
            console.print(f"[dim]Available: {', '.join(all_names)}[/dim]")
        raise typer.Exit(code=1)

    answers = _resolve_answers(project_path)
    discovered_names = {s.name for s in external}
    report = check_compat(
        spec,
        answers,
        is_in_tree=is_in_tree,
        discovered_plugin_names=discovered_names,
    )

    # Pass the reserved set so the CLI indicator matches mount-time
    # reality: a plugin whose name collides with a core command (init,
    # add, deploy, ...) is filtered out at mount and reported here as
    # "CLI: no" rather than misleading users with "CLI: yes".
    cli_apps = discover_plugin_cli_apps(_core_command_reserved_names())
    has_cli = name in cli_apps

    lines: list[str] = []
    # Plugin-supplied strings (name/description) get escaped so a plugin
    # whose metadata happens to contain ``[brackets]`` doesn't get its
    # name eaten by Rich's markup parser. Core-controlled markup tags
    # (`[bold cyan]`, `[green]`, …) stay raw.
    header = f"[bold cyan]{_escape(spec.name)}[/bold cyan] {_escape(spec.version)}"
    if is_in_tree:
        header += "  [green](first-party)[/green]"
    elif spec.verified:
        header += "  [green](verified)[/green]"
    else:
        header += "  [yellow](community — unverified)[/yellow]"
    lines.append(header)
    lines.append(f"[dim]{_escape(spec.description)}[/dim]")
    lines.append("")
    lines.append(f"  Kind:           {_kind_label(spec)}")
    if spec.type is not None:
        type_value = getattr(spec.type, "value", str(spec.type))
        lines.append(f"  Type:           {type_value}")

    if spec.required_components:
        lines.append(
            f"  Requires comp:  {_escape(', '.join(spec.required_components))}"
        )
    if spec.recommended_components:
        lines.append(
            f"  Recommends:     {_escape(', '.join(spec.recommended_components))}"
        )
    if spec.required_services:
        lines.append(f"  Requires svcs:  {_escape(', '.join(spec.required_services))}")
    if spec.required_plugins:
        lines.append(f"  Requires plug:  {_escape(', '.join(spec.required_plugins))}")
    if spec.conflicts:
        lines.append(f"  Conflicts:      {_escape(', '.join(spec.conflicts))}")
    if spec.pyproject_deps:
        # Module-level _escape import handles deps like
        # ``python-jose[cryptography]==3.3.0`` that contain literal
        # square brackets Rich would otherwise treat as markup.
        deps_preview = ", ".join(_escape(d) for d in spec.pyproject_deps[:5])
        more = (
            f" (+{len(spec.pyproject_deps) - 5} more)"
            if len(spec.pyproject_deps) > 5
            else ""
        )
        lines.append(f"  Python deps:    {deps_preview}{more}")

    lines.append("")
    if spec.options:
        lines.append("[bold]Options[/bold]")
        for opt in spec.options:
            mode = getattr(opt.mode, "value", str(opt.mode))
            choices = _escape(", ".join(opt.choices)) if opt.choices else "—"
            default = (
                _escape(str(opt.default)) if opt.default not in (None, []) else "—"
            )
            auto = " (has auto_requires)" if opt.auto_requires else ""
            lines.append(
                f"  {_escape(opt.name):<10} [{mode:<6}]  choices: {choices}  "
                f"default: {default}{auto}"
            )
        lines.append("")

    file_count = len(spec.files.primary) if spec.files else 0
    migration_count = len(spec.migrations)
    table_count = sum(len(m.tables) for m in spec.migrations)
    lines.append(
        f"  Files: {file_count}   "
        f"Migrations: {migration_count} ({table_count} tables)   "
        f"CLI: {'yes' if has_cli else 'no'}"
    )

    lines.append("")
    lines.append(
        f"[bold]Compat[/bold]  {_status_marker(report.status)} {_escape(report.detail)}"
    )

    console.print(Panel("\n".join(lines), expand=False))


# ---------------------------------------------------------------------
# `aegis plugins update` (#772)
# ---------------------------------------------------------------------


def _installed_plugin_entries(answers: dict) -> list[dict]:
    """Return only dict-shaped entries from ``answers["_plugins"]``.

    Mirrors the normalisation in ``ManualUpdater.add_plugin`` /
    ``remove_plugin`` so update operates on the same view of state.

    Pre-Round-8 ``_plugins`` data could be a list of strings
    (``"scraper>=1.0"``); those entries lack the version + wiring
    payload the update flow needs. We warn the user with a
    re-add hint instead of silently dropping them.
    """
    raw = answers.get("_plugins") or []
    if not isinstance(raw, list):
        return []

    legacy_strings = [item for item in raw if isinstance(item, str)]
    if legacy_strings:
        typer.secho(
            "Skipping legacy string-shaped _plugins entries: "
            f"{', '.join(repr(s) for s in legacy_strings)}. "
            "Re-add them with `aegis add <name>` to upgrade to the "
            "current dict format.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    return [p for p in raw if isinstance(p, dict)]


def _resolve_installed_spec(name: str) -> tuple[PluginSpec, str] | None:
    """Match ``name`` against the currently *installed* plugin set
    (i.e. what ``discover_plugins`` returns post-``pip install -U``).

    Returns ``(spec, module_name)`` if found, else ``None``. The module
    name is required by ``ManualUpdater.add_plugin`` to locate the
    plugin's template tree.
    """
    from importlib.metadata import entry_points

    for plugin in discover_plugins():
        if plugin.name != name:
            continue
        for ep in entry_points(group="aegis.plugins"):
            try:
                loader = ep.load()
                # Mirror ``plugin_discovery._load_plugin_spec``:
                # entry-points may export a factory callable OR a
                # ``PluginSpec`` instance directly. Calling an instance
                # would crash, so branch on ``callable``.
                ep_spec = loader() if callable(loader) else loader
            except Exception:
                continue
            if getattr(ep_spec, "name", None) == plugin.name:
                module_name = ep.value.split(":")[0].split(".")[0]
                return (plugin, module_name)
        # Defensive only — discovery populated this spec from one of
        # the entry points above, so the matched-ep path should always
        # return. If somehow not, ``plugin.name`` is the best guess
        # and template resolution will surface a clear error.
        return (plugin, plugin.name)
    return None


@plugins_app.command("update")
def plugins_update_command(
    plugin_name: str | None = typer.Argument(
        None,
        help="Plugin to update. Required unless --all is given.",
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="Update every plugin currently in this project's ``_plugins``.",
    ),
    project_path: str = typer.Option(
        ".",
        "--project-path",
        "-p",
        help="Path to the Aegis project (default: current directory).",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts."),
) -> None:
    """Re-render an installed plugin's templates at its currently
    pip-installed version.

    Workflow: plugin author publishes a new version of
    ``aegis-plugin-foo`` to PyPI; user runs
    ``pip install -U aegis-plugin-foo`` to pull the new bits onto
    disk; this command re-runs the project-configure step so the
    plugin's updated templates / wiring / migrations land in the
    project tree. Only plugins whose pip-installed version differs
    from the project's recorded version actually re-render.

    The recorded version (``_plugins[i].version``) is updated even
    when nothing visibly changes, so a re-run on identical bits is a
    no-op.
    """
    from ..core.copier_manager import load_copier_answers
    from ..core.manual_updater import ManualUpdater

    if not all_ and not plugin_name:
        typer.secho("Pass a plugin name or use --all.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    if all_ and plugin_name:
        typer.secho(
            "Pass either a plugin name OR --all, not both.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    target_path = Path(project_path).resolve()
    try:
        answers = load_copier_answers(target_path)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e

    installed = _installed_plugin_entries(answers)
    if not installed:
        typer.secho("No plugins are installed in this project.", fg=typer.colors.YELLOW)
        return

    targets: list[dict]
    if all_:
        targets = installed
    else:
        targets = [p for p in installed if p.get("name") == plugin_name]
        if not targets:
            typer.secho(
                f"Plugin {plugin_name!r} is not installed in this project.",
                fg=typer.colors.RED,
                err=True,
            )
            typer.echo(
                "   Use ``aegis plugins list`` to see what's available, "
                "and ``aegis add <name>`` to install."
            )
            raise typer.Exit(1)

    # Check disk vs. recorded version for each target. We touch the
    # ManualUpdater only for plugins whose pip-installed bits actually
    # differ — otherwise the op is a no-op and we say so.
    updated: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    for entry in targets:
        name = entry.get("name", "")
        recorded_version = entry.get("version", "0.0.0")

        resolved = _resolve_installed_spec(name)
        if resolved is None:
            failed.append(
                (
                    name,
                    f"plugin {name!r} is in the project's _plugins list but "
                    f"not currently pip-installed; run "
                    f"``pip install aegis-plugin-{name}`` first.",
                )
            )
            continue

        installed_spec, module_name = resolved
        installed_version = installed_spec.version

        if installed_version == recorded_version:
            skipped.append(f"{name} (already at {installed_version})")
            continue

        typer.echo(
            f"\nUpdating plugin: {name} ({recorded_version} → {installed_version})"
        )
        if not yes and not typer.confirm(f"Apply update to {name!r}?", default=True):
            skipped.append(f"{name} (skipped by user)")
            continue

        updater = ManualUpdater(target_path)
        # ``add_plugin`` is idempotent: a same-named entry replaces
        # the old one, shared files regenerate, plugin templates re-render.
        # That's exactly the update operation.
        result = updater.add_plugin(
            spec=installed_spec,
            plugin_module_name=module_name,
            plugin_options=entry.get("options") or None,
        )
        if result.success:
            updated.append(f"{name} → {installed_version}")
        else:
            failed.append((name, result.error_message or "unknown error"))

    # Summary
    typer.echo()
    if updated:
        typer.secho(f"Updated: {len(updated)}", fg=typer.colors.GREEN)
        for line in updated:
            typer.echo(f"   • {line}")
    if skipped:
        typer.echo(f"Skipped: {len(skipped)}")
        for line in skipped:
            typer.echo(f"   • {line}")
    if failed:
        typer.secho(f"Failed: {len(failed)}", fg=typer.colors.RED, err=True)
        for name, msg in failed:
            typer.secho(f"   • {name}: {msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


# ---------------------------------------------------------------------
# `aegis plugins search`
# ---------------------------------------------------------------------


@plugins_app.command("search")
def plugins_search_command(
    keyword: str = typer.Argument("", help="Optional keyword to search for"),
) -> None:
    """Search the official plugin registry.

    Stub until ticket #773 ships the official registry. Until then,
    plugin authors instruct users to ``pip install aegis-plugin-<name>``
    directly.
    """
    typer.secho(
        "Plugin registry is not yet available (ticket #773).",
        fg=typer.colors.YELLOW,
    )
    typer.echo("For now: pip install aegis-plugin-<name>, then aegis plugins list.")
    if keyword:
        typer.echo(
            f"Once the registry is live, this command will search for {keyword!r}."
        )
