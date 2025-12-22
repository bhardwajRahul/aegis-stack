"""
Deterministic ID generation for RAG chunks.

These functions are in a separate module to avoid importing ChromaDB
when only ID generation is needed (e.g., in tests).
"""

import hashlib


def get_file_hash(source_path: str) -> str:
    """Generate deterministic hash for a file path."""
    return hashlib.md5(source_path.encode()).hexdigest()[:8]


def generate_chunk_id(source_path: str, chunk_index: int) -> str:
    """
    Generate deterministic chunk ID.

    Format: {file_hash}_{chunk_index}
    Example: a1b2c3d4_0, a1b2c3d4_1, etc.

    This ensures:
    - Same file always gets same hash prefix
    - Easy to find/delete all chunks from a file
    - Re-indexing same file produces same IDs (upsert works)
    """
    file_hash = get_file_hash(source_path)
    return f"{file_hash}_{chunk_index}"
