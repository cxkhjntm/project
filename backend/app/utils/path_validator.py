"""Path traversal protection utilities."""

import os
from pathlib import Path


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def validate_path(path: str, base_directory: str) -> str:
    """Validate that path is within base directory, preventing traversal attacks.

    Args:
        path: Path to validate
        base_directory: Base directory that path must be within

    Returns:
        Normalized absolute path

    Raises:
        PathValidationError: If path is invalid or outside base directory
    """
    if not path:
        raise PathValidationError("Path cannot be empty")
    if not base_directory:
        raise PathValidationError("Base directory cannot be empty")

    base = Path(base_directory).resolve()
    target = Path(path).resolve()

    if not target.is_relative_to(base):
        raise PathValidationError(
            f"Path traversal detected: '{path}' is outside base directory"
        )

    return str(target)


def validate_file_path(file_path: str, allowed_extensions: set[str]) -> bool:
    """Validate file extension against allowed set.

    Args:
        file_path: File path to validate
        allowed_extensions: Set of allowed extensions (e.g., {'.txt', '.md'})

    Returns:
        True if extension is allowed, False otherwise
    """
    if not file_path:
        return False

    ext = Path(file_path).suffix.lower()
    return ext in allowed_extensions


__all__ = [
    "PathValidationError",
    "validate_path",
    "validate_file_path",
]
