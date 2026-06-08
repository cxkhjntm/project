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


def validate_output_directory(path: str) -> str:
    """Validate that output directory is an absolute path without traversal attempts.

    Args:
        path: Output directory path to validate

    Returns:
        Validated path (original string preserved)

    Raises:
        PathValidationError: If path is invalid, relative, or contains traversal
    """
    if not path:
        raise PathValidationError("Output directory cannot be empty")

    p = Path(path)

    # Reject relative paths: accept Unix absolute (/) and Windows absolute (C:\)
    if not (p.is_absolute() or path.startswith('/')):
        raise PathValidationError(
            f"Output directory must be an absolute path, got: '{path}'"
        )

    if '..' in p.parts:
        raise PathValidationError(
            f"Path traversal detected in output directory: '{path}'"
        )

    return path


def validate_path_safety(file_path: str) -> str:
    """Validate path safety for local file access (no base directory constraint).

    Checks for common path traversal and injection patterns:
    - Rejects paths containing '..' segments
    - Rejects paths starting with '~' (home directory expansion)
    - Rejects empty paths

    Args:
        file_path: Path to validate

    Returns:
        Resolved absolute path

    Raises:
        PathValidationError: If path contains dangerous patterns
    """
    if not file_path:
        raise PathValidationError("Path cannot be empty")

    p = Path(file_path)

    if file_path.strip().startswith("~"):
        raise PathValidationError(
            f"Tilde expansion not allowed: '{file_path}'"
        )

    if ".." in p.parts:
        raise PathValidationError(
            f"Path traversal detected: '{file_path}' contains '..'"
        )

    resolved = p.resolve()
    return str(resolved)


__all__ = [
    "PathValidationError",
    "validate_path",
    "validate_file_path",
    "validate_output_directory",
    "validate_path_safety",
]
