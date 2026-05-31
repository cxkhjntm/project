"""Filesystem browsing endpoints for folder selection."""

import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_directory: bool


class DirectoryListing(BaseModel):
    current_path: str
    parent_path: str | None
    entries: List[DirectoryEntry]


EXCLUDED_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "target", ".idea", ".vscode",
}


@router.get("/browse", response_model=DirectoryListing)
async def browse_directory(
    path: str = Query(default="", description="Directory path to browse. Empty = user home"),
) -> DirectoryListing:
    """List subdirectories in a given path for folder selection.

    Only returns directories (not files) and skips common excluded directories
    like node_modules, .git, etc.
    """
    if not path:
        target = Path.home()
    else:
        target = Path(path).expanduser().resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

    entries: List[DirectoryEntry] = []
    try:
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if item.name.startswith("."):
                continue
            if item.is_dir() and item.name not in EXCLUDED_DIRS:
                entries.append(
                    DirectoryEntry(
                        name=item.name,
                        path=str(item),
                        is_directory=True,
                    )
                )
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {path}")

    parent = str(target.parent) if target.parent != target else None

    return DirectoryListing(
        current_path=str(target),
        parent_path=parent,
        entries=entries,
    )
