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

app = typer.Typer(help="RAG service commands for document indexing and search")
console = Console()


def get_rag_service() -> RAGService:
    """Get RAG service instance."""
    return RAGService(settings)


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
                "Indexing...",
                total=None,
                status="Loading documents...",
            )

            def on_progress(batch: int, total: int, chunks: int) -> None:
                progress.update(
                    task,
                    total=total,
                    completed=batch,
                    status=f"Batch {batch}/{total} ({chunks} chunks)",
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
        ext_display = ", ".join(stats.extensions) if stats.extensions else "none"

        # Display results with phase breakdown
        console.print(
            Panel(
                f"[green]Successfully indexed {stats.documents_added:,} chunks "
                f"from {stats.source_files:,} files[/green]\n\n"
                f"[bold]Extensions:[/bold] {ext_display}\n"
                f"[bold]Duration:[/bold] {total_str}\n"
                f"  [dim]Loading:[/dim]  {format_duration(stats.load_ms)} ({pct(stats.load_ms)})\n"
                f"  [dim]Chunking:[/dim] {format_duration(stats.chunk_ms)} ({pct(stats.chunk_ms)})\n"
                f"  [dim]Indexing:[/dim] {format_duration(stats.duration_ms)} ({pct(stats.duration_ms)})\n"
                f"[bold]Throughput:[/bold] {chunks_per_sec:.1f} chunks/sec\n"
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


@app.command("add")
def add_file(
    path: Annotated[
        str,
        typer.Argument(help="File path to add/update"),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help="Collection name"),
    ] = "default",
    show_ids: Annotated[
        bool,
        typer.Option("--show-ids", help="Show chunk IDs in output"),
    ] = False,
) -> None:
    """
    Add or update a single file in the collection.

    Uses upsert semantics: re-adding a file updates its chunks.

    Examples:
        # Add a single file
        rag add app/services/auth.py --collection my-code

        # Show the chunk IDs
        rag add app/services/auth.py -c my-code --show-ids
    """
    rag_service = get_rag_service()

    console.print(f"\n[bold blue]Adding:[/bold blue] {path}")
    console.print(f"[bold blue]Collection:[/bold blue] {collection}")
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
            f"[green]Added/updated:[/green] {file_name}\n"
            f"Chunks: {result.chunk_count}\n"
            f"Hash: {result.file_hash}"
        )

        if show_ids and result.chunk_ids:
            output += f"\nIDs: {', '.join(result.chunk_ids)}"

        console.print(
            Panel(
                output,
                title=f"Collection: {collection}",
                border_style="green",
            )
        )

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] File not found: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("remove")
def remove_file(
    source_path: Annotated[
        str,
        typer.Argument(help="Source path of file to remove (as stored in metadata)"),
    ],
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help="Collection name"),
    ] = "default",
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """
    Remove a file's chunks from the collection.

    Uses the source path as stored in the collection metadata.
    Use 'rag files' to see the exact paths stored.

    Examples:
        # Remove a file
        rag remove /path/to/app/services/auth.py --collection my-code

        # Skip confirmation
        rag remove /path/to/file.py -c my-code --force
    """
    rag_service = get_rag_service()

    # Confirm deletion
    if not force:
        confirm = typer.confirm(
            f"Remove all chunks for '{source_path}' from '{collection}'?"
        )
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
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
                f"[green]Removed {result.chunk_count} chunks[/green] for: {source_path}"
            )
        else:
            console.print(f"[yellow]No chunks found for:[/yellow] {source_path}")
            console.print(
                "[dim]Tip: Use 'rag files --collection <name>' to see indexed paths.[/dim]"
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("files")
def list_files(
    collection: Annotated[
        str,
        typer.Option("--collection", "-c", help="Collection name"),
    ] = "default",
) -> None:
    """
    List all indexed files in a collection.

    Shows file paths and chunk counts.

    Examples:
        rag files --collection my-code
    """
    rag_service = get_rag_service()

    try:
        files = asyncio.run(rag_service.list_files(collection_name=collection))

        if not files:
            console.print(
                f"[yellow]No files indexed in collection:[/yellow] {collection}"
            )
            console.print(
                "\n[dim]Tip: Use 'rag index <path> --collection <name>' or "
                "'rag add <file> --collection <name>' to index content.[/dim]"
            )
            return

        # Create table
        table = Table(
            title=f"Indexed Files: {collection}",
            show_header=True,
        )
        table.add_column("File", style="cyan")
        table.add_column("Chunks", justify="right", style="green")

        total_chunks = 0
        for file in files:
            table.add_row(file.source, str(file.chunks))
            total_chunks += file.chunks

        console.print()
        console.print(table)
        console.print(
            f"\n[bold]Total:[/bold] {len(files)} files, {total_chunks} chunks"
        )
        console.print()

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

        # Create status panel
        status_lines = [
            f"[bold]Enabled:[/bold] {'Yes' if status.get('enabled') else 'No'}",
            f"[bold]Persist Directory:[/bold] {status.get('persist_directory')}",
            f"[bold]Embedding Model:[/bold] {status.get('embedding_model')}",
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
