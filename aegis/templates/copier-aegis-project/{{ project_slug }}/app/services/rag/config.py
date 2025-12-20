"""
RAG service configuration.

Configuration management for RAG service including chunking settings,
vector store paths, and search parameters.
"""

from typing import Any

from pydantic import BaseModel, Field


class RAGServiceConfig(BaseModel):
    """
    RAG service configuration that integrates with main app settings.

    Provides chunking, vector store, and search configuration.
    """

    enabled: bool = True
    persist_directory: str = Field(
        default="./data/chromadb",
        description="Directory for ChromaDB persistence",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model (ChromaDB built-in)",
    )
    chunk_size: int = Field(
        default=1000,
        gt=0,
        le=10000,
        description="Maximum chunk size in characters",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=500,
        description="Overlap between chunks in characters",
    )
    default_top_k: int = Field(
        default=5,
        gt=0,
        le=50,
        description="Default number of search results",
    )
    default_extensions: list[str] = Field(
        default=[".py", ".js", ".ts", ".md", ".txt", ".json", ".yaml", ".yml"],
        description="Default file extensions to include",
    )

    @classmethod
    def from_settings(cls, settings: Any) -> "RAGServiceConfig":
        """Create configuration from main application settings."""
        return cls(
            enabled=getattr(settings, "RAG_ENABLED", True),
            persist_directory=getattr(
                settings, "RAG_PERSIST_DIRECTORY", "./data/chromadb"
            ),
            embedding_model=getattr(
                settings, "RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
            ),
            chunk_size=getattr(settings, "RAG_CHUNK_SIZE", 1000),
            chunk_overlap=getattr(settings, "RAG_CHUNK_OVERLAP", 200),
            default_top_k=getattr(settings, "RAG_DEFAULT_TOP_K", 5),
        )

    def validate_configuration(self) -> list[str]:
        """
        Validate RAG service configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.enabled:
            return errors

        if self.chunk_overlap >= self.chunk_size:
            errors.append(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )

        return errors


def get_rag_config(settings: Any) -> RAGServiceConfig:
    """Get RAG service configuration from application settings."""
    return RAGServiceConfig.from_settings(settings)
