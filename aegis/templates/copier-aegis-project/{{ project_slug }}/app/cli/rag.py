"""
RAG (Retrieval-Augmented Generation) CLI commands.

Provides commands for indexing documents, searching collections,
and managing vector store collections.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from app.core.config import settings
from app.core.log import suppress_logs
from app.i18n import lazy_t, t
from app.services.rag.config import get_rag_config
from app.services.rag.service import RAGService
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

app = typer.Typer(help=lazy_t("rag.help"))
console = Console()


def get_rag_service() -> RAGService:
    """Get RAG service instance."""
    config = get_rag_config(settings)
    return RAGService(config)


def format_duration(ms: float) -> str:
    """Format milliseconds into human-readable duration."""
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"


def _get_model_cache_path() -> Path:
    """Get the path where embedding model would be cached."""
    if settings.RAG_MODEL_CACHE_DIR:
        return Path(settings.RAG_MODEL_CACHE_DIR)
    # Default HuggingFace cache location
    return Path.home() / ".cache" / "huggingface" / "hub"


def _is_model_cached() -> bool:
    """Check if the embedding model is already downloaded."""
    model_name = settings.RAG_EMBEDDING_MODEL
    cache_path = _get_model_cache_path()

    # sentence-transformers caches models in hub/models--{org}--{model}
    model_dir_name = f"models--{model_name.replace('/', '--')}"
    model_path = cache_path / model_dir_name

    # Check if model directory exists and has content
    return model_path.exists() and any(model_path.iterdir())


def _ensure_model_ready() -> None:
    """Check if model/API is ready, download local model if needed."""
    # OpenAI embeddings don't require local model
    if settings.RAG_EMBEDDING_PROVIDER == "openai":
        # Early validation: check API key is configured
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            console.print()
            console.print(f"[red]{t('rag.openai_key_missing')}[/red]")
            console.print(f"[dim]{t('rag.openai_key_hint')}[/dim]")
            raise typer.Exit(code=1)
        return

    # sentence-transformers: check cache and download if needed
    if _is_model_cached():
        return

    model_name = settings.RAG_EMBEDDING_MODEL
    cache_dir = settings.RAG_MODEL_CACHE_DIR

    console.print()
    console.print(f"[yellow]{t('rag.model_not_found')}[/yellow]")
    console.print(f"[dim]{t('rag.model_info', model=model_name)}[/dim]")
    console.print()

    try:
        from sentence_transformers import SentenceTransformer

        console.print(f"[bold cyan]{t('rag.downloading_model')}[/bold cyan]")
        console.print()  # Blank line before tqdm progress bars

        if cache_dir:
            SentenceTransformer(model_name, cache_folder=cache_dir)
        else:
            SentenceTransformer(model_name)

        console.print()  # Blank line after progress bars
        console.print(f"[green]{t('rag.model_downloaded')}[/green]")
        console.print()
    except Exception as e:
        console.print(f"[red]{t('rag.model_download_failed', error=e)}[/red]")
        console.print(f"[dim]{t('rag.model_download_hint')}[/dim]")
        raise typer.Exit(code=1)


@app.command("index", help=lazy_t("rag.help_index"))
def index_documents(
    path: Annotated[
        str,
        typer.Argument(help=lazy_t("rag.arg_path")),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help=lazy_t("rag.opt_collection")),
    ] = "default",
    extensions: Annotated[
        str | None,
        typer.Option("--extensions", "-e", help=lazy_t("rag.opt_extensions")),
    ] = None,
) -> None:
    # Ensure embedding model is available (download if needed)
    if settings.RAG_EMBEDDING_PROVIDER == "sentence-transformers":
        _ensure_model_ready()

    rag_service = get_rag_service()

    # Parse extensions
    ext_list = None
    if extensions:
        ext_list = [e.strip() for e in extensions.split(",")]
        # Ensure extensions start with dot
        ext_list = [e if e.startswith(".") else f".{e}" for e in ext_list]

    console.print(f"\n[bold blue]{t('rag.indexing_label')}[/bold blue] {path}")
    console.print(f"[bold blue]{t('rag.collection_label')}[/bold blue] {collection}")
    if ext_list:
        console.print(
            f"[bold blue]{t('rag.extensions_label')}[/bold blue] {', '.join(ext_list)}"
        )
    console.print()

    try:
        with (
            suppress_logs(),
            Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("[cyan]{task.fields[status]}"),
                console=console,
            ) as progress,
        ):
            task = progress.add_task(
                t("rag.indexing_progress"),
                total=None,
                status=t("rag.loading_documents"),
            )

            def on_progress(batch: int, total: int, chunks: int) -> None:
                progress.update(
                    task,
                    total=total,
                    completed=batch,
                    status=t(
                        "rag.batch_progress", batch=batch, total=total, chunks=chunks
                    ),
                )

            stats = asyncio.run(
                rag_service.refresh_index(
                    path=Path(path),
                    collection_name=collection,
                    extensions=ext_list,
                    progress_callback=on_progress,
                )
            )

        # Calculate total duration and stats
        total_ms = stats.load_ms + stats.chunk_ms + stats.duration_ms
        total_str = format_duration(total_ms)
        chunks_per_sec = (
            stats.documents_added / (total_ms / 1000) if total_ms > 0 else 0
        )

        # Calculate phase percentages
        def pct(phase_ms: float) -> str:
            if total_ms <= 0:
                return "0%"
            return f"{(phase_ms / total_ms) * 100:.0f}%"

        # Format extensions for display
        ext_display = (
            ", ".join(stats.extensions) if stats.extensions else t("shared.none")
        )

        # Display results with phase breakdown
        console.print(
            Panel(
                f"[green]{t('rag.index_success', chunks=f'{stats.documents_added:,}', files=f'{stats.source_files:,}')}[/green]\n\n"
                f"[bold]{t('rag.extensions_label')}[/bold] {ext_display}\n"
                f"[bold]{t('rag.duration_label')}[/bold] {total_str}\n"
                f"  [dim]{t('rag.loading_phase')}[/dim]  {format_duration(stats.load_ms)} ({pct(stats.load_ms)})\n"
                f"  [dim]{t('rag.chunking_phase')}[/dim] {format_duration(stats.chunk_ms)} ({pct(stats.chunk_ms)})\n"
                f"  [dim]{t('rag.indexing_phase')}[/dim] {format_duration(stats.duration_ms)} ({pct(stats.duration_ms)})\n"
                f"[bold]{t('rag.throughput_label')}[/bold] {chunks_per_sec:.1f} {t('rag.chunks_per_sec')}\n"
                f"[bold]{t('rag.collection_size_label')}[/bold] {stats.total_documents:,} {t('rag.chunks_unit')}",
                title=f"{t('rag.collection_title')}: {collection}",
                border_style="green",
            )
        )

    except FileNotFoundError as e:
        console.print(
            f"[bold red]{t('shared.error')}[/bold red] {t('rag.path_not_found', path=getattr(e, 'filename', str(e)))}"
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("add", help=lazy_t("rag.help_add"))
def add_file(
    path: Annotated[
        str,
        typer.Argument(help=lazy_t("rag.arg_file_path")),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help=lazy_t("rag.opt_collection")),
    ] = "default",
    show_ids: Annotated[
        bool,
        typer.Option("--show-ids", help=lazy_t("rag.opt_show_ids")),
    ] = False,
) -> None:
    # Ensure embedding model is available (download if needed)
    if settings.RAG_EMBEDDING_PROVIDER == "sentence-transformers":
        _ensure_model_ready()

    rag_service = get_rag_service()

    console.print(f"\n[bold blue]{t('rag.adding_label')}[/bold blue] {path}")
    console.print(f"[bold blue]{t('rag.collection_label')}[/bold blue] {collection}")
    console.print()

    try:
        result = asyncio.run(
            rag_service.add_file(
                path=Path(path),
                collection_name=collection,
            )
        )

        # Display result
        file_name = Path(result.file_path).name
        output = (
            f"[green]{t('rag.added_updated')}[/green] {file_name}\n"
            f"{t('rag.chunks_label')} {result.chunk_count}\n"
            f"{t('rag.hash_label')} {result.file_hash}"
        )

        if show_ids and result.chunk_ids:
            output += f"\n{t('rag.ids_label')} {', '.join(result.chunk_ids)}"

        console.print(
            Panel(
                output,
                title=f"{t('rag.collection_title')}: {collection}",
                border_style="green",
            )
        )

    except FileNotFoundError as e:
        console.print(
            f"[bold red]{t('shared.error')}[/bold red] {t('rag.file_not_found', path=e)}"
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("remove", help=lazy_t("rag.help_remove"))
def remove_file(
    source_path: Annotated[
        str,
        typer.Argument(help=lazy_t("rag.arg_source_path")),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help=lazy_t("rag.opt_collection")),
    ] = "default",
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help=lazy_t("rag.opt_force")),
    ] = False,
) -> None:
    rag_service = get_rag_service()

    # Confirm deletion
    if not force:
        confirm = typer.confirm(
            t("rag.confirm_remove", source=source_path, collection=collection)
        )
        if not confirm:
            console.print(f"[yellow]{t('shared.cancelled')}[/yellow]")
            return

    try:
        result = asyncio.run(
            rag_service.remove_file(
                source_path=source_path,
                collection_name=collection,
            )
        )

        if result.chunk_count > 0:
            console.print(
                f"[green]{t('rag.removed_chunks', count=result.chunk_count)}[/green] {source_path}"
            )
        else:
            console.print(f"[yellow]{t('rag.no_chunks_found')}[/yellow] {source_path}")
            console.print(f"[dim]{t('rag.files_hint')}[/dim]")

    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("files", help=lazy_t("rag.help_files"))
def list_files(
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help=lazy_t("rag.opt_collection")),
    ] = "default",
) -> None:
    rag_service = get_rag_service()

    try:
        files = asyncio.run(rag_service.list_files(collection_name=collection))

        if not files:
            console.print(
                f"[yellow]{t('rag.no_files_in_collection')}[/yellow] {collection}"
            )
            console.print(f"\n[dim]{t('rag.index_hint')}[/dim]")
            return

        # Create table
        table = Table(
            title=t("rag.indexed_files_title", collection=collection),
            show_header=True,
        )
        table.add_column(t("rag.file_column"), style="cyan")
        table.add_column(t("rag.chunks_column"), justify="right", style="green")

        total_chunks = 0
        for file in files:
            table.add_row(file.source, str(file.chunks))
            total_chunks += file.chunks

        console.print()
        console.print(table)
        console.print(
            f"\n[bold]{t('rag.total_label')}[/bold] {t('rag.files_and_chunks', files=len(files), chunks=total_chunks)}"
        )
        console.print()

    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("search", help=lazy_t("rag.help_search"))
def search_documents(
    query: Annotated[
        str,
        typer.Argument(help=lazy_t("rag.arg_query")),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help=lazy_t("rag.opt_collection_search")),
    ] = "default",
    top_k: Annotated[
        int,
        typer.Option("--top-k", "-k", help=lazy_t("rag.opt_top_k")),
    ] = 5,
    show_content: Annotated[
        bool,
        typer.Option("--content", help=lazy_t("rag.opt_content")),
    ] = False,
) -> None:
    # Ensure embedding model is available (download if needed)
    if settings.RAG_EMBEDDING_PROVIDER == "sentence-transformers":
        _ensure_model_ready()

    rag_service = get_rag_service()

    console.print(f"\n[bold blue]{t('rag.searching_label')}[/bold blue] {query}")
    console.print(f"[bold blue]{t('rag.collection_label')}[/bold blue] {collection}")
    console.print()

    try:
        results = asyncio.run(
            rag_service.search(
                query=query,
                collection_name=collection,
                top_k=top_k,
            )
        )

        if not results:
            console.print(f"[yellow]{t('rag.no_results')}[/yellow]")
            console.print(f"\n[dim]{t('rag.search_hint')}[/dim]")
            return

        # Display results
        console.print(f"[green]{t('rag.found_results', count=len(results))}[/green]\n")

        for result in results:
            source = result.metadata.get("source", t("shared.unknown"))
            file_name = result.metadata.get("file_name", Path(source).name)
            score = result.score

            # Create panel for each result
            if show_content:
                content = result.content
                if len(content) > 500:
                    content = content[:500] + "..."
                panel_content = (
                    f"[dim]{t('rag.score_label')} {score:.4f}[/dim]\n\n{content}"
                )
            else:
                preview = result.content[:200].replace("\n", " ")
                if len(result.content) > 200:
                    preview += "..."
                panel_content = (
                    f"[dim]{t('rag.score_label')} {score:.4f}[/dim]\n\n{preview}"
                )

            console.print(
                Panel(
                    panel_content,
                    title=f"[bold]#{result.rank}[/bold] {file_name}",
                    subtitle=f"[dim]{source}[/dim]",
                    border_style="blue",
                )
            )
            console.print()

    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("list", help=lazy_t("rag.help_list"))
def list_collections() -> None:
    rag_service = get_rag_service()

    try:
        collections = asyncio.run(rag_service.list_collections())

        if not collections:
            console.print(f"[yellow]{t('rag.no_collections')}[/yellow]")
            console.print(f"\n[dim]{t('rag.create_collection_hint')}[/dim]")
            return

        # Create table
        table = Table(title=t("rag.collections_title"), show_header=True)
        table.add_column(t("rag.collection_column"), style="cyan")
        table.add_column(t("rag.documents_column"), justify="right", style="green")

        for name in collections:
            stats = asyncio.run(rag_service.get_collection_stats(name))
            count = stats.get("count", 0) if stats else 0
            table.add_row(name, str(count))

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("delete", help=lazy_t("rag.help_delete"))
def delete_collection(
    collection: Annotated[
        str,
        typer.Argument(help=lazy_t("rag.arg_collection")),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help=lazy_t("rag.opt_force")),
    ] = False,
) -> None:
    rag_service = get_rag_service()

    # Confirm deletion
    if not force:
        confirm = typer.confirm(t("rag.confirm_delete", collection=collection))
        if not confirm:
            console.print(f"[yellow]{t('shared.cancelled')}[/yellow]")
            return

    try:
        deleted = asyncio.run(rag_service.delete_collection(collection))

        if deleted:
            console.print(f"[green]{t('rag.deleted_collection')}[/green] {collection}")
        else:
            console.print(
                f"[yellow]{t('rag.collection_not_found')}[/yellow] {collection}"
            )

    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("status", help=lazy_t("rag.help_status"))
def show_status() -> None:
    rag_service = get_rag_service()

    try:
        status = rag_service.get_service_status()
        collections = asyncio.run(rag_service.list_collections())

        # Check if embedding model is installed
        model_cached = _is_model_cached()
        if model_cached:
            model_status = f"[green]{t('rag.model_installed')}[/green]"
        else:
            model_status = f"[yellow]{t('rag.model_not_installed')}[/yellow] [dim]({t('rag.run_install_model')})[/dim]"

        # Create status panel
        yes_no = t("shared.yes") if status.get("enabled") else t("shared.no")
        status_lines = [
            f"[bold]{t('rag.enabled_label')}[/bold] {yes_no}",
            f"[bold]{t('rag.persist_dir_label')}[/bold] {status.get('persist_directory')}",
            f"[bold]{t('rag.embedding_model_label')}[/bold] {status.get('embedding_model')}",
            f"[bold]{t('rag.model_status_label')}[/bold] {model_status}",
            f"[bold]{t('rag.chunk_size_label')}[/bold] {status.get('chunk_size')}",
            f"[bold]{t('rag.chunk_overlap_label')}[/bold] {status.get('chunk_overlap')}",
            f"[bold]{t('rag.default_top_k_label')}[/bold] {status.get('default_top_k')}",
            f"[bold]{t('rag.collections_count_label')}[/bold] {len(collections)}",
        ]

        if status.get("last_activity"):
            status_lines.append(
                f"[bold]{t('rag.last_activity_label')}[/bold] {status.get('last_activity')}"
            )

        console.print()
        console.print(
            Panel(
                "\n".join(status_lines),
                title=t("rag.status_title"),
                border_style="blue",
            )
        )
        console.print()

    except Exception as e:
        console.print(f"[bold red]{t('shared.error')}[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("install-model", help=lazy_t("rag.help_install_model"))
def install_model(
    cache_dir: Annotated[
        str | None,
        typer.Option(
            "--cache-dir",
            "-d",
            help=lazy_t("rag.opt_cache_dir"),
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help=lazy_t("rag.opt_model"),
        ),
    ] = None,
) -> None:
    # OpenAI embeddings don't require local model download
    if settings.RAG_EMBEDDING_PROVIDER == "openai":
        console.print(f"\n[yellow]{t('rag.openai_no_download')}[/yellow]")
        console.print(f"[dim]{t('rag.openai_key_hint')}[/dim]\n")
        return

    from sentence_transformers import SentenceTransformer

    # Determine model name
    model_name = model or settings.RAG_EMBEDDING_MODEL

    # Determine cache directory (None = use system HuggingFace cache)
    target_dir = cache_dir or settings.RAG_MODEL_CACHE_DIR

    # Check if model is already cached before downloading
    was_cached = _is_model_cached()

    console.print(f"\n[bold blue]{t('rag.model_label')}[/bold blue] {model_name}")
    if target_dir:
        console.print(
            f"[bold blue]{t('rag.cache_dir_label')}[/bold blue] {Path(target_dir).resolve()}"
        )
    else:
        console.print(
            f"[bold blue]{t('rag.cache_dir_label')}[/bold blue] [dim]({t('rag.system_hf_cache')})[/dim]"
        )
    console.print()

    try:
        # Create cache directory if specified
        if target_dir:
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)

        # Download/load model with appropriate messaging
        if was_cached:
            console.print(f"[dim]{t('rag.loading_from_cache')}[/dim]")
        else:
            console.print(
                f"[bold cyan]{t('rag.downloading_named_model', model=model_name)}[/bold cyan]"
            )
            console.print()  # Blank line before tqdm progress bars

        if target_dir:
            _ = SentenceTransformer(model_name, cache_folder=str(target_path))
        else:
            _ = SentenceTransformer(model_name)

        if not was_cached:
            console.print()  # Blank line after progress bars

        # Build result message
        if was_cached:
            status_msg = f"[green]{t('rag.model_found_in_cache')}[/green]"
            title = t("rag.model_ready_title")
        else:
            status_msg = f"[green]{t('rag.model_downloaded')}[/green]"
            title = t("rag.model_install_complete_title")

        if target_dir:
            location_msg = (
                f"[bold]{t('rag.location_label')}[/bold] {Path(target_dir).resolve()}"
            )
            hint_msg = f"\n\n[dim]{t('rag.cache_dir_hint', dir=target_dir)}[/dim]"
        else:
            location_msg = f"[bold]{t('rag.location_label')}[/bold] [dim]({t('rag.system_hf_cache')})[/dim]"
            hint_msg = ""

        console.print(
            Panel(
                f"{status_msg}\n\n"
                f"[bold]{t('rag.model_label')}[/bold] {model_name}\n"
                f"{location_msg}{hint_msg}",
                title=title,
                border_style="green",
            )
        )

    except Exception as e:
        console.print(
            f"[bold red]{t('shared.error')}[/bold red] {t('rag.model_download_failed', error=e)}"
        )
        raise typer.Exit(code=1)
