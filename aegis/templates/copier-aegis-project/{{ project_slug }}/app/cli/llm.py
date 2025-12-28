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

app = typer.Typer(help="LLM catalog and model management commands")
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


@app.command()
def sync(
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Mode filter: 'chat', 'embedding', or 'all'",
        ),
    ] = "chat",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Preview changes without modifying the database",
        ),
    ] = False,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            "-r",
            help="Truncate all LLM tables before syncing (full refresh)",
        ),
    ] = False,
) -> None:
    """Sync LLM catalog from OpenRouter and LiteLLM APIs.

    Fetches model data from public APIs and upserts to the local database.
    LiteLLM provides the primary catalog (~2000 models) while OpenRouter
    enriches with descriptions and metadata.
    """
    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be saved[/yellow]\n")

    if refresh and dry_run:
        console.print(
            "[yellow]Refresh requested - would truncate all LLM tables[/yellow]\n"
        )

    start_time = time.time()

    with (
        suppress_logs(),
        console.status(f"[bold green]Syncing LLM catalog (mode={mode})..."),
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
            sync_llm_catalog(session, mode=mode, dry_run=dry_run)
        )

    duration = time.time() - start_time
    _display_sync_result(result, dry_run, duration)


@app.command()
def status() -> None:
    """Show LLM catalog statistics.

    Displays counts of vendors, models, deployments, and prices
    currently in the database.
    """
    with Session(engine) as session:
        stats: CatalogStats = get_catalog_stats(session)

    _display_catalog_stats(stats)


@app.command()
def vendors() -> None:
    """List all LLM vendors in the catalog.

    Shows each vendor with their model count, sorted alphabetically.
    """
    results = list_vendors()

    if not results:
        console.print("[yellow]No vendors found. Run 'llm sync' first.[/yellow]")
        return

    table = Table(title=f"LLM Vendors ({len(results)} total)")
    table.add_column("Vendor", style="cyan")
    table.add_column("Models", style="green", justify="right")

    for vendor in results:
        table.add_row(vendor.name, str(vendor.model_count))

    console.print(table)


@app.command()
def modalities() -> None:
    """List all modalities in the catalog.

    Shows each modality with counts of models supporting it.
    """
    results = list_modalities()

    if not results:
        console.print("[yellow]No modalities found. Run 'llm sync' first.[/yellow]")
        return

    table = Table(title=f"LLM Modalities ({len(results)} total)")
    table.add_column("Modality", style="cyan")
    table.add_column("Models", style="green", justify="right")

    for item in results:
        table.add_row(item.modality, str(item.model_count))

    console.print(table)


@app.command("list")
async def list_cmd(
    ctx: typer.Context,
    pattern: Annotated[
        str | None,
        typer.Argument(
            help="Search pattern for model ID or title (case-insensitive)",
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
            help="Maximum number of results",
        ),
    ] = 50,
    include_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Include disabled models",
        ),
    ] = False,
) -> None:
    """List LLM models from catalog.

    Search for models by pattern or filter by vendor/modality.
    At least one search pattern or filter is required.

    \b
    Examples:
        llm list claude
        llm list gpt-4 --vendor openai
        llm list --vendor anthropic
        llm list --modality image
    """
    if not pattern and not vendor and not modality:
        console.print(ctx.get_help())
        console.print()
        console.print("[red]Error:[/red] Please provide a search pattern or filter.")
        raise typer.Exit(2)

    results = await list_models(
        pattern=pattern,
        vendor=vendor,
        modality=modality,
        limit=limit,
        include_disabled=include_all,
    )

    if not results:
        console.print("[yellow]No models found matching your criteria.[/yellow]")
        return

    table = Table(title=f"LLM Models ({len(results)} results)")
    table.add_column("Model ID", style="cyan", no_wrap=True)
    table.add_column("Vendor", style="green")
    table.add_column("Context", justify="right")
    table.add_column("Input $/1M", justify="right")
    table.add_column("Output $/1M", justify="right")
    table.add_column("Released", justify="right")

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


@app.command()
async def current() -> None:
    """Show current LLM configuration.

    Displays the active provider, model, and settings from .env,
    enriched with catalog data if available.
    """
    config = await get_current_config()

    # Build tree for configuration
    tree = Tree("[bold]Current LLM Configuration[/bold]")
    tree.add(f"Provider: [cyan]{config.provider}[/cyan]")
    tree.add(f"Model: [cyan]{config.model}[/cyan]")
    tree.add(f"Temperature: [green]{config.temperature}[/green]")
    tree.add(f"Max Tokens: [green]{config.max_tokens:,}[/green]")

    console.print(tree)
    console.print()

    # Show catalog enrichment if available
    if config.context_window:
        catalog_tree = Tree("[bold]Model Details (from catalog)[/bold]")
        catalog_tree.add(f"Context Window: [green]{config.context_window:,}[/green]")

        if config.input_price is not None:
            catalog_tree.add(
                f"Input Price: [green]${config.input_price:.2f}[/green] / 1M tokens"
            )

        if config.output_price is not None:
            catalog_tree.add(
                f"Output Price: [green]${config.output_price:.2f}[/green] / 1M tokens"
            )

        if config.modalities:
            catalog_tree.add(
                f"Modalities: [green]{', '.join(config.modalities)}[/green]"
            )

        console.print(catalog_tree)
    else:
        console.print(
            "[dim]Model not found in catalog. Run 'llm sync' to populate.[/dim]"
        )


