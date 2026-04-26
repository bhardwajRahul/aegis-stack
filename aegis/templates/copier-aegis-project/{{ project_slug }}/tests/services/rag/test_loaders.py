"""Tests for RAG document loaders."""

from pathlib import Path

import pytest
from app.services.rag.loaders import (
    LOADER_MAP,
    CodebaseLoader,
    get_extension_info,
    get_supported_extensions,
)


@pytest.fixture
def sample_codebase(tmp_path: Path) -> Path:
    """Create a sample codebase for testing."""
    # Create Python files
    (tmp_path / "main.py").write_text("def main():\n    print('hello')")
    (tmp_path / "utils.py").write_text("def helper(): pass")

    # Create subdirectory with files
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "core.py").write_text("class Core: pass")

    # Create non-code files
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "config.yaml").write_text("key: value")

    # Create files to exclude
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-311.pyc").write_bytes(b"compiled")

    return tmp_path


class TestCodebaseLoader:
    """Tests for CodebaseLoader."""

    @pytest.mark.asyncio
    async def test_load_single_file(self, tmp_path: Path) -> None:
        """Test loading a single file."""
        file_path = tmp_path / "test.py"
        file_path.write_text("print('test')")

        loader = CodebaseLoader()
        docs = await loader.load(file_path)

        assert len(docs) == 1
        assert docs[0].content == "print('test')"
        assert docs[0].metadata["extension"] == ".py"
        assert docs[0].metadata["language"] == "python"

    @pytest.mark.asyncio
    async def test_load_directory(self, sample_codebase: Path) -> None:
        """Test loading a directory."""
        loader = CodebaseLoader()
        docs = await loader.load(sample_codebase)

        # Should load all matching files
        assert len(docs) >= 4  # main.py, utils.py, core.py, README.md

        # Should not load pycache
        sources = [d.metadata["source"] for d in docs]
        assert not any("__pycache__" in s for s in sources)

    @pytest.mark.asyncio
    async def test_load_with_extensions_filter(self, sample_codebase: Path) -> None:
        """Test loading with specific extensions."""
        loader = CodebaseLoader()
        docs = await loader.load(
            sample_codebase,
            extensions=[".py"],
        )

        # Should only load Python files
        for doc in docs:
            assert doc.metadata["extension"] == ".py"

    @pytest.mark.asyncio
    async def test_load_nonexistent_path(self) -> None:
        """Test loading from non-existent path."""
        loader = CodebaseLoader()

        with pytest.raises(FileNotFoundError):
            await loader.load("/nonexistent/path")

    @pytest.mark.asyncio
    async def test_document_metadata(self, tmp_path: Path) -> None:
        """Test that documents have proper metadata."""
        file_path = tmp_path / "example.py"
        file_path.write_text("# Example code\nx = 1")

        loader = CodebaseLoader()
        docs = await loader.load(file_path)

        assert len(docs) == 1
        doc = docs[0]

        assert "source" in doc.metadata
        assert "file_name" in doc.metadata
        assert doc.metadata["file_name"] == "example.py"
        assert "extension" in doc.metadata
        assert "file_type" in doc.metadata
        assert "language" in doc.metadata
        assert "size_bytes" in doc.metadata


class TestLoaderUtilities:
    """Tests for loader utility functions."""

    def test_get_supported_extensions(self) -> None:
        """Test getting supported extensions."""
        extensions = get_supported_extensions()
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".md" in extensions

    def test_get_extension_info(self) -> None:
        """Test getting extension info."""
        info = get_extension_info(".py")
        assert info is not None
        assert info["type"] == "code"
        assert info["language"] == "python"

        info = get_extension_info(".unknown")
        assert info is None

    def test_loader_map_completeness(self) -> None:
        """Test that all common extensions are in loader map."""
        expected = [".py", ".js", ".ts", ".md", ".json", ".yaml"]
        for ext in expected:
            assert ext in LOADER_MAP
