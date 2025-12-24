"""LLM catalog sync CLI commands.

Commands for syncing LLM model data from public APIs (OpenRouter, LiteLLM)
into the local database catalog.
"""

import asyncio
import time
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import Session, delete

from app.core.db import engine
from app.core.log import suppress_logs
from app.services.ai.etl import CatalogStats, SyncResult, get_catalog_stats
from app.services.ai.etl.llm_sync_service import sync_llm_catalog
from app.services.ai.models.llm import (
    LargeLanguageModel,
    LLMDeployment,
    LLMModality,
    LLMPrice,
    LLMVendor,
)

app = typer.Typer(help="LLM catalog synchronization commands")
console = Console()


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
