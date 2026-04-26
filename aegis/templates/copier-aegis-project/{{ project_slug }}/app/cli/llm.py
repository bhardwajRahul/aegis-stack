"""LLM catalog and model management CLI commands.

Commands for syncing LLM model data, listing available models,
viewing current configuration, and switching active models.
"""

import asyncio
import time
from typing import Annotated

import typer
from app.core.db import engine
from app.core.log import suppress_logs
from app.i18n import lazy_t, t
from app.services.ai.etl import CatalogStats, SyncResult, get_catalog_stats
from app.services.ai.etl.llm_sync_service import sync_llm_catalog
from app.services.ai.llm_service import (
    get_current_config,
    get_model_info,
    list_modalities,
    list_models,
    list_vendors,
    set_active_model,
)
from app.services.ai.models.llm import (
    LargeLanguageModel,
    LLMDeployment,
    LLMModality,
    LLMPrice,
    LLMVendor,
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from sqlmodel import Session, delete

app = typer.Typer(help=lazy_t("llm.help"))
console = Console()


def _get_modalities_help() -> str:
    """Get modality help text from database.

    Returns:
        Help text string for the modality option.
    """
    try:
        from sqlmodel import select

        with Session(engine) as session:
            modalities = session.exec(select(LLMModality.modality).distinct()).all()
            if modalities:
                return f"Filter by modality ({', '.join(sorted({str(m) for m in modalities}))})"
    except Exception:
        pass
    return "Filter by modality"


def _get_vendors_help() -> str:
    """Get vendor help text from database.

    Returns:
        Help text string for the vendor option.
    """
    try:
        from sqlmodel import select

        with Session(engine) as session:
            vendors = session.exec(select(LLMVendor.name).distinct()).all()
            if vendors:
                sorted_vendors = sorted({str(v) for v in vendors})
                sample = sorted_vendors[:8]
                if len(sorted_vendors) > 8:
                    return f"Filter by vendor ({', '.join(sample)}, ...)"
                return f"Filter by vendor ({', '.join(sample)})"
    except Exception:
        pass
    return "Filter by vendor name"


@app.command(help=lazy_t("llm.help_sync"))
def sync(
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help=lazy_t("llm.opt_mode"),
        ),
    ] = "chat",
    source: Annotated[
        str,
        typer.Option(
            "--source",
            "-s",
            help=lazy_t("llm.opt_source"),
        ),
    ] = "cloud",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help=lazy_t("llm.opt_dry_run"),
        ),
    ] = False,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            "-r",
            help=lazy_t("llm.opt_refresh"),
        ),
    ] = False,
) -> None:
    if dry_run:
        console.print(f"[yellow]{t('llm.dry_run_mode')}[/yellow]\n")

    if refresh and dry_run:
        console.print(f"[yellow]{t('llm.refresh_dry_run')}[/yellow]\n")

    start_time = time.time()

    # Build status message based on source
    if source == "ollama":
        status_msg = f"[bold green]{t('llm.syncing_ollama')}..."
    elif source == "all":
        status_msg = f"[bold green]{t('llm.syncing_catalog_all', mode=mode)}..."
    else:
        status_msg = f"[bold green]{t('llm.syncing_catalog', mode=mode)}..."

    with (
        suppress_logs(),
        console.status(status_msg),
        Session(engine) as session,
    ):
        if refresh and not dry_run:
            # Truncate catalog tables in reverse FK dependency order
            # Note: LLMUsage is operational data, not catalog - preserved
            session.exec(delete(LLMModality))
            session.exec(delete(LLMPrice))
            session.exec(delete(LLMDeployment))
            session.exec(delete(LargeLanguageModel))
            session.exec(delete(LLMVendor))
            session.commit()

        result: SyncResult = asyncio.run(
            sync_llm_catalog(session, mode=mode, source=source, dry_run=dry_run)
        )

    duration = time.time() - start_time
    _display_sync_result(result, dry_run, duration)


@app.command(help=lazy_t("llm.help_status"))
def status() -> None:
    with Session(engine) as session:
        stats: CatalogStats = get_catalog_stats(session)

    _display_catalog_stats(stats)


@app.command(help=lazy_t("llm.help_vendors"))
def vendors() -> None:
    results = list_vendors()

    if not results:
        console.print(f"[yellow]{t('llm.no_vendors')}[/yellow]")
        return

    table = Table(title=t("llm.vendors_title", count=len(results)))
    table.add_column(t("llm.vendor_column"), style="cyan")
    table.add_column(t("llm.models_column"), style="green", justify="right")

    for vendor in results:
        table.add_row(vendor.name, str(vendor.model_count))

    console.print(table)


