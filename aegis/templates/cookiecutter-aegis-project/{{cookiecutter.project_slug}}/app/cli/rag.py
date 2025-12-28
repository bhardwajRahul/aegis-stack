"""
RAG (Retrieval-Augmented Generation) CLI commands.

Provides commands for indexing documents, searching collections,
and managing vector store collections.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.config import settings
from app.core.log import suppress_logs
from app.services.rag.config import get_rag_config
from app.services.rag.service import RAGService

app = typer.Typer(help="RAG service commands for document indexing and search")
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
            console.print("[red]OpenAI API key not configured.[/red]")
            console.print(
                "[dim]Set OPENAI_API_KEY environment variable to use OpenAI embeddings.[/dim]"
            )
            raise typer.Exit(code=1)
        return

    # sentence-transformers: check cache and download if needed
    if _is_model_cached():
        return

    model_name = settings.RAG_EMBEDDING_MODEL
    cache_dir = settings.RAG_MODEL_CACHE_DIR

    console.print()
    console.print("[yellow]Embedding model not found locally.[/yellow]")
    console.print(f"[dim]Model: {model_name} (~400MB download)[/dim]")
    console.print()

    try:
        from sentence_transformers import SentenceTransformer

        console.print(
            "[bold cyan]Downloading embedding model (first-time setup)...[/bold cyan]"
        )
        console.print()  # Blank line before tqdm progress bars

        if cache_dir:
            SentenceTransformer(model_name, cache_folder=cache_dir)
        else:
            SentenceTransformer(model_name)

        console.print()  # Blank line after progress bars
        console.print("[green]✓ Model downloaded successfully[/green]")
        console.print()
    except Exception as e:
        console.print(f"[red]Failed to download model: {e}[/red]")
        console.print("[dim]Try running: rag install-model[/dim]")
        raise typer.Exit(code=1)


@app.command("index")
def index_documents(
    path: Annotated[
        str,
        typer.Argument(help="File or directory path to index"),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help="Collection name"),
    ] = "default",
    extensions: Annotated[
        str | None,
        typer.Option(
            "--extensions", "-e", help="Comma-separated file extensions (e.g., .py,.md)"
        ),
    ] = None,
) -> None:
    """
    Index documents from a path into a collection.

    Loads files from the specified path, chunks them, and indexes
    them into ChromaDB for semantic search.

    Examples:
        # Index current directory
        rag index . --collection my-codebase

        # Index specific directory with extensions
        rag index ./app --collection code --extensions .py,.ts
    """
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

    console.print(f"\n[bold blue]Indexing:[/bold blue] {path}")
    console.print(f"[bold blue]Collection:[/bold blue] {collection}")
    if ext_list:
        console.print(f"[bold blue]Extensions:[/bold blue] {', '.join(ext_list)}")
    console.print()

    try:
        with suppress_logs():
            stats = asyncio.run(
                rag_service.refresh_index(
                    path=Path(path),
                    collection_name=collection,
                    extensions=ext_list,
                )
            )

        # Calculate total duration
        total_ms = stats.load_ms + stats.chunk_ms + stats.duration_ms
        total_str = format_duration(total_ms)

        # Format extensions for display
        ext_display = ", ".join(stats.extensions) if stats.extensions else "none"

        # Display results
        console.print(
            Panel(
                f"[green]Successfully indexed {stats.documents_added:,} chunks "
                f"from {stats.source_files:,} files[/green]\n\n"
                f"[bold]Extensions:[/bold] {ext_display}\n"
                f"[bold]Duration:[/bold] {total_str}\n"
                f"[bold]Collection size:[/bold] {stats.total_documents:,} chunks",
                title=f"Collection: {collection}",
                border_style="green",
            )
        )

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] Path not found: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("search")
def search_documents(
    query: Annotated[
        str,
        typer.Argument(help="Search query"),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help="Collection to search"),
    ] = "default",
    top_k: Annotated[
        int,
        typer.Option("--top-k", "-k", help="Number of results"),
    ] = 5,
    show_content: Annotated[
        bool,
        typer.Option("--content", help="Show full content of results"),
    ] = False,
) -> None:
    """
    Search for documents in a collection.

    Performs semantic search using the query text against the
    specified collection.

    Examples:
        # Basic search
        rag search "how does authentication work" --collection my-codebase

        # Show full content
        rag search "database connection" -c code --content
    """
    # Ensure embedding model is available (download if needed)
    if settings.RAG_EMBEDDING_PROVIDER == "sentence-transformers":
        _ensure_model_ready()

    rag_service = get_rag_service()

    console.print(f"\n[bold blue]Searching:[/bold blue] {query}")
    console.print(f"[bold blue]Collection:[/bold blue] {collection}")
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
            console.print("[yellow]No results found.[/yellow]")
            console.print(
                "\n[dim]Tip: Make sure the collection exists and contains documents.[/dim]"
            )
            return

        # Display results
        console.print(f"[green]Found {len(results)} results:[/green]\n")

        for result in results:
            source = result.metadata.get("source", "Unknown")
            file_name = result.metadata.get("file_name", Path(source).name)
            score = result.score

            # Create panel for each result
            if show_content:
                content = result.content
                if len(content) > 500:
                    content = content[:500] + "..."
                panel_content = f"[dim]Score: {score:.4f}[/dim]\n\n{content}"
            else:
                preview = result.content[:200].replace("\n", " ")
                if len(result.content) > 200:
                    preview += "..."
                panel_content = f"[dim]Score: {score:.4f}[/dim]\n\n{preview}"

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
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("list")
def list_collections() -> None:
    """
    List all collections in the vector store.

    Shows collection names and document counts.
    """
    rag_service = get_rag_service()

    try:
        collections = asyncio.run(rag_service.list_collections())

        if not collections:
            console.print("[yellow]No collections found.[/yellow]")
            console.print(
                "\n[dim]Tip: Use 'rag index <path> --collection <name>' to create a collection.[/dim]"
            )
            return

        # Create table
        table = Table(title="RAG Collections", show_header=True)
        table.add_column("Collection", style="cyan")
        table.add_column("Documents", justify="right", style="green")

        for name in collections:
            stats = asyncio.run(rag_service.get_collection_stats(name))
            count = stats.get("count", 0) if stats else 0
            table.add_row(name, str(count))

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_collection(
    collection: Annotated[
        str,
        typer.Argument(help="Collection name to delete"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """
    Delete a collection from the vector store.

    Permanently removes the collection and all its documents.
    """
    rag_service = get_rag_service()

    # Confirm deletion
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete collection '{collection}'?"
        )
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    try:
        deleted = asyncio.run(rag_service.delete_collection(collection))

        if deleted:
            console.print(f"[green]Deleted collection:[/green] {collection}")
        else:
            console.print(f"[yellow]Collection not found:[/yellow] {collection}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("status")
def show_status() -> None:
    """
    Show RAG service status and configuration.
    """
    rag_service = get_rag_service()

    try:
        status = rag_service.get_service_status()
        collections = asyncio.run(rag_service.list_collections())

        # Check if embedding model is installed
        model_cached = _is_model_cached()
        if model_cached:
            model_status = "[green]Installed[/green]"
        else:
            model_status = (
                "[yellow]Not installed[/yellow] [dim](run: rag install-model)[/dim]"
            )

        # Create status panel
        status_lines = [
            f"[bold]Enabled:[/bold] {'Yes' if status.get('enabled') else 'No'}",
            f"[bold]Persist Directory:[/bold] {status.get('persist_directory')}",
            f"[bold]Embedding Model:[/bold] {status.get('embedding_model')}",
            f"[bold]Model Status:[/bold] {model_status}",
            f"[bold]Chunk Size:[/bold] {status.get('chunk_size')}",
            f"[bold]Chunk Overlap:[/bold] {status.get('chunk_overlap')}",
            f"[bold]Default Top K:[/bold] {status.get('default_top_k')}",
            f"[bold]Collections:[/bold] {len(collections)}",
        ]

        if status.get("last_activity"):
            status_lines.append(
                f"[bold]Last Activity:[/bold] {status.get('last_activity')}"
            )

        console.print()
        console.print(
            Panel(
                "\n".join(status_lines),
                title="RAG Service Status",
                border_style="blue",
            )
        )
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("install-model")
def install_model(
    cache_dir: Annotated[
        str | None,
        typer.Option(
            "--cache-dir",
            "-d",
            help="Directory to cache the model (default: system HuggingFace cache)",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Model name to download (default: from settings)",
        ),
    ] = None,
) -> None:
    """
    Pre-download the embedding model for offline/air-gapped operation.

    Downloads the sentence-transformers model to a local cache directory
    so RAG operations work without network access.

    Examples:
        # Download to default location (system HuggingFace cache)
        rag install-model

        # Download to custom location
        rag install-model --cache-dir /path/to/models

        # Download a specific model
        rag install-model --model sentence-transformers/all-MiniLM-L6-v2
    """
    # OpenAI embeddings don't require local model download
    if settings.RAG_EMBEDDING_PROVIDER == "openai":
        console.print(
            "\n[yellow]OpenAI embeddings don't require local model downloads.[/yellow]"
        )
        console.print("[dim]Ensure OPENAI_API_KEY is set in your environment.[/dim]\n")
        return

    from sentence_transformers import SentenceTransformer

    # Determine model name
    model_name = model or settings.RAG_EMBEDDING_MODEL

    # Determine cache directory (None = use system HuggingFace cache)
    target_dir = cache_dir or settings.RAG_MODEL_CACHE_DIR

    # Check if model is already cached before downloading
    was_cached = _is_model_cached()

    console.print(f"\n[bold blue]Model:[/bold blue] {model_name}")
    if target_dir:
        console.print(
            f"[bold blue]Cache directory:[/bold blue] {Path(target_dir).resolve()}"
        )
    else:
        console.print(
            "[bold blue]Cache directory:[/bold blue] [dim](system HuggingFace cache)[/dim]"
        )
    console.print()

    try:
        # Create cache directory if specified
        if target_dir:
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)

        # Download/load model with appropriate messaging
        if was_cached:
            console.print("[dim]Loading model from cache...[/dim]")
        else:
            console.print(f"[bold cyan]Downloading {model_name}...[/bold cyan]")
            console.print()  # Blank line before tqdm progress bars

        if target_dir:
            _ = SentenceTransformer(model_name, cache_folder=str(target_path))
        else:
            _ = SentenceTransformer(model_name)

        if not was_cached:
            console.print()  # Blank line after progress bars

        # Build result message
        if was_cached:
            status_msg = "[green]Model found in cache[/green]"
            title = "Model Ready"
        else:
            status_msg = "[green]Model downloaded successfully[/green]"
            title = "Model Installation Complete"

        if target_dir:
            location_msg = f"[bold]Location:[/bold] {Path(target_dir).resolve()}"
            hint_msg = f"\n\n[dim]To use this cache, set RAG_MODEL_CACHE_DIR={target_dir}[/dim]"
        else:
            location_msg = (
                "[bold]Location:[/bold] [dim](system HuggingFace cache)[/dim]"
            )
            hint_msg = ""

        console.print(
            Panel(
                f"{status_msg}\n\n"
                f"[bold]Model:[/bold] {model_name}\n"
                f"{location_msg}{hint_msg}",
                title=title,
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to download model: {e}")
        raise typer.Exit(code=1)
