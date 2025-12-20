"""
RAG service core implementation.

This module provides the main RAGService class that handles document loading,
chunking, indexing, and semantic search functionality.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.log import logger

from .chunking import DocumentChunker
from .config import get_rag_config
from .loaders import CodebaseLoader
from .models import Document, IndexStats, SearchResult
from .vectorstore import VectorStoreManager


class RAGServiceError(Exception):
    """Base exception for RAG service errors."""

    pass


class LoaderError(RAGServiceError):
    """Exception raised when document loading fails."""

    pass


class IndexingError(RAGServiceError):
    """Exception raised when indexing fails."""

    pass


class SearchError(RAGServiceError):
    """Exception raised when search fails."""

    pass


class RAGService:
    """
    Core RAG service for document retrieval.

    Handles document loading, chunking, indexing to ChromaDB,
    and semantic search with built-in embeddings.

    Example:
        ```python
        from app.services.rag.service import RAGService
        from app.core.config import settings

        rag = RAGService(settings)

        # Index codebase
        await rag.refresh_index("./app", "my-codebase")

        # Search
        results = await rag.search("how does auth work?", "my-codebase")
        for r in results:
            print(f"{r.metadata['source']}: {r.content[:100]}...")
        ```
    """

    def __init__(self, settings: Any):
        """Initialize RAG service with configuration."""
        self.settings = settings
        self.config = get_rag_config(settings)
        self.loader = CodebaseLoader()
        self.chunker = DocumentChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.vectorstore = VectorStoreManager(
            persist_directory=self.config.persist_directory,
            embedding_model=self.config.embedding_model,
        )
        self._last_activity: datetime | None = None

    # ============================================
    # Core Async Functions (scheduler/worker ready)
    # ============================================

    async def load_documents(
        self,
        path: str | Path,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[Document]:
        """
        Load source files from a path.

        Args:
            path: File or directory path to load
            extensions: File extensions to include (e.g., [".py", ".md"])
            exclude_patterns: Glob patterns to exclude (e.g., ["**/test_*"])

        Returns:
            list[Document]: Loaded documents with metadata

        Raises:
            LoaderError: If loading fails
        """
        try:
            documents = await self.loader.load(path, extensions, exclude_patterns)
            self._last_activity = datetime.now(UTC)
            return documents
        except FileNotFoundError as e:
            raise LoaderError(f"Path not found: {path}") from e
        except Exception as e:
            raise LoaderError(f"Failed to load documents: {e}") from e

    async def chunk_documents(
        self,
        documents: list[Document],
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[Document]:
        """
        Split documents into chunks for indexing.

        Args:
            documents: Documents to chunk
            chunk_size: Override default chunk size
            chunk_overlap: Override default overlap

        Returns:
            list[Document]: Chunked documents with preserved metadata
        """
        chunks = await self.chunker.chunk(documents, chunk_size, chunk_overlap)
        self._last_activity = datetime.now(UTC)
        return chunks

    async def index_documents(
        self,
        documents: list[Document],
        collection_name: str,
        metadata_fields: list[str] | None = None,
    ) -> IndexStats:
        """
        Add documents to ChromaDB collection.

        Args:
            documents: Documents (or chunks) to index
            collection_name: ChromaDB collection name
            metadata_fields: Which metadata fields to include

        Returns:
            IndexStats: Statistics about the indexing operation

        Raises:
            IndexingError: If indexing fails
        """
        try:
            stats = await self.vectorstore.add_documents(
                documents, collection_name, metadata_fields
            )
            self._last_activity = datetime.now(UTC)

            logger.info(
                "rag_service.index_documents",
                collection=collection_name,
                documents=stats.documents_added,
                total=stats.total_documents,
                duration_ms=round(stats.duration_ms, 2),
            )

            return stats
        except Exception as e:
            raise IndexingError(f"Failed to index documents: {e}") from e

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Query vector store for relevant documents.

        Args:
            query: Search query text
            collection_name: ChromaDB collection to search
            top_k: Number of results to return (default from config)
            filter_metadata: Optional metadata filter

        Returns:
            list[SearchResult]: Ranked search results with scores

        Raises:
            SearchError: If search fails
        """
        try:
            k = top_k or self.config.default_top_k
            results = await self.vectorstore.search(
                query, collection_name, k, filter_metadata
            )
            self._last_activity = datetime.now(UTC)
            return results
        except Exception as e:
            raise SearchError(f"Failed to search: {e}") from e

    async def refresh_index(
        self,
        path: str | Path,
        collection_name: str,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> IndexStats:
        """
        Full reindex: load, chunk, and index documents.

        Convenience method that combines load_documents,
        chunk_documents, and index_documents into a single operation.
        Deletes existing collection before reindexing.

        Args:
            path: File or directory path to load
            collection_name: ChromaDB collection name
            extensions: File extensions to include
            exclude_patterns: Glob patterns to exclude

        Returns:
            IndexStats: Statistics about the indexing operation
        """
        logger.info(
            "rag_service.refresh_index.start",
            path=str(path),
            collection=collection_name,
        )

        # Delete existing collection
        await self.vectorstore.delete_collection(collection_name)

        # Load documents
        documents = await self.load_documents(path, extensions, exclude_patterns)

        if not documents:
            logger.warning(
                "rag_service.refresh_index.no_documents",
                path=str(path),
            )
            return IndexStats(
                collection_name=collection_name,
                documents_added=0,
                total_documents=0,
                duration_ms=0.0,
            )

        # Chunk documents
        chunks = await self.chunk_documents(documents)

        # Index chunks
        stats = await self.index_documents(chunks, collection_name)

        logger.info(
            "rag_service.refresh_index.complete",
            collection=collection_name,
            source_docs=len(documents),
            chunks=stats.documents_added,
            duration_ms=round(stats.duration_ms, 2),
        )

        return stats

    # ============================================
    # Collection Management
    # ============================================

    async def list_collections(self) -> list[str]:
        """List all ChromaDB collections."""
        return await self.vectorstore.list_collections()

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any] | None:
        """Get statistics for a collection."""
        info = await self.vectorstore.get_collection_info(collection_name)
        if info:
            return info.model_dump()
        return None

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a ChromaDB collection."""
        return await self.vectorstore.delete_collection(collection_name)

    # ============================================
    # Service Status & Health
    # ============================================

    def get_service_status(self) -> dict[str, Any]:
        """Get current service status and metrics."""
        return {
            "enabled": self.config.enabled,
            "persist_directory": self.config.persist_directory,
            "embedding_model": self.config.embedding_model,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "default_top_k": self.config.default_top_k,
            "last_activity": self._last_activity.isoformat()
            if self._last_activity
            else None,
        }

    def validate_service(self) -> list[str]:
        """Validate service configuration and return any issues."""
        return self.config.validate_configuration()
