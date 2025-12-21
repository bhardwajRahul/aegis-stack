"""
ChromaDB vector store integration for RAG service.

Uses ChromaDB's built-in embeddings (all-MiniLM-L6-v2) for
zero-configuration semantic search.
"""

import asyncio
from pathlib import Path
from typing import Any

import chromadb
from app.core.log import logger
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

from .models import CollectionInfo, Document, IndexStats, SearchResult


class VectorStoreError(Exception):
    """Base exception for vector store errors."""

    pass


class CollectionNotFoundError(VectorStoreError):
    """Raised when a collection is not found."""

    pass


class VectorStoreManager:
    """Manages ChromaDB collections and operations."""

    def __init__(
        self,
        persist_directory: str = "./data/chromadb",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize vector store manager.

        Args:
            persist_directory: Directory for ChromaDB persistence
            embedding_model: Embedding model name (ChromaDB built-in)
        """
        self.persist_directory = Path(persist_directory)
        self.embedding_model = embedding_model
        self._client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client (lazy initialization)."""
        if self._client is None:
            self.persist_directory.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info(
                "vectorstore.initialized",
                persist_directory=str(self.persist_directory),
            )

        return self._client

    async def add_documents(
        self,
        documents: list[Document],
        collection_name: str,
        metadata_fields: list[str] | None = None,
    ) -> IndexStats:
        """
        Add documents to a collection.

        ChromaDB will automatically embed documents using the built-in
        all-MiniLM-L6-v2 model.

        Args:
            documents: Documents to add
            collection_name: Target collection name
            metadata_fields: Metadata fields to include (default: all)

        Returns:
            IndexStats: Indexing statistics
        """
        start_time = asyncio.get_event_loop().time()

        # Get or create collection
        collection = await asyncio.to_thread(
            self.client.get_or_create_collection,
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Prepare documents for ChromaDB
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for i, doc in enumerate(documents):
            doc_id = f"{collection_name}_{i}"
            ids.append(doc_id)
            texts.append(doc.content)

            # Filter metadata if specified
            if metadata_fields:
                metadata = {
                    k: v for k, v in doc.metadata.items() if k in metadata_fields
                }
            else:
                metadata = doc.metadata

            # ChromaDB requires string/int/float/bool values
            clean_metadata = self._clean_metadata(metadata)
            metadatas.append(clean_metadata)

        # Add to collection in batches
        batch_size = 500
        for batch_start in range(0, len(ids), batch_size):
            batch_end = min(batch_start + batch_size, len(ids))

            await asyncio.to_thread(
                collection.add,
                ids=ids[batch_start:batch_end],
                documents=texts[batch_start:batch_end],
                metadatas=metadatas[batch_start:batch_end],
            )

        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000

        total_count = await asyncio.to_thread(collection.count)

        stats = IndexStats(
            collection_name=collection_name,
            documents_added=len(documents),
            total_documents=total_count,
            duration_ms=duration_ms,
        )

        logger.info(
            "vectorstore.add_documents",
            collection=collection_name,
            count=len(documents),
            duration_ms=round(duration_ms, 2),
        )

        return stats

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Search for relevant documents.

        Args:
            query: Search query text
            collection_name: Collection to search
            top_k: Number of results
            filter_metadata: Optional metadata filter

        Returns:
            list[SearchResult]: Ranked results with scores
        """
        try:
            collection = await asyncio.to_thread(
                self.client.get_collection,
                name=collection_name,
            )
        except (ValueError, NotFoundError):
            logger.warning(
                "vectorstore.collection_not_found",
                collection=collection_name,
            )
            return []

        # Build ChromaDB where clause
        where = None
        if filter_metadata:
            where = self._build_where_clause(filter_metadata)

        # Query collection
        results = await asyncio.to_thread(
            collection.query,
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Convert to SearchResult objects
        search_results: list[SearchResult] = []

        if results["documents"] and results["documents"][0]:
            for i, doc_text in enumerate(results["documents"][0]):
                # ChromaDB returns distance, convert to similarity score
                distance = results["distances"][0][i] if results["distances"] else 0.0
                # For cosine distance, similarity = 1 - distance
                # But distance can be > 1 for non-normalized vectors
                score = max(0.0, min(1.0, 1.0 - distance))

                result = SearchResult(
                    content=doc_text,
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=score,
                    rank=i + 1,
                )
                search_results.append(result)

        logger.debug(
            "vectorstore.search",
            collection=collection_name,
            query_length=len(query),
            results=len(search_results),
        )

        return search_results

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            await asyncio.to_thread(
                self.client.delete_collection,
                name=collection_name,
            )
            logger.info("vectorstore.delete_collection", collection=collection_name)
            return True
        except (ValueError, NotFoundError):
            return False

    async def list_collections(self) -> list[str]:
        """List all collection names."""
        collections = await asyncio.to_thread(self.client.list_collections)
        # ChromaDB 1.x returns strings, older versions return Collection objects
        if collections and isinstance(collections[0], str):
            return collections
        return [c.name for c in collections]

    async def get_collection_info(self, collection_name: str) -> CollectionInfo | None:
        """Get information about a collection."""
        try:
            collection = await asyncio.to_thread(
                self.client.get_collection,
                name=collection_name,
            )
            count = await asyncio.to_thread(collection.count)
            return CollectionInfo(
                name=collection_name,
                count=count,
                metadata=collection.metadata or {},
            )
        except (ValueError, NotFoundError):
            return None

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        collections = await self.list_collections()
        return collection_name in collections

    def _clean_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Clean metadata for ChromaDB compatibility."""
        clean: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, str | int | float | bool):
                clean[key] = value
            elif value is None:
                continue
            else:
                # Convert other types to string
                clean[key] = str(value)
        return clean

    def _build_where_clause(self, filter_metadata: dict[str, Any]) -> dict[str, Any]:
        """Build ChromaDB where clause from filter."""
        # Simple equality filter
        if len(filter_metadata) == 1:
            key, value = next(iter(filter_metadata.items()))
            return {key: value}

        # Multiple conditions with AND
        conditions = []
        for key, value in filter_metadata.items():
            conditions.append({key: value})

        return {"$and": conditions}
