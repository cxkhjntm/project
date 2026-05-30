# Stage 2: 群聊创建 + 文件处理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户能创建群聊、上传文件、指定文件夹，为后续讨论引擎做准备。

**Architecture:** 后端新增 Room CRUD + 文件处理服务，前端新增群聊创建页和文件上传组件。遵循现有 Provider/RoleCard 的 CRUD 模式。

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + TypeScript + Tailwind (frontend), python-multipart + chardet (file handling)

---

## 文件结构

### 后端新增文件
- `backend/app/schemas/room.py` — Room 请求/响应 schema
- `backend/app/schemas/shared_source.py` — SharedSource 请求/响应 schema
- `backend/app/services/room_service.py` — Room CRUD 服务
- `backend/app/services/file_ingestion.py` — 文件扫描与内容提取
- `backend/app/routers/rooms.py` — Room API 路由
- `backend/app/routers/sources.py` — SharedSource API 路由
- `backend/app/utils/file_filter.py` — 文件过滤规则工具
- `backend/tests/test_room_service.py` — Room 服务测试
- `backend/tests/test_file_ingestion.py` — 文件处理测试

### 前端新增文件
- `frontend/src/pages/RoomCreatePage.tsx` — 群聊创建页
- `frontend/src/pages/RoomsPage.tsx` — 群聊列表页
- `frontend/src/components/room/RoomForm.tsx` — 群聊创建表单
- `frontend/src/components/room/RoomList.tsx` — 群聊列表组件
- `frontend/src/components/room/FileUpload.tsx` — 文件上传组件

### 前端修改文件
- `frontend/src/routes.tsx` — 添加群聊路由
- `frontend/src/api/client.ts` — 添加 Room/Source API 方法
- `frontend/src/types/index.ts` — 确认类型定义完整

---

## Task 1: Room Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/room.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Create Room schemas**

```python
# backend/app/schemas/room.py
"""Room schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ParticipantInput(BaseModel):
    """Schema for room participant input."""
    role_card_id: str = Field(..., description="Role card ID")
    provider_id: str = Field(..., description="Provider ID to use for this role")
    model_override: Optional[str] = Field(None, description="Override model for this role")


class RoomCreate(BaseModel):
    """Schema for creating a room."""
    name: str = Field(..., min_length=1, max_length=200, description="Room name")
    goal: str = Field(..., min_length=1, description="Discussion goal")
    mode: str = Field("code_document", description="Work mode: code_document, document, code")
    strategy: str = Field("standard", description="Discussion strategy")
    output_directory: str = Field(..., min_length=1, max_length=500, description="Output directory path")
    round_limit: int = Field(5, ge=1, le=20, description="Maximum discussion rounds")
    participants: List[ParticipantInput] = Field(..., min_length=1, description="Room participants")


class RoomUpdate(BaseModel):
    """Schema for updating a room."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    goal: Optional[str] = Field(None, min_length=1)
    mode: Optional[str] = None
    strategy: Optional[str] = None
    output_directory: Optional[str] = Field(None, min_length=1, max_length=500)
    round_limit: Optional[int] = Field(None, ge=1, le=20)


class ParticipantResponse(BaseModel):
    """Schema for participant response."""
    room_id: str
    role_card_id: str
    provider_id: str
    model_override: Optional[str] = None

    class Config:
        from_attributes = True


class RoomResponse(BaseModel):
    """Schema for room response."""
    id: str
    name: str
    goal: str
    mode: str
    strategy: str
    output_directory: str
    round_limit: int
    status: str
    created_at: datetime
    updated_at: datetime
    participants: List[ParticipantResponse] = []

    class Config:
        from_attributes = True


class RoomListItem(BaseModel):
    """Schema for room list item (without participants)."""
    id: str
    name: str
    goal: str
    mode: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Update schemas __init__.py**

```python
# backend/app/schemas/__init__.py
"""Pydantic schemas for request/response validation."""

from app.schemas.room import (
    RoomCreate,
    RoomUpdate,
    RoomResponse,
    RoomListItem,
    ParticipantInput,
    ParticipantResponse,
)

