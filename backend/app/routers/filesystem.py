"""Filesystem browsing endpoints for folder selection."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.shared_source import SharedSourceResponse
from app.services.file_ingestion import file_ingestion_service
from app.services.room_service import room_service
from app.utils.path_validator import PathValidationError

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_directory: bool


class DirectoryListing(BaseModel):
    current_path: str
    parent_path: str | None
    entries: list[DirectoryEntry]


class ShortcutEntry(BaseModel):
    name: str
    path: str
    icon: str


class MkdirRequest(BaseModel):
    path: str
    name: str


class MkdirResponse(BaseModel):
    path: str
    success: bool


class LocalFileRequest(BaseModel):
    file_path: str


EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    ".idea",
    ".vscode",
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

    entries: list[DirectoryEntry] = []
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


@router.get("/shortcuts", response_model=list[ShortcutEntry])
async def get_shortcuts() -> list[ShortcutEntry]:
    """返回常用文件夹快捷入口（桌面、文档、下载等）。"""
    home = Path.home()
    candidates = [
        ("桌面", home / "Desktop", "🖥️"),
        ("文档", home / "Documents", "📄"),
        ("下载", home / "Downloads", "📥"),
        ("主目录", home, "🏠"),
    ]

    # Windows 特有路径
    if os.name == "nt":
        for drive_letter in ["C", "D", "E", "F"]:
            drive = Path(f"{drive_letter}:\\")
            if drive.exists():
                candidates.append((f"{drive_letter}: 盘", drive, "💾"))

    shortcuts: list[ShortcutEntry] = []
    for name, path, icon in candidates:
        if path.exists() and path.is_dir():
            shortcuts.append(ShortcutEntry(name=name, path=str(path), icon=icon))

    return shortcuts


@router.post("/mkdir", response_model=MkdirResponse)
async def create_directory(request: MkdirRequest) -> MkdirResponse:
    """在指定路径下创建新文件夹。"""
    parent = Path(request.path).expanduser().resolve()

    if not parent.exists():
        raise HTTPException(status_code=404, detail=f"父目录不存在: {request.path}")
    if not parent.is_dir():
        raise HTTPException(status_code=400, detail=f"不是目录: {request.path}")

    # 安全检查：文件夹名称
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")
    if any(c in name for c in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]):
        raise HTTPException(status_code=400, detail="文件夹名称包含非法字符")

    target = parent / name
    if target.exists():
        raise HTTPException(status_code=409, detail=f"文件夹已存在: {name}")

    try:
        target.mkdir(parents=False, exist_ok=False)
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"权限不足，无法创建: {name}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"创建文件夹失败: {e}")

    return MkdirResponse(path=str(target), success=True)


@router.post(
    "/rooms/{room_id}/sources/local",
    response_model=SharedSourceResponse,
    status_code=201,
)
async def add_local_file_source(
    room_id: str,
    request: LocalFileRequest,
    session: AsyncSession = Depends(get_session),
) -> SharedSourceResponse:
    """Add a local file as shared source (direct read, no upload)."""
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    try:
        source = await file_ingestion_service.ingest_local_file(session, room_id, request.file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    if not source:
        raise HTTPException(
            status_code=400,
            detail="File rejected: invalid extension or too large",
        )

    return SharedSourceResponse.model_validate(source)