@app.command(help=lazy_t("llm.help_modalities"))
def modalities() -> None:
    results = list_modalities()

    if not results:
        console.print(f"[yellow]{t('llm.no_modalities')}[/yellow]")
        return

    table = Table(title=t("llm.modalities_title", count=len(results)))
    table.add_column(t("llm.modality_column"), style="cyan")
    table.add_column(t("llm.models_column"), style="green", justify="right")

    for item in results:
        table.add_row(item.modality, str(item.model_count))

    console.print(table)


@app.command("list", help=lazy_t("llm.help_list"))
async def list_cmd(
    ctx: typer.Context,
    pattern: Annotated[
        str | None,
        typer.Argument(
            help=lazy_t("llm.arg_pattern"),
        ),
    ] = None,
    vendor: Annotated[
        str | None,
        typer.Option(
            "--vendor",
            "-v",
            help=_get_vendors_help(),
        ),
    ] = None,
    modality: Annotated[
        str | None,
        typer.Option(
            "--modality",
            "-m",
            help=_get_modalities_help(),
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help=lazy_t("llm.opt_limit"),
        ),
    ] = 50,
    include_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help=lazy_t("llm.opt_all"),
        ),
    ] = False,
) -> None:
    if not pattern and not vendor and not modality:
        console.print(ctx.get_help())
        console.print()
        console.print(f"[red]{t('shared.error')}[/red] {t('llm.provide_filter')}")
        raise typer.Exit(2)

    results = await list_models(
        pattern=pattern,
        vendor=vendor,
        modality=modality,
        limit=limit,
        include_disabled=include_all,
    )

    if not results:
        console.print(f"[yellow]{t('llm.no_models_found')}[/yellow]")
        return

    table = Table(title=t("llm.models_title", count=len(results)))
    table.add_column(t("llm.model_id_column"), style="cyan", no_wrap=True)
    table.add_column(t("llm.vendor_column"), style="green")
    table.add_column(t("llm.context_column"), justify="right")
    table.add_column(t("llm.input_price_column"), justify="right")
    table.add_column(t("llm.output_price_column"), justify="right")
    table.add_column(t("llm.released_column"), justify="right")

    for model in results:
        table.add_row(
            model.model_id,
            model.vendor,
            f"{model.context_window:,}",
            f"${model.input_price:.2f}" if model.input_price else "-",
            f"${model.output_price:.2f}" if model.output_price else "-",
            model.released_on or "-",
        )

    console.print(table)


@app.command(help=lazy_t("llm.help_current"))
async def current() -> None:
    config = await get_current_config()

    # Build tree for configuration
    tree = Tree(f"[bold]{t('llm.current_config')}[/bold]")
    tree.add(f"{t('llm.provider_label')} [cyan]{config.provider}[/cyan]")
    tree.add(f"{t('llm.model_label')} [cyan]{config.model}[/cyan]")
    tree.add(f"{t('llm.temperature_label')} [green]{config.temperature}[/green]")
    tree.add(f"{t('llm.max_tokens_label')} [green]{config.max_tokens:,}[/green]")

    console.print(tree)
    console.print()

    # Show catalog enrichment if available
    if config.context_window:
        catalog_tree = Tree(f"[bold]{t('llm.model_details')}[/bold]")
        catalog_tree.add(
            f"{t('llm.context_window_label')} [green]{config.context_window:,}[/green]"
        )

        if config.input_price is not None:
            catalog_tree.add(
                f"{t('llm.input_price_label')} [green]${config.input_price:.2f}[/green] {t('llm.per_million_tokens')}"
            )

        if config.output_price is not None:
            catalog_tree.add(
                f"{t('llm.output_price_label')} [green]${config.output_price:.2f}[/green] {t('llm.per_million_tokens')}"
            )

        if config.modalities:
            catalog_tree.add(
                f"{t('llm.modalities_label')} [green]{', '.join(config.modalities)}[/green]"
            )

        console.print(catalog_tree)
    else:
        console.print(f"[dim]{t('llm.model_not_in_catalog')}[/dim]")


@app.command(help=lazy_t("llm.help_use"))
async def use(
    model_id: Annotated[
        str,
        typer.Argument(
            help=lazy_t("llm.arg_model_id_use"),
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help=lazy_t("llm.opt_force"),
        ),
    ] = False,
) -> None:
    with console.status(
        f"[bold green]{t('llm.switching_model', model_id=model_id)}..."
    ):
        result = await set_active_model(model_id, force=force)

    if result.success:
        console.print(f"[green]\u2713[/green] {result.message}")
        if result.vendor:
            console.print(f"  {t('llm.vendor_label')} [cyan]{result.vendor}[/cyan]")
    else:
        console.print(f"[red]\u2717[/red] {result.message}")
        raise typer.Exit(1)