__all__ = [
    "RoomCreate",
    "RoomUpdate",
    "RoomResponse",
    "RoomListItem",
    "ParticipantInput",
    "ParticipantResponse",
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/room.py backend/app/schemas/__init__.py
git commit -m "feat(backend): add Room and Participant Pydantic schemas"
```

---

## Task 2: Room Service (CRUD)

**Files:**
- Create: `backend/app/services/room_service.py`
- Modify: `backend/app/services/__init__.py`

- [ ] **Step 1: Create Room service**

```python
# backend/app/services/room_service.py
"""Room service for CRUD operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room, RoomParticipant
from app.schemas.room import RoomCreate, RoomUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RoomService:
    """Service for room CRUD operations."""

    async def create(self, session: AsyncSession, data: RoomCreate) -> Room:
        """Create a new room with participants.
        
        Args:
            session: Database session
            data: Room creation data
            
        Returns:
            Created room with participants loaded
        """
        import uuid

        room = Room(
            id=str(uuid.uuid4()),
            name=data.name,
            goal=data.goal,
            mode=data.mode,
            strategy=data.strategy,
            output_directory=data.output_directory,
            round_limit=data.round_limit,
            status="draft",
        )
        session.add(room)
        await session.flush()

        # Add participants
        for p in data.participants:
            participant = RoomParticipant(
                room_id=room.id,
                role_card_id=p.role_card_id,
                provider_id=p.provider_id,
                model_override=p.model_override,
            )
            session.add(participant)

        await session.flush()

        # Reload with participants
        result = await session.execute(
            select(Room)
            .where(Room.id == room.id)
            .options(selectinload(Room.participants))
        )
        room = result.scalar_one()

        logger.info("Created room", room_id=room.id, name=room.name)
        return room

    async def get_all(self, session: AsyncSession) -> List[Room]:
        """Get all rooms.
        
        Args:
            session: Database session
            
        Returns:
            List of rooms
        """
        result = await session.execute(
            select(Room).order_by(Room.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, room_id: str) -> Optional[Room]:
        """Get room by ID with participants.
        
        Args:
            session: Database session
            room_id: Room ID
            
        Returns:
            Room with participants or None
        """
        result = await session.execute(
            select(Room)
            .where(Room.id == room_id)
            .options(selectinload(Room.participants))
        )
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, room_id: str, data: RoomUpdate
    ) -> Optional[Room]:
        """Update a room.
        
        Args:
            session: Database session
            room_id: Room ID
            data: Update data
            
        Returns:
            Updated room or None
        """
        room = await self.get_by_id(session, room_id)
        if not room:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(room, field, value)

        await session.flush()

        logger.info("Updated room", room_id=room.id)
        return room

    async def delete(self, session: AsyncSession, room_id: str) -> bool:
        """Delete a room (cascade deletes participants, sources, messages, artifacts).
        
        Args:
            session: Database session
            room_id: Room ID
            
        Returns:
            True if deleted, False if not found
        """
        room = await self.get_by_id(session, room_id)
        if not room:
            return False

        await session.delete(room)
        await session.flush()

        logger.info("Deleted room", room_id=room_id)
        return True

    async def update_status(
        self, session: AsyncSession, room_id: str, status: str
    ) -> Optional[Room]:
        """Update room status.
        
        Args:
            session: Database session
            room_id: Room ID
            status: New status (draft, active, completed, error)
            
        Returns:
            Updated room or None
        """
        room = await self.get_by_id(session, room_id)
        if not room:
            return None

        room.status = status
        await session.flush()

        logger.info("Updated room status", room_id=room.id, status=status)
        return room


# Singleton instance
room_service = RoomService()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/room_service.py
git commit -m "feat(backend): add Room service with CRUD operations"
```

---

## Task 3: Room API Router

**Files:**
- Create: `backend/app/routers/rooms.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create Room router**

```python
# backend/app/routers/rooms.py
"""Room API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.room import (
    RoomCreate,
    RoomListItem,
    RoomResponse,
    RoomUpdate,
)
from app.services.room_service import room_service

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    data: RoomCreate,
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Create a new room with participants."""
    room = await room_service.create(session, data)
    return RoomResponse.model_validate(room)


@router.get("", response_model=List[RoomListItem])
async def list_rooms(
    session: AsyncSession = Depends(get_session),
) -> List[RoomListItem]:
    """List all rooms."""
    rooms = await room_service.get_all(session)
    return [RoomListItem.model_validate(r) for r in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Get a room by ID with participants."""
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse.model_validate(room)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: str,
    data: RoomUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Update a room."""
    room = await room_service.update(session, room_id, data)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse.model_validate(room)


@router.delete("/{room_id}", status_code=204)
async def delete_room(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a room (cascade deletes all related data)."""
    deleted = await room_service.delete(session, room_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Room not found")
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/app/main.py` imports:
```python
from app.routers import providers, role_cards, rooms
```

Add to `create_app()` function:
```python
app.include_router(rooms.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/rooms.py backend/app/main.py
git commit -m "feat(backend): add Room CRUD API endpoints"
```

---

## Task 4: File Filter Utility

**Files:**
- Create: `backend/app/utils/file_filter.py`

- [ ] **Step 1: Create file filter utility**

```python
# backend/app/utils/file_filter.py
"""File filtering and validation utilities."""

import os
from pathlib import Path
from typing import List, Optional

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
) -> List[dict]:
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

        # Skip excluded directories
        if item.is_dir():
            if is_excluded_directory(item.name):
                continue
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

        try:
            relative = item.relative_to(dir_path)
        except ValueError:
            relative = item

        files.append({
            "path": str(item),
            "relative_path": str(relative),
            "size": size,
            "extension": item.suffix.lower(),
        })

    return files


def read_file_content(file_path: str, max_chars: int = 100_000) -> Optional[str]:
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/utils/file_filter.py
git commit -m "feat(backend): add file filter utility with directory scanning"
```

---

## Task 5: File Ingestion Service

**Files:**
- Create: `backend/app/services/file_ingestion.py`

- [ ] **Step 1: Create file ingestion service**

```python
# backend/app/services/file_ingestion.py
"""File ingestion service for processing uploaded files and folders."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shared_source import SharedSource
from app.utils.file_filter import (
    read_file_content,
    scan_directory,
    is_allowed_extension,
    is_file_too_large,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Temporary upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class FileIngestionService:
    """Service for processing files and folders."""

    async def save_uploaded_file(
        self,
        session: AsyncSession,
        room_id: str,
        filename: str,
        content: bytes,
    ) -> Optional[SharedSource]:
        """Save an uploaded file and create a SharedSource.
        
        Args:
            session: Database session
            room_id: Room ID
            filename: Original filename
            content: File content bytes
            
        Returns:
            Created SharedSource or None if file rejected
        """
        # Validate extension
        if not is_allowed_extension(filename):
            logger.warning("Rejected file: invalid extension", filename=filename)
            return None

        # Validate size
        if is_file_too_large(len(content)):
            logger.warning("Rejected file: too large", filename=filename, size=len(content))
            return None

        # Save to upload directory
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        saved_name = f"{file_id}{ext}"
        file_path = UPLOAD_DIR / saved_name

        file_path.write_bytes(content)

        # Create source record
        source = SharedSource(
            id=file_id,
            room_id=room_id,
            source_type="file",
            path=str(file_path),
            content=filename,  # Store original filename in content field
            file_count=1,
        )
        session.add(source)
        await session.flush()

        logger.info("Saved uploaded file", source_id=file_id, filename=filename)
        return source

    async def add_folder_source(
        self,
        session: AsyncSession,
        room_id: str,
        folder_path: str,
    ) -> Optional[SharedSource]:
        """Add a folder as a shared source.
        
        Args:
            session: Database session
            room_id: Room ID
            folder_path: Path to folder
            
        Returns:
            Created SharedSource or None if folder invalid
        """
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            logger.warning("Invalid folder path", path=folder_path)
            return None

        # Scan folder to count files
        try:
            files = scan_directory(folder_path)
        except Exception as e:
            logger.error("Failed to scan folder", path=folder_path, error=str(e))
            return None

        source = SharedSource(
            id=str(uuid.uuid4()),
            room_id=room_id,
            source_type="folder",
            path=folder_path,
            file_count=len(files),
        )
        session.add(source)
        await session.flush()

        logger.info("Added folder source", source_id=source.id, path=folder_path, file_count=len(files))
        return source

    async def add_text_source(
        self,
        session: AsyncSession,
        room_id: str,
        text_content: str,
    ) -> SharedSource:
        """Add pasted text as a shared source.
        
        Args:
            session: Database session
            room_id: Room ID
            text_content: Pasted text content
            
        Returns:
            Created SharedSource
        """
        source = SharedSource(
            id=str(uuid.uuid4()),
            room_id=room_id,
            source_type="text",
            content=text_content,
            file_count=0,
        )
        session.add(source)
        await session.flush()

        logger.info("Added text source", source_id=source.id, length=len(text_content))
        return source

    async def get_room_sources(
        self, session: AsyncSession, room_id: str
    ) -> List[SharedSource]:
        """Get all sources for a room.
        
        Args:
            session: Database session
            room_id: Room ID
            
        Returns:
            List of shared sources
        """
        from sqlalchemy import select

        result = await session.execute(
            select(SharedSource)
            .where(SharedSource.room_id == room_id)
            .order_by(SharedSource.created_at)
        )
        return list(result.scalars().all())

    async def delete_source(
        self, session: AsyncSession, source_id: str
    ) -> bool:
        """Delete a shared source.
        
        Args:
            session: Database session
            source_id: Source ID
            
        Returns:
            True if deleted, False if not found
        """
        from sqlalchemy import select

        result = await session.execute(
            select(SharedSource).where(SharedSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return False

        # Clean up uploaded file if it's a file source
        if source.source_type == "file" and source.path:
            try:
                Path(source.path).unlink(missing_ok=True)
            except OSError:
                pass

        await session.delete(source)
        await session.flush()

        logger.info("Deleted source", source_id=source_id)
        return True

    def get_file_content_for_room(self, room_id: str, sources: List[SharedSource]) -> str:
        """Get aggregated file content for a room's sources.
        
        Args:
            room_id: Room ID
            sources: List of shared sources
            
        Returns:
            Aggregated content string (truncated)
        """
        parts = []
        total_chars = 0
        max_total = 200_000  # 200K chars total budget

        for source in sources:
            if total_chars >= max_total:
                parts.append("\n... [content budget exhausted]")
                break

            if source.source_type == "file" and source.path:
                content = read_file_content(source.path, max_chars=50_000)
                if content:
                    header = f"\n{'='*60}\nFILE: {source.content or source.path}\n{'='*60}\n"
                    parts.append(header + content)
                    total_chars += len(content)

            elif source.source_type == "folder" and source.path:
                try:
                    files = scan_directory(source.path)
                    for f in files[:50]:  # Limit to 50 files per folder
                        if total_chars >= max_total:
                            break
                        content = read_file_content(f["path"], max_chars=20_000)
                        if content:
                            header = f"\n{'='*60}\nFILE: {f['relative_path']}\n{'='*60}\n"
                            parts.append(header + content)
                            total_chars += len(content)
                except Exception as e:
                    parts.append(f"\n[Error scanning folder: {e}]")

            elif source.source_type == "text" and source.content:
                remaining = max_total - total_chars
                text = source.content[:remaining]
                parts.append(f"\n{'='*60}\nPASTED TEXT\n{'='*60}\n{text}")
                total_chars += len(text)

        return "\n".join(parts)


# Singleton instance
file_ingestion_service = FileIngestionService()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/file_ingestion.py
git commit -m "feat(backend): add file ingestion service with folder scanning"
```

---

## Task 6: Sources API Router

**Files:**
- Create: `backend/app/schemas/shared_source.py`
- Create: `backend/app/routers/sources.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create SharedSource schemas**

```python
# backend/app/schemas/shared_source.py
"""SharedSource schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SharedSourceCreate(BaseModel):
    """Schema for creating a shared source."""
    source_type: str = Field(..., description="Source type: file, folder, text")
    path: Optional[str] = Field(None, description="Path for folder source")
    content: Optional[str] = Field(None, description="Content for text source")


class SharedSourceResponse(BaseModel):
    """Schema for shared source response."""
    id: str
    room_id: str
    source_type: str
    path: Optional[str] = None
    content: Optional[str] = None
    file_count: int
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Create Sources router**

```python
# backend/app/routers/sources.py
"""Shared source API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.shared_source import SharedSourceCreate, SharedSourceResponse
from app.services.file_ingestion import file_ingestion_service
from app.services.room_service import room_service

router = APIRouter(tags=["sources"])


@router.post(
    "/api/rooms/{room_id}/sources",
    response_model=SharedSourceResponse,
    status_code=201,
)
async def add_source(
    room_id: str,
    source_type: str = Form(...),
    path: str = Form(None),
    content: str = Form(None),
    file: UploadFile = File(None),
    session: AsyncSession = Depends(get_session),
) -> SharedSourceResponse:
    """Add a shared source to a room.
    
    For source_type='file': upload file via multipart/form-data
    For source_type='folder': provide path
    For source_type='text': provide content
    """
    # Verify room exists
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if source_type == "file":
        if not file:
            raise HTTPException(status_code=400, detail="File is required for source_type='file'")
        file_content = await file.read()
        source = await file_ingestion_service.save_uploaded_file(
            session, room_id, file.filename or "unknown", file_content
        )
        if not source:
            raise HTTPException(status_code=400, detail="File rejected: invalid extension or too large")

    elif source_type == "folder":
        if not path:
            raise HTTPException(status_code=400, detail="Path is required for source_type='folder'")
        source = await file_ingestion_service.add_folder_source(session, room_id, path)
        if not source:
            raise HTTPException(status_code=400, detail="Invalid folder path")

    elif source_type == "text":
        if not content:
            raise HTTPException(status_code=400, detail="Content is required for source_type='text'")
        source = await file_ingestion_service.add_text_source(session, room_id, content)

    else:
        raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")

    return SharedSourceResponse.model_validate(source)


@router.get("/api/rooms/{room_id}/sources", response_model=List[SharedSourceResponse])
async def list_sources(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> List[SharedSourceResponse]:
    """List all sources for a room."""
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sources = await file_ingestion_service.get_room_sources(session, room_id)
    return [SharedSourceResponse.model_validate(s) for s in sources]


@router.delete("/api/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a shared source."""
    deleted = await file_ingestion_service.delete_source(session, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
```

- [ ] **Step 3: Register router in main.py**

Add to `backend/app/main.py` imports:
```python
from app.routers import providers, role_cards, rooms, sources
```

Add to `create_app()` function:
```python
app.include_router(sources.router)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/shared_source.py backend/app/routers/sources.py backend/app/main.py
git commit -m "feat(backend): add SharedSource API with file upload support"
```

---

## Task 7: Frontend Types & API Client Updates

**Files:**
- Modify: `frontend/src/types/index.ts` (verify Room types)
- Modify: `frontend/src/api/client.ts` (verify Room/Source methods)

- [ ] **Step 1: Verify and update types**

Check `frontend/src/types/index.ts` — Room types already exist from Stage 0. Verify they match backend schemas:

```typescript
// Should already exist:
export interface Room {
  id: string;
  name: string;
  goal: string;
  mode: RoomMode;
  strategy: RoomStrategy;
  output_directory: string;
  round_limit: number;
  status: RoomStatus;
  created_at: string;
  updated_at: string;
  participants?: RoomParticipant[];
}

export interface RoomCreate {
  name: string;
  goal: string;
  mode?: RoomMode;
  strategy?: RoomStrategy;
  output_directory: string;
  round_limit?: number;
  participants: ParticipantInput[];
}

// Add if missing:
export interface ParticipantInput {
  role_card_id: string;
  provider_id: string;
  model_override?: string;
}
```

- [ ] **Step 2: Verify API client methods**

Check `frontend/src/api/client.ts` — Room methods already exist. Verify file upload method:

```typescript
// Add if missing:
async uploadRoomSource(roomId: string, formData: FormData): Promise<unknown> {
  const response = await fetch(`${this.baseUrl}/rooms/${roomId}/sources`, {
    method: 'POST',
    body: formData,  // Don't set Content-Type for FormData
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(error.detail || 'Upload failed', response.status);
  }
  return response.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend): add file upload API method and participant types"
```

---

## Task 8: Room Create Page UI

**Files:**
- Create: `frontend/src/pages/RoomCreatePage.tsx`
- Create: `frontend/src/components/room/RoomForm.tsx`
- Modify: `frontend/src/routes.tsx`

- [ ] **Step 1: Create RoomForm component**

```tsx
// frontend/src/components/room/RoomForm.tsx
import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import type { RoleCard, Provider, RoomCreate, ParticipantInput } from '@/types';

interface RoomFormProps {
  onSubmit: (data: RoomCreate) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
}

export default function RoomForm({ onSubmit, onCancel, isSubmitting }: RoomFormProps) {
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [outputDirectory, setOutputDirectory] = useState('');
  const [roundLimit, setRoundLimit] = useState(5);
  const [selectedParticipants, setSelectedParticipants] = useState<Map<string, string>>(new Map());
  
  const [roleCards, setRoleCards] = useState<RoleCard[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [rcData, pData] = await Promise.all([
          apiClient.getRoleCards(),
          apiClient.getProviders(),
        ]);
        setRoleCards(rcData as RoleCard[]);
        setProviders(pData as Provider[]);
      } catch (err) {
        console.error('Failed to load data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  const toggleParticipant = (roleId: string) => {
    setSelectedParticipants(prev => {
      const next = new Map(prev);
      if (next.has(roleId)) {
        next.delete(roleId);
      } else if (providers.length > 0) {
        next.set(roleId, providers[0].id);
      }
      return next;
    });
  };

  const updateProvider = (roleId: string, providerId: string) => {
    setSelectedParticipants(prev => {
      const next = new Map(prev);
      next.set(roleId, providerId);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const participants: ParticipantInput[] = Array.from(selectedParticipants.entries()).map(
      ([roleCardId, providerId]) => ({ role_card_id: roleCardId, provider_id: providerId })
    );

    await onSubmit({
      name,
      goal,
      output_directory: outputDirectory,
      round_limit: roundLimit,
      participants,
    });
  };

  if (isLoading) {
    return <div className="text-center py-8">加载中...</div>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          讨论室名称
        </label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="例如：登录模块设计讨论"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          讨论目标
        </label>
        <textarea
          value={goal}
          onChange={e => setGoal(e.target.value)}
          required
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="描述本次讨论要达成的目标..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          产出目录
        </label>
        <input
          type="text"
          value={outputDirectory}
          onChange={e => setOutputDirectory(e.target.value)}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="/path/to/output"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          最大轮次: {roundLimit}
        </label>
        <input
          type="range"
          min={1}
          max={10}
          value={roundLimit}
          onChange={e => setRoundLimit(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          选择专家角色
        </label>
        <div className="space-y-2">
          {roleCards.map(rc => (
            <div
              key={rc.id}
              className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                selectedParticipants.has(rc.id)
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => toggleParticipant(rc.id)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{rc.name}</span>
                  {rc.is_builtin && (
                    <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      内置
                    </span>
                  )}
                  <p className="text-sm text-gray-500 mt-0.5">{rc.description}</p>
                </div>
                <input
                  type="checkbox"
                  checked={selectedParticipants.has(rc.id)}
                  onChange={() => toggleParticipant(rc.id)}
                  className="h-4 w-4 text-primary-600"
                />
              </div>
              {selectedParticipants.has(rc.id) && providers.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <label className="text-xs text-gray-500">Provider:</label>
                  <select
                    value={selectedParticipants.get(rc.id)}
                    onChange={e => updateProvider(rc.id, e.target.value)}
                    className="ml-2 text-sm border border-gray-300 rounded px-2 py-1"
                    onClick={e => e.stopPropagation()}
                  >
                    {providers.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end space-x-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isSubmitting || selectedParticipants.size === 0}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {isSubmitting ? '创建中...' : '创建讨论室'}
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Create RoomCreatePage**

```tsx
// frontend/src/pages/RoomCreatePage.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/api/client';
import type { RoomCreate } from '@/types';
import RoomForm from '@/components/room/RoomForm';

export default function RoomCreatePage() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (data: RoomCreate) => {
    try {
      setIsSubmitting(true);
      setError(null);
      await apiClient.createRoom(data);
      navigate('/rooms');
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建讨论室失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">创建讨论室</h1>
        <p className="text-sm text-gray-500 mt-1">
          设置讨论目标，选择专家角色，开始多专家协作
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <RoomForm
          onSubmit={handleCreate}
          onCancel={() => navigate('/rooms')}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update routes**

```tsx
// frontend/src/routes.tsx
import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/shared/Layout';
import HomePage from '@/pages/HomePage';
import SettingsPage from '@/pages/SettingsPage';
import RoleCardsPage from '@/pages/RoleCardsPage';
import RoomsPage from '@/pages/RoomsPage';
import RoomCreatePage from '@/pages/RoomCreatePage';

const PlaceholderPage = ({ title }: { title: string }) => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-semibold text-gray-900 mb-2">{title}</h2>
    <p className="text-gray-600">此页面正在开发中...</p>
  </div>
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'role-cards', element: <RoleCardsPage /> },
      { path: 'rooms', element: <RoomsPage /> },
      { path: 'rooms/create', element: <RoomCreatePage /> },
      { path: 'rooms/:id', element: <PlaceholderPage title="讨论室详情" /> },
    ],
  },
]);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RoomCreatePage.tsx frontend/src/components/room/RoomForm.tsx frontend/src/routes.tsx
git commit -m "feat(frontend): add room creation page with participant selection"
```

---

## Task 9: Rooms List Page UI

**Files:**
- Create: `frontend/src/pages/RoomsPage.tsx`
- Create: `frontend/src/components/room/RoomList.tsx`

- [ ] **Step 1: Create RoomList component**

```tsx
// frontend/src/components/room/RoomList.tsx
import type { Room } from '@/types';

interface RoomListProps {
  rooms: Room[];
  onDelete: (roomId: string) => void;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  active: { label: '进行中', color: 'bg-green-100 text-green-700' },
  completed: { label: '已完成', color: 'bg-blue-100 text-blue-700' },
  error: { label: '错误', color: 'bg-red-100 text-red-700' },
};

const modeLabels: Record<string, string> = {
  code_document: '代码文档',
  document: '纯文档',
  code: '代码',
};

export default function RoomList({ rooms, onDelete }: RoomListProps) {
  if (rooms.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <p className="text-gray-500">暂无讨论室</p>
        <p className="text-sm text-gray-400 mt-1">点击上方按钮创建第一个讨论室</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {rooms.map(room => {
        const status = statusLabels[room.status] || statusLabels.draft;
        return (
          <div
            key={room.id}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900">{room.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded ${status.color}`}>
                    {status.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {modeLabels[room.mode] || room.mode}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{room.goal}</p>
                <p className="text-xs text-gray-400 mt-2">
                  创建于 {new Date(room.created_at).toLocaleString('zh-CN')}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <a
                  href={`/rooms/${room.id}`}
                  className="px-3 py-1.5 text-sm text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded-md transition-colors"
                >
                  进入
                </a>
                <button
                  onClick={() => onDelete(room.id)}
                  className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create RoomsPage**

```tsx
// frontend/src/pages/RoomsPage.tsx
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import type { Room } from '@/types';
import RoomList from '@/components/room/RoomList';

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRooms = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.getRooms();
      setRooms(data as Room[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载讨论室列表失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRooms();
  }, [fetchRooms]);

  const handleDelete = async (roomId: string) => {
    if (!window.confirm('确定要删除这个讨论室吗？所有相关数据将被永久删除。')) {
      return;
    }

    try {
      await apiClient.deleteRoom(roomId);
      await fetchRooms();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除讨论室失败');
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">讨论室</h1>
          <p className="text-sm text-gray-500 mt-1">
            管理专家讨论室，查看历史讨论
          </p>
        </div>
        <Link
          to="/rooms/create"
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          + 创建讨论室
        </Link>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-gray-500">加载中...</p>
        </div>
      ) : (
        <RoomList rooms={rooms} onDelete={handleDelete} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/RoomsPage.tsx frontend/src/components/room/RoomList.tsx
git commit -m "feat(frontend): add rooms list page with status display"
```

---

## Task 10: File Upload Component

**Files:**
- Create: `frontend/src/components/room/FileUpload.tsx`

- [ ] **Step 1: Create FileUpload component**

```tsx
// frontend/src/components/room/FileUpload.tsx
import { useState, useRef } from 'react';
import { apiClient } from '@/api/client';
import type { SharedSource } from '@/types';

interface FileUploadProps {
  roomId: string;
  onSourceAdded: (source: SharedSource) => void;
}

export default function FileUpload({ roomId, onSourceAdded }: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [folderPath, setFolderPath] = useState('');
  const [textContent, setTextContent] = useState('');
  const [activeTab, setActiveTab] = useState<'file' | 'folder' | 'text'>('file');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('source_type', 'file');
        formData.append('file', file);

        const source = await apiClient.uploadRoomSource(roomId, formData);
        onSourceAdded(source as SharedSource);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '文件上传失败');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFolderAdd = async () => {
    if (!folderPath.trim()) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('source_type', 'folder');
      formData.append('path', folderPath);

      const source = await apiClient.uploadRoomSource(roomId, formData);
      onSourceAdded(source as SharedSource);
      setFolderPath('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加文件夹失败');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTextAdd = async () => {
    if (!textContent.trim()) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('source_type', 'text');
      formData.append('content', textContent);

      const source = await apiClient.uploadRoomSource(roomId, formData);
      onSourceAdded(source as SharedSource);
      setTextContent('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加文本失败');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex border-b border-gray-200">
        {(['file', 'folder', 'text'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-primary-50 text-primary-700 border-b-2 border-primary-500'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            {tab === 'file' && '📁 上传文件'}
            {tab === 'folder' && '📂 指定文件夹'}
            {tab === 'text' && '📝 粘贴文本'}
          </button>
        ))}
      </div>

      <div className="p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {activeTab === 'file' && (
          <div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.md,.json,.csv,.py,.ts,.js,.tsx,.jsx,.html,.css,.yaml,.yml,.toml"
              onChange={e => handleFileUpload(e.target.files)}
              className="hidden"
            />
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-colors"
            >
              <div className="text-3xl mb-2">📄</div>
              <p className="text-sm text-gray-600">
                点击选择文件，或拖拽文件到此处
              </p>
              <p className="text-xs text-gray-400 mt-1">
                支持 .txt, .md, .json, .csv, .py, .ts, .js 等文本文件
              </p>
            </div>
            {isUploading && (
              <p className="text-sm text-gray-500 mt-2">上传中...</p>
            )}
          </div>
        )}

        {activeTab === 'folder' && (
          <div className="flex gap-2">
            <input
              type="text"
              value={folderPath}
              onChange={e => setFolderPath(e.target.value)}
              placeholder="输入文件夹路径，例如 /path/to/project"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={handleFolderAdd}
              disabled={isUploading || !folderPath.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isUploading ? '添加中...' : '添加'}
            </button>
          </div>
        )}

        {activeTab === 'text' && (
          <div>
            <textarea
              value={textContent}
              onChange={e => setTextContent(e.target.value)}
              placeholder="粘贴需要讨论的文本内容..."
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={handleTextAdd}
              disabled={isUploading || !textContent.trim()}
              className="mt-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isUploading ? '添加中...' : '添加文本'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/room/FileUpload.tsx
git commit -m "feat(frontend): add file upload component with folder and text support"
```

---

## Task 11: Backend Tests

**Files:**
- Create: `backend/tests/test_room_service.py`
- Create: `backend/tests/test_file_ingestion.py`

- [ ] **Step 1: Create Room service tests**

```python
# backend/tests/test_room_service.py
"""Tests for room service."""

import pytest
from app.services.room_service import RoomService
from app.schemas.room import RoomCreate, ParticipantInput


@pytest.fixture
def room_service() -> RoomService:
    """Create room service instance."""
    return RoomService()


@pytest.fixture
def sample_room_data() -> RoomCreate:
    """Sample room creation data."""
    return RoomCreate(
        name="Test Room",
        goal="Test discussion goal",
        mode="code_document",
        strategy="standard",
        output_directory="/tmp/test-output",
        round_limit=5,
        participants=[
            ParticipantInput(
                role_card_id="test-role-id",
                provider_id="test-provider-id",
            )
        ],
    )


class TestRoomService:
    """Test room service operations."""

    def test_service_instantiation(self, room_service: RoomService) -> None:
        """Test service can be instantiated."""
        assert room_service is not None

    def test_room_data_creation(self, sample_room_data: RoomCreate) -> None:
        """Test room data schema."""
        assert sample_room_data.name == "Test Room"
        assert sample_room_data.goal == "Test discussion goal"
        assert len(sample_room_data.participants) == 1
        assert sample_room_data.participants[0].role_card_id == "test-role-id"
```

- [ ] **Step 2: Create file ingestion tests**

```python
# backend/tests/test_file_ingestion.py
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_room_service.py backend/tests/test_file_ingestion.py
git commit -m "test(backend): add room service and file filter tests"
```

---

## Task 12: Run Tests & Verify

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Start backend and test API**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Test endpoints:
```bash
# Create room
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","goal":"Test goal","output_directory":"/tmp","participants":[{"role_card_id":"test","provider_id":"test"}]}'

# List rooms
curl http://localhost:8000/api/rooms

# Upload file
curl -X POST http://localhost:8000/api/rooms/{id}/sources \
  -F "source_type=file" \
  -F "file=@README.md"
```

- [ ] **Step 3: Start frontend and verify UI**

```bash
cd frontend && npm run dev
```

Navigate to http://localhost:5173/rooms and verify:
- Room list page loads
- "Create Room" button works
- Room form shows role cards and providers
- File upload component works

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete Stage 2 - room creation and file processing

- Room CRUD API with participant management
- File upload API with multipart/form-data support
- Folder scanning service with file filtering
- File content extraction with encoding detection
- SharedSource CRUD API
- Room creation page UI with participant selection
- Rooms list page with status display
- File upload component with folder and text support
- Backend tests for room service and file filter

Verification: See docs/stage2-test.md"
```

---

## Verification Checklist

- [ ] `POST /api/rooms` creates room with participants
- [ ] `GET /api/rooms` lists all rooms
- [ ] `GET /api/rooms/{id}` returns room with participants
- [ ] `PUT /api/rooms/{id}` updates room
- [ ] `DELETE /api/rooms/{id}` deletes room and cascade data
- [ ] `POST /api/rooms/{id}/sources` with file uploads file
- [ ] `POST /api/rooms/{id}/sources` with folder path adds folder
- [ ] `POST /api/rooms/{id}/sources` with text adds text
- [ ] `GET /api/rooms/{id}/sources` lists sources
- [ ] `DELETE /api/sources/{id}` deletes source
- [ ] Frontend room list page loads and displays rooms
- [ ] Frontend room creation form works
- [ ] Frontend file upload component works
- [ ] All backend tests pass
