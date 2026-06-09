"""Tests for path traversal protection utilities."""

import os
from pathlib import Path

import pytest

from app.utils.path_validator import (
    PathValidationError,
    validate_file_path,
    validate_path,
    validate_path_safety,
)


class TestPathValidationError:
    """Test custom exception class."""

    def test_is_exception(self) -> None:
        """Test PathValidationError is an Exception subclass."""
        assert issubclass(PathValidationError, Exception)

    def test_can_raise_with_message(self) -> None:
        """Test exception can be raised with a message."""
        with pytest.raises(PathValidationError, match="test error"):
            raise PathValidationError("test error")


class TestValidatePath:
    """Test validate_path function."""

    def test_valid_path_within_base(self, tmp_path: Path) -> None:
        """Test that a valid path within base directory is accepted."""
        base = str(tmp_path)
        test_path = str(tmp_path / "subdir" / "file.txt")
        result = validate_path(test_path, base)
        assert os.path.isabs(result)
        assert result.startswith(base)

    def test_rejects_dot_dot_traversal(self, tmp_path: Path) -> None:
        """Test that path with .. traversal is rejected."""
        base = str(tmp_path)
        test_path = str(tmp_path / ".." / "outside" / "file.txt")
        with pytest.raises(PathValidationError, match="traversal"):
            validate_path(test_path, base)

    def test_rejects_path_outside_base(self, tmp_path: Path) -> None:
        """Test that path outside base directory is rejected."""
        base = str(tmp_path / "allowed")
        test_path = str(tmp_path / "other" / "file.txt")
        with pytest.raises(PathValidationError):
            validate_path(test_path, base)

    def test_rejects_absolute_path_outside_base(self, tmp_path: Path) -> None:
        """Test that absolute path outside base is rejected."""
        base = str(tmp_path)
        outside = tmp_path.parent / "outside" / "file.txt"
        with pytest.raises(PathValidationError):
            validate_path(str(outside), base)

    def test_normalizes_path(self, tmp_path: Path) -> None:
        """Test that path is properly normalized."""
        base = str(tmp_path)
        test_path = str(tmp_path / "subdir" / "." / "file.txt")
        result = validate_path(test_path, base)
        assert ".." not in result
        assert "/./" not in result

    def test_accepts_base_directory_itself(self, tmp_path: Path) -> None:
        """Test that base directory path itself is valid."""
        base = str(tmp_path)
        result = validate_path(base, base)
        assert os.path.isabs(result)

    def test_accepts_nested_path(self, tmp_path: Path) -> None:
        """Test deeply nested valid path is accepted."""
        base = str(tmp_path)
        test_path = str(tmp_path / "a" / "b" / "c" / "d" / "file.txt")
        result = validate_path(test_path, base)
        assert result.startswith(base)

    def test_rejects_encoded_traversal(self, tmp_path: Path) -> None:
        """Test that encoded traversal sequences are handled."""
        base = str(tmp_path)
        test_path = str(tmp_path / "subdir" / ".." / ".." / "etc" / "passwd")
        with pytest.raises(PathValidationError, match="traversal"):
            validate_path(test_path, base)

    def test_empty_path_raises(self, tmp_path: Path) -> None:
        """Test that empty path raises error."""
        base = str(tmp_path)
        with pytest.raises(PathValidationError):
            validate_path("", base)

    def test_empty_base_raises(self, tmp_path: Path) -> None:
        """Test that empty base directory raises error."""
        test_path = str(tmp_path / "file.txt")
        with pytest.raises(PathValidationError):
            validate_path(test_path, "")


class TestValidateFilePath:
    """Test validate_file_path function."""

    def test_accepts_allowed_extension(self) -> None:
        """Test that allowed extension passes validation."""
        allowed = {".txt", ".md", ".py"}
        assert validate_file_path("document.txt", allowed) is True

    def test_rejects_disallowed_extension(self) -> None:
        """Test that disallowed extension fails validation."""
        allowed = {".txt", ".md"}
        assert validate_file_path("script.exe", allowed) is False

    def test_case_insensitive_extension(self) -> None:
        """Test that extension check is case insensitive."""
        allowed = {".txt", ".md"}
        assert validate_file_path("document.TXT", allowed) is True

    def test_handles_path_with_directories(self) -> None:
        """Test validation works with full path."""
        allowed = {".txt"}
        assert validate_file_path("/some/dir/file.txt", allowed) is True

    def test_rejects_no_extension(self) -> None:
        """Test that file without extension is rejected."""
        allowed = {".txt"}
        assert validate_file_path("Makefile", allowed) is False

    def test_empty_filename(self) -> None:
        """Test empty filename handling."""
        allowed = {".txt"}
        assert validate_file_path("", allowed) is False

    def test_dot_file(self) -> None:
        """Test dotfile handling."""
        allowed = {".txt"}
        assert validate_file_path(".gitignore", allowed) is False

    def test_multiple_dots_in_filename(self) -> None:
        """Test filename with multiple dots."""
        allowed = {".txt"}
        assert validate_file_path("file.backup.txt", allowed) is True

    def test_empty_allowed_extensions(self) -> None:
        """Test with empty allowed extensions set."""
        allowed: set[str] = set()
        assert validate_file_path("file.txt", allowed) is False


class TestValidatePathSafety:
    """Test validate_path_safety function."""

    def test_valid_absolute_path(self, tmp_path: Path) -> None:
        """Test that a valid absolute path passes."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")
        result = validate_path_safety(str(test_file))
        assert os.path.isabs(result)

    def test_rejects_dot_dot_traversal(self) -> None:
        """Test that .. traversal is rejected."""
        with pytest.raises(PathValidationError, match="traversal"):
            validate_path_safety("/some/path/../../../etc/passwd")

    def test_rejects_dot_dot_in_middle(self, tmp_path: Path) -> None:
        """Test that .. in middle of path is rejected."""
        with pytest.raises(PathValidationError, match="traversal"):
            validate_path_safety(str(tmp_path / "sub" / ".." / "other"))

    def test_rejects_tilde_prefix(self) -> None:
        """Test that ~ expansion is rejected."""
        with pytest.raises(PathValidationError, match="Tilde"):
            validate_path_safety("~/Documents/secret.txt")

    def test_rejects_tilde_with_spaces(self) -> None:
        """Test that ~ with leading spaces is rejected."""
        with pytest.raises(PathValidationError, match="Tilde"):
            validate_path_safety("  ~/file.txt")

    def test_rejects_empty_path(self) -> None:
        """Test that empty path is rejected."""
        with pytest.raises(PathValidationError, match="empty"):
            validate_path_safety("")

    def test_accepts_valid_relative_path(self, tmp_path: Path) -> None:
        """Test that a simple relative path without traversal passes."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")
        result = validate_path_safety(str(test_file))
        assert os.path.isabs(result)

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        """Test that returned path is resolved."""
        test_file = tmp_path / "sub" / "file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("content")
        result = validate_path_safety(str(test_file))
        assert ".." not in result
        assert str(test_file.resolve()) == result
