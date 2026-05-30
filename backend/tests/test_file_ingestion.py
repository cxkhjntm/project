"""Tests for file ingestion service."""

import pytest
from pathlib import Path
import tempfile
import os

from app.utils.file_filter import (
    is_allowed_extension,
    is_excluded_directory,
    is_file_too_large,
    scan_directory,
    read_file_content,
)


class TestFileFilter:
    """Test file filter utilities."""

    def test_allowed_extensions(self) -> None:
        """Test allowed extension check."""
        assert is_allowed_extension("test.py") is True
        assert is_allowed_extension("test.ts") is True
        assert is_allowed_extension("test.js") is True
        assert is_allowed_extension("test.md") is True
        assert is_allowed_extension("test.txt") is True
        assert is_allowed_extension("test.json") is True
        assert is_allowed_extension("test.csv") is True
        assert is_allowed_extension("test.exe") is False
        assert is_allowed_extension("test.bin") is False

    def test_excluded_directories(self) -> None:
        """Test excluded directory check."""
        assert is_excluded_directory("node_modules") is True
        assert is_excluded_directory(".git") is True
        assert is_excluded_directory("__pycache__") is True
        assert is_excluded_directory("src") is False
        assert is_excluded_directory("tests") is False

    def test_file_size_limit(self) -> None:
        """Test file size limit check."""
        assert is_file_too_large(1024) is False  # 1KB
        assert is_file_too_large(1024 * 1024) is False  # 1MB
        assert is_file_too_large(100 * 1024 * 1024) is True  # 100MB

    def test_scan_directory(self) -> None:
        """Test directory scanning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "test.py").write_text("print('hello')")
            (Path(tmpdir) / "test.md").write_text("# Hello")
            (Path(tmpdir) / "test.exe").write_bytes(b"\x00\x00")
            (Path(tmpdir) / "node_modules").mkdir()
            (Path(tmpdir) / "node_modules" / "dep.py").write_text("ignored")

            files = scan_directory(tmpdir)
            
            paths = [f["relative_path"] for f in files]
            assert "test.py" in paths
            assert "test.md" in paths
            assert "test.exe" not in paths
            assert not any("node_modules" in p for p in paths)

    def test_read_file_content(self) -> None:
        """Test file content reading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World!")
            tmp_path = f.name

        try:
            content = read_file_content(tmp_path)
            assert content == "Hello, World!"
        finally:
            os.unlink(tmp_path)

    def test_read_nonexistent_file(self) -> None:
        """Test reading nonexistent file returns None."""
        content = read_file_content("/nonexistent/file.txt")
        assert content is None