@app.command(help=lazy_t("llm.help_info"))
async def info(
    model_id: Annotated[
        str,
        typer.Argument(
            help=lazy_t("llm.arg_model_id_info"),
        ),
    ],
) -> None:
    details = await get_model_info(model_id)

    if not details:
        console.print(
            f"[red]{t('shared.error')}[/red] {t('llm.model_not_found', model_id=model_id)}\n"
            f"{t('llm.run_sync_hint')}"
        )
        raise typer.Exit(1)

    # Build info panel
    info_lines = [
        f"[bold cyan]{details.title}[/bold cyan]",
        "",
        f"[dim]{t('llm.model_id_label')}[/dim] {details.model_id}",
        f"[dim]{t('llm.vendor_label')}[/dim] {details.vendor}",
    ]

    if details.description:
        info_lines.append(
            f"[dim]{t('llm.description_label')}[/dim] {details.description}"
        )

    info_lines.extend(
        [
            "",
            f"[dim]{t('llm.context_window_label')}[/dim] {details.context_window:,} {t('llm.tokens_unit')}",
            f"[dim]{t('llm.streamable_label')}[/dim] {t('shared.yes') if details.streamable else t('shared.no')}",
            f"[dim]{t('llm.enabled_label')}[/dim] {t('shared.yes') if details.enabled else t('shared.no')}",
        ]
    )

    if details.released_on:
        info_lines.append(
            f"[dim]{t('llm.released_label')}[/dim] {details.released_on[:10]}"
        )

    info_lines.append("")

    if details.input_price is not None or details.output_price is not None:
        info_lines.append(f"[bold]{t('llm.pricing_header')}[/bold]")
        if details.input_price is not None:
            info_lines.append(f"  {t('llm.input_label')} ${details.input_price:.2f}")
        if details.output_price is not None:
            info_lines.append(f"  {t('llm.output_label')} ${details.output_price:.2f}")
        info_lines.append("")

    if details.modalities:
        info_lines.append(
            f"[dim]{t('llm.modalities_label')}[/dim] {', '.join(details.modalities)}"
        )

    panel = Panel(
        "\n".join(info_lines),
        title=f"[bold]{model_id}[/bold]",
        border_style="cyan",
    )
    console.print(panel)


def _display_catalog_stats(stats: CatalogStats) -> None:
    """Display catalog statistics in formatted tables.

    Args:
        stats: The catalog stats to display.
    """
    # Summary table
    summary_table = Table(title=t("llm.catalog_summary"))
    summary_table.add_column(t("llm.metric_column"), style="cyan")
    summary_table.add_column(t("llm.count_column"), style="green", justify="right")

    summary_table.add_row(t("llm.vendors_row"), str(stats.vendor_count))
    summary_table.add_row(t("llm.models_row"), str(stats.model_count))
    summary_table.add_row(t("llm.deployments_row"), str(stats.deployment_count))
    summary_table.add_row(t("llm.prices_row"), str(stats.price_count))

    console.print(summary_table)
    console.print()

    # Top vendors table
    if stats.top_vendors:
        vendor_table = Table(title=t("llm.top_vendors"))
        vendor_table.add_column(t("llm.vendor_column"), style="cyan")
        vendor_table.add_column(t("llm.models_column"), style="green", justify="right")

        for vendor_name, count in stats.top_vendors:
            vendor_table.add_row(vendor_name, str(count))

        console.print(vendor_table)


def _display_sync_result(result: SyncResult, dry_run: bool, duration: float) -> None:
    """Display sync results in a formatted table.

    Args:
        result: The sync result to display.
        dry_run: Whether this was a dry run.
        duration: How long the sync took in seconds.
    """
    title = t("llm.sync_results_dry_run") if dry_run else t("llm.sync_results")
    table = Table(title=title)
    table.add_column(t("llm.metric_column"), style="cyan")
    table.add_column(t("llm.count_column"), style="green", justify="right")

    table.add_row(t("llm.vendors_added"), str(result.vendors_added))
    table.add_row(t("llm.vendors_updated"), str(result.vendors_updated))
    table.add_row(t("llm.models_added"), str(result.models_added))
    table.add_row(t("llm.models_updated"), str(result.models_updated))
    table.add_row(t("llm.deployments_synced"), str(result.deployments_synced))
    table.add_row(t("llm.prices_synced"), str(result.prices_synced))
    table.add_row(t("llm.modalities_synced"), str(result.modalities_synced))
    table.add_row(t("llm.duration_row"), f"{duration:.2f}s")

    if result.errors:
        table.add_row(t("llm.errors_row"), f"[red]{len(result.errors)}[/red]")

    console.print(table)

    if result.errors:
        console.print(f"\n[red]{t('llm.errors_header')}[/red]")
        for error in result.errors[:10]:  # Show first 10 errors
            console.print(f"  \u2022 {error}")
        if len(result.errors) > 10:
            console.print(
                f"  {t('llm.and_more_errors', count=len(result.errors) - 10)}"
            )
