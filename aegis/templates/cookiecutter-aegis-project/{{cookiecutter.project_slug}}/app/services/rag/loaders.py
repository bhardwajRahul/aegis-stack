"""
Document loaders for RAG service.

Provides codebase loading functionality with file type detection
and metadata extraction.
"""

import asyncio
import fnmatch
from pathlib import Path
from typing import Any

from app.core.log import logger

from .models import Document

# Default extensions to index (conservative set for most codebases)
DEFAULT_EXTENSIONS = [".py", ".md", ".yml", ".yaml", ".txt"]

# Supported file extensions and their metadata
LOADER_MAP: dict[str, dict[str, Any]] = {
    # Code files
    ".py": {"type": "code", "language": "python"},
    ".js": {"type": "code", "language": "javascript"},
    ".ts": {"type": "code", "language": "typescript"},
    ".tsx": {"type": "code", "language": "typescript"},
    ".jsx": {"type": "code", "language": "javascript"},
    ".java": {"type": "code", "language": "java"},
    ".go": {"type": "code", "language": "go"},
    ".rs": {"type": "code", "language": "rust"},
    ".rb": {"type": "code", "language": "ruby"},
    ".php": {"type": "code", "language": "php"},
    ".c": {"type": "code", "language": "c"},
    ".cpp": {"type": "code", "language": "cpp"},
    ".h": {"type": "code", "language": "c"},
    ".hpp": {"type": "code", "language": "cpp"},
    ".cs": {"type": "code", "language": "csharp"},
    ".swift": {"type": "code", "language": "swift"},
    ".kt": {"type": "code", "language": "kotlin"},
    ".scala": {"type": "code", "language": "scala"},
    # Config/data files
    ".json": {"type": "data", "language": "json"},
    ".yaml": {"type": "config", "language": "yaml"},
    ".yml": {"type": "config", "language": "yaml"},
    ".toml": {"type": "config", "language": "toml"},
    ".xml": {"type": "data", "language": "xml"},
    ".sql": {"type": "code", "language": "sql"},
    # Documentation
    ".md": {"type": "documentation", "language": "markdown"},
    ".txt": {"type": "documentation", "language": "text"},
    ".rst": {"type": "documentation", "language": "restructuredtext"},
    # Shell scripts
    ".sh": {"type": "script", "language": "bash"},
    ".bash": {"type": "script", "language": "bash"},
    ".zsh": {"type": "script", "language": "zsh"},
    # Web files
    ".html": {"type": "web", "language": "html"},
    ".css": {"type": "web", "language": "css"},
    ".scss": {"type": "web", "language": "scss"},
    ".less": {"type": "web", "language": "less"},
}

# Default exclusion patterns
DEFAULT_EXCLUDE_PATTERNS = [
    "**/.git/**",
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/.env",
    "**/.env.*",
    "**/dist/**",
    "**/build/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/egg-info/**",
    "**/.eggs/**",
    "**/.tox/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/coverage/**",
    "**/.coverage",
    "**/htmlcov/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/package-lock.json",
    "**/yarn.lock",
    "**/poetry.lock",
    "**/uv.lock",
]


class CodebaseLoader:
    """Loads source files from a codebase directory."""

    def __init__(
        self,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ):
        """
        Initialize codebase loader.

        Args:
            extensions: File extensions to include (default: DEFAULT_EXTENSIONS)
            exclude_patterns: Glob patterns to exclude
        """
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS

    async def load(
        self,
        path: str | Path,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[Document]:
        """
        Load documents from path.

        Args:
            path: File or directory to load
            extensions: Override default extensions
            exclude_patterns: Override default exclusions

        Returns:
            list[Document]: Loaded documents with metadata

        Raises:
            FileNotFoundError: If path does not exist
        """
        path = Path(path)
        extensions = extensions or self.extensions
        exclude = exclude_patterns or self.exclude_patterns

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        documents: list[Document] = []

        if path.is_file():
            doc = await self._load_file(path)
            if doc:
                documents.append(doc)
        else:
            documents = await self._load_directory(path, extensions, exclude)

        logger.info(
            "codebase_loader.load",
            path=str(path),
            document_count=len(documents),
        )

        return documents

    async def _load_file(self, file_path: Path) -> Document | None:
        """Load a single file."""
        ext = file_path.suffix.lower()

        if ext not in LOADER_MAP:
            return None

        try:
            # Run file I/O in thread pool to not block event loop
            content = await asyncio.to_thread(
                file_path.read_text, encoding="utf-8", errors="replace"
            )

            file_info = LOADER_MAP[ext]

            return Document(
                content=content,
                metadata={
                    "source": str(file_path.absolute()),
                    "file_name": file_path.name,
                    "extension": ext,
                    "file_type": file_info["type"],
                    "language": file_info["language"],
                    "size_bytes": len(content.encode("utf-8")),
                },
            )
        except Exception as e:
            logger.warning(
                "codebase_loader.file_error",
                file_path=str(file_path),
                error=str(e),
            )
            return None

    async def _load_directory(
        self,
        directory: Path,
        extensions: list[str],
        exclude_patterns: list[str],
    ) -> list[Document]:
        """Load all matching files from directory."""
        documents: list[Document] = []

        def should_exclude(file_path: Path) -> bool:
            """Check if file matches any exclusion pattern."""
            # Get relative path for pattern matching
            try:
                rel_path = file_path.relative_to(directory)
            except ValueError:
                rel_path = file_path

            # Check each exclusion pattern
            for pattern in exclude_patterns:
                # Use pathlib's match which handles ** patterns
                if rel_path.match(pattern):
                    return True
                # Also check individual path components for simple exclusions
                # e.g., ".venv" should exclude any path containing .venv
                simple_pattern = pattern.replace("**/", "").replace("/**", "")
                for part in rel_path.parts:
                    if fnmatch.fnmatch(part, simple_pattern):
                        return True
            return False

        # Collect all matching files
        tasks = []
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                if not should_exclude(file_path):
                    tasks.append(self._load_file(file_path))

        # Load files concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Document):
                    documents.append(result)
                elif isinstance(result, Exception):
                    logger.warning("codebase_loader.load_error", error=str(result))

        return documents


def get_supported_extensions() -> list[str]:
    """Get list of supported file extensions."""
    return list(LOADER_MAP.keys())


def get_extension_info(extension: str) -> dict[str, Any] | None:
    """Get metadata for a file extension."""
    return LOADER_MAP.get(extension.lower())