@app.command()
async def use(
    model_id: Annotated[
        str,
        typer.Argument(
            help="Model ID to set as active (e.g., gpt-4o, claude-sonnet-4-20250514)",
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip catalog validation and allow any model string",
        ),
    ] = False,
) -> None:
    """Switch to a different LLM model.

    Updates AI_MODEL in .env. If the model belongs to a different vendor
    and current provider is not 'public', also updates AI_PROVIDER.

    Examples:
        llm use gpt-4o
        llm use claude-sonnet-4-20250514
        llm use my-custom-model --force
    """
    with console.status(f"[bold green]Switching to {model_id}..."):
        result = await set_active_model(model_id, force=force)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
        if result.vendor:
            console.print(f"  Vendor: [cyan]{result.vendor}[/cyan]")
    else:
        console.print(f"[red]✗[/red] {result.message}")
        raise typer.Exit(1)


@app.command()
async def info(
    model_id: Annotated[
        str,
        typer.Argument(
            help="Model ID to get information about",
        ),
    ],
) -> None:
    """Show detailed information about a specific LLM model.

    Displays full model details from the catalog including pricing,
    capabilities, and metadata.

    Examples:
        llm info gpt-4o
        llm info claude-sonnet-4-20250514
    """
    details = await get_model_info(model_id)

    if not details:
        console.print(
            f"[red]Error:[/red] Model '{model_id}' not found in catalog.\n"
            "Run 'llm sync' to populate the catalog."
        )
        raise typer.Exit(1)

    # Build info panel
    info_lines = [
        f"[bold cyan]{details.title}[/bold cyan]",
        "",
        f"[dim]Model ID:[/dim] {details.model_id}",
        f"[dim]Vendor:[/dim] {details.vendor}",
    ]

    if details.description:
        info_lines.append(f"[dim]Description:[/dim] {details.description}")

    info_lines.extend(
        [
            "",
            f"[dim]Context Window:[/dim] {details.context_window:,} tokens",
            f"[dim]Streamable:[/dim] {'Yes' if details.streamable else 'No'}",
            f"[dim]Enabled:[/dim] {'Yes' if details.enabled else 'No'}",
        ]
    )

    if details.released_on:
        info_lines.append(f"[dim]Released:[/dim] {details.released_on[:10]}")

    info_lines.append("")

    if details.input_price is not None or details.output_price is not None:
        info_lines.append("[bold]Pricing (per 1M tokens)[/bold]")
        if details.input_price is not None:
            info_lines.append(f"  Input: ${details.input_price:.2f}")
        if details.output_price is not None:
            info_lines.append(f"  Output: ${details.output_price:.2f}")
        info_lines.append("")

    if details.modalities:
        info_lines.append(f"[dim]Modalities:[/dim] {', '.join(details.modalities)}")

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
    summary_table = Table(title="LLM Catalog Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green", justify="right")

    summary_table.add_row("Vendors", str(stats.vendor_count))
    summary_table.add_row("Models", str(stats.model_count))
    summary_table.add_row("Deployments", str(stats.deployment_count))
    summary_table.add_row("Prices", str(stats.price_count))

    console.print(summary_table)
    console.print()

    # Top vendors table
    if stats.top_vendors:
        vendor_table = Table(title="Top Vendors by Model Count")
        vendor_table.add_column("Vendor", style="cyan")
        vendor_table.add_column("Models", style="green", justify="right")

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
    title = "Sync Results (Dry Run)" if dry_run else "Sync Results"
    table = Table(title=title)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")

    table.add_row("Vendors Added", str(result.vendors_added))
    table.add_row("Vendors Updated", str(result.vendors_updated))
    table.add_row("Models Added", str(result.models_added))
    table.add_row("Models Updated", str(result.models_updated))
    table.add_row("Deployments Synced", str(result.deployments_synced))
    table.add_row("Prices Synced", str(result.prices_synced))
    table.add_row("Modalities Synced", str(result.modalities_synced))
    table.add_row("Duration", f"{duration:.2f}s")

    if result.errors:
        table.add_row("Errors", f"[red]{len(result.errors)}[/red]")

    console.print(table)

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors[:10]:  # Show first 10 errors
            console.print(f"  • {error}")
        if len(result.errors) > 10:
            console.print(f"  ... and {len(result.errors) - 10} more")
