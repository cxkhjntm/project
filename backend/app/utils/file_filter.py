"""File filtering and validation utilities."""

from pathlib import Path

from app.config import settings


def is_allowed_extension(filename: str) -> bool:
    """Check if file extension is allowed.

    Args:
        filename: File name or path

    Returns:
        True if extension is allowed
    """
    ext = Path(filename).suffix.lower()
    return ext in settings.allowed_extensions


def is_excluded_directory(dir_name: str) -> bool:
    """Check if directory should be excluded.

    Args:
        dir_name: Directory name

    Returns:
        True if directory should be excluded
    """
    return dir_name in settings.excluded_directories


def is_file_too_large(file_size: int) -> bool:
    """Check if file exceeds size limit.

    Args:
        file_size: File size in bytes

    Returns:
        True if file is too large
    """
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    return file_size > max_bytes


def scan_directory(
    directory: str,
    recursive: bool = True,
    max_files: int = 1000,
) -> list[dict]:
    """Scan directory for allowed text files.

    Args:
        directory: Directory path to scan
        recursive: Whether to scan subdirectories
        max_files: Maximum number of files to return

    Returns:
        List of dicts with 'path', 'relative_path', 'size', 'extension'

    Raises:
        FileNotFoundError: If directory doesn't exist
        PermissionError: If directory is not readable
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    files = []

    if recursive:
        walker = dir_path.rglob("*")
    else:
        walker = dir_path.glob("*")

    for item in walker:
        if len(files) >= max_files:
            break

        # Skip directories entirely
        if item.is_dir():
            continue

        # Compute relative path and check if any parent is excluded
        try:
            relative = item.relative_to(dir_path)
        except ValueError:
            relative = item

        if any(is_excluded_directory(part) for part in relative.parts[:-1]):
            continue

        # Check extension
        if not is_allowed_extension(item.name):
            continue

        # Check size
        try:
            size = item.stat().st_size
        except OSError:
            continue

        if is_file_too_large(size):
            continue

        files.append(
            {
                "path": str(item),
                "relative_path": str(relative),
                "size": size,
                "extension": item.suffix.lower(),
            }
        )

    return files


def read_file_content(file_path: str, max_chars: int = 100_000) -> str | None:
    """Read file content with encoding detection.

    Args:
        file_path: Path to file
        max_chars: Maximum characters to read

    Returns:
        File content string, or None if unreadable
    """
    import chardet

    path = Path(file_path)
    if not path.exists():
        return None

    try:
        raw = path.read_bytes()
    except OSError:
        return None

    # Detect encoding
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        content = raw.decode(encoding, errors="replace")
    except (UnicodeDecodeError, LookupError):
        content = raw.decode("utf-8", errors="replace")

    # Truncate if too long
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n... [truncated at {max_chars} chars]"

    return content


__all__ = [
    "is_allowed_extension",
    "is_excluded_directory",
    "is_file_too_large",
    "scan_directory",
    "read_file_content",
]
