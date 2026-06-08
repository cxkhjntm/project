"""Tests for file ingestion service."""

import pytest
from pathlib import Path
import tempfile
import os
import uuid

from app.utils.file_filter import (
    is_allowed_extension,
    is_excluded_directory,
    is_file_too_large,
    scan_directory,
    read_file_content,
)
from app.utils.path_validator import PathValidationError
from app.services.file_ingestion import FileIngestionService


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


class TestIngestLocalFile:
    """Test FileIngestionService.ingest_local_file."""

    @pytest.fixture
    def service(self) -> FileIngestionService:
        return FileIngestionService()

    @pytest.mark.asyncio
    async def test_ingest_valid_txt_file(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test ingesting a valid .txt file."""
        test_file = tmp_path / "hello.txt"
        test_file.write_text("Hello, World!")
        room_id = str(uuid.uuid4())

        source = await service.ingest_local_file(db_session, room_id, str(test_file))

        assert source is not None
        assert source.source_type == "local_file"
        assert source.room_id == room_id
        assert source.path == str(test_file.resolve())
        assert "Hello, World!" in source.content

    @pytest.mark.asyncio
    async def test_ingest_valid_py_file(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test ingesting a valid .py file."""
        test_file = tmp_path / "script.py"
        test_file.write_text("print('hello')")
        room_id = str(uuid.uuid4())

        source = await service.ingest_local_file(db_session, room_id, str(test_file))

        assert source is not None
        assert source.source_type == "local_file"

    @pytest.mark.asyncio
    async def test_rejects_disallowed_extension(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test that files with disallowed extensions are rejected."""
        test_file = tmp_path / "binary.exe"
        test_file.write_bytes(b"\x00\x00\x00")
        room_id = str(uuid.uuid4())

        source = await service.ingest_local_file(db_session, room_id, str(test_file))
        assert source is None

    @pytest.mark.asyncio
    async def test_rejects_nonexistent_file(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test that nonexistent file raises FileNotFoundError."""
        room_id = str(uuid.uuid4())
        fake_path = str(tmp_path / "does_not_exist.txt")

        with pytest.raises(FileNotFoundError):
            await service.ingest_local_file(db_session, room_id, fake_path)

    @pytest.mark.asyncio
    async def test_rejects_dot_dot_traversal(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test that path traversal is rejected."""
        room_id = str(uuid.uuid4())
        traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")

        with pytest.raises(PathValidationError, match="traversal"):
            await service.ingest_local_file(db_session, room_id, traversal_path)

    @pytest.mark.asyncio
    async def test_rejects_tilde_path(
        self, service: FileIngestionService, db_session
    ) -> None:
        """Test that tilde expansion path is rejected."""
        room_id = str(uuid.uuid4())

        with pytest.raises(PathValidationError, match="Tilde"):
            await service.ingest_local_file(db_session, room_id, "~/secret.txt")

    @pytest.mark.asyncio
    async def test_rejects_directory(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test that directory path raises FileNotFoundError."""
        room_id = str(uuid.uuid4())

        with pytest.raises(FileNotFoundError):
            await service.ingest_local_file(db_session, room_id, str(tmp_path))

    @pytest.mark.asyncio
    async def test_content_truncated_to_budget(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test that large file content is truncated."""
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 200_000)
        room_id = str(uuid.uuid4())

        source = await service.ingest_local_file(db_session, room_id, str(test_file))

        assert source is not None
        assert len(source.content) <= 60_000

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(
        self, service: FileIngestionService, db_session, tmp_path: Path
    ) -> None:
        """Test that files exceeding size limit are rejected."""
        test_file = tmp_path / "huge.txt"
        test_file.write_bytes(b"x" * (11 * 1024 * 1024))
        room_id = str(uuid.uuid4())

        source = await service.ingest_local_file(db_session, room_id, str(test_file))
        assert source is None
