"""
Document chunking utilities for RAG service.

Provides text splitting with configurable chunk sizes and overlap,
using a recursive character text splitting strategy.
"""

import asyncio

from app.core.log import logger

from .models import Document


class DocumentChunker:
    """Splits documents into smaller chunks for indexing."""

    # Separators for recursive splitting (in order of preference)
    SEPARATORS = [
        "\n\n\n",  # Triple newline (major sections)
        "\n\n",  # Double newline (paragraphs)
        "\n",  # Single newline
        ". ",  # Sentence end
        "? ",  # Question end
        "! ",  # Exclamation end
        "; ",  # Semicolon
        ", ",  # Clause
        " ",  # Word
        "",  # Character (last resort)
    ]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def chunk(
        self,
        documents: list[Document],
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[Document]:
        """
        Split documents into chunks.

        Args:
            documents: Documents to split
            chunk_size: Override default chunk size
            chunk_overlap: Override default overlap

        Returns:
            list[Document]: Chunked documents with preserved metadata
        """
        size = chunk_size or self.chunk_size
        overlap = chunk_overlap or self.chunk_overlap

        # Run chunking in thread pool (CPU-bound)
        chunks = await asyncio.to_thread(
            self._chunk_documents_sync, documents, size, overlap
        )

        logger.info(
            "document_chunker.chunk",
            input_docs=len(documents),
            output_chunks=len(chunks),
            chunk_size=size,
            overlap=overlap,
        )

        return chunks

    def _chunk_documents_sync(
        self,
        documents: list[Document],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Document]:
        """Synchronous chunking implementation."""
        chunks: list[Document] = []

        for doc in documents:
            doc_chunks = self._split_text(doc.content, chunk_size, chunk_overlap)

            for i, chunk_text in enumerate(doc_chunks):
                chunk = Document(
                    content=chunk_text,
                    metadata={
                        **doc.metadata,
                        "chunk_index": i,
                        "total_chunks": len(doc_chunks),
                        "chunk_size": len(chunk_text),
                    },
                )
                chunks.append(chunk)

        return chunks

    def _split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        depth: int = 0,
    ) -> list[str]:
        """Recursively split text into chunks."""
        # If text fits in one chunk, return as-is
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        # Prevent infinite recursion - fall back to length-based splitting
        if depth > 10:
            return self._split_by_length(text, chunk_size, chunk_overlap)

        # Find best separator
        for separator in self.SEPARATORS:
            if separator and separator in text:
                return self._split_with_separator(
                    text, separator, chunk_size, chunk_overlap, depth
                )

        # No separator found, split by fixed length
        return self._split_by_length(text, chunk_size, chunk_overlap)

    def _split_with_separator(
        self,
        text: str,
        separator: str,
        chunk_size: int,
        chunk_overlap: int,
        depth: int = 0,
    ) -> list[str]:
        """Split text using a separator."""
        splits = text.split(separator)
        chunks: list[str] = []
        current_chunk = ""

        for split in splits:
            # Check if adding this split would exceed chunk size
            potential_chunk = (
                current_chunk + separator + split if current_chunk else split
            )

            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if non-empty
                if current_chunk.strip():
                    chunks.append(current_chunk)

                # Start new chunk with overlap from previous
                if chunk_overlap > 0 and current_chunk:
                    # Get overlap from end of current chunk
                    overlap_text = current_chunk[-chunk_overlap:]
                    current_chunk = overlap_text + separator + split
                else:
                    current_chunk = split

                # If single split is too large, recursively split it
                if len(current_chunk) > chunk_size:
                    sub_chunks = self._split_text(
                        current_chunk, chunk_size, chunk_overlap, depth + 1
                    )
                    if sub_chunks:
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1]
                    else:
                        current_chunk = ""

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk)

        return chunks

    def _split_by_length(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        """Split text by fixed length (last resort)."""
        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - chunk_overlap

            # Safety: prevent infinite loop
            if start <= 0 and end >= len(text):
                break

        return chunks


def estimate_chunks(content_length: int, chunk_size: int, chunk_overlap: int) -> int:
    """
    Estimate the number of chunks for a given content length.

    Args:
        content_length: Length of content in characters
        chunk_size: Chunk size
        chunk_overlap: Overlap between chunks

    Returns:
        Estimated number of chunks
    """
    if content_length <= chunk_size:
        return 1

    effective_size = chunk_size - chunk_overlap
    if effective_size <= 0:
        return 1

    return max(1, (content_length - chunk_overlap) // effective_size + 1)
