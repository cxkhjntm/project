# Stage 4: Artifact Generation & Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement artifact generation, storage, and preview functionality for the Expert Room application.

**Architecture:** Backend will generate structured Markdown artifacts from discussion results, save them to user-specified directories, and provide API endpoints for artifact management. Frontend will display artifact previews and manage artifact lifecycle.

**Tech Stack:** Python, FastAPI, SQLAlchemy, React, TypeScript, Tailwind CSS

---

## File Structure

### Backend Files to Create/Modify:
- `backend/app/services/artifact_writer.py` - Artifact generation service
- `backend/app/routers/artifacts.py` - Artifact API endpoints
- `backend/app/schemas/artifact.py` - Artifact Pydantic schemas
- `backend/app/services/discussion_log.py` - Discussion log generation

### Frontend Files to Create/Modify:
- `frontend/src/components/artifacts/ArtifactPreview.tsx` - Markdown preview component
- `frontend/src/components/artifacts/ArtifactList.tsx` - Artifact list component
- `frontend/src/pages/ArtifactPage.tsx` - Artifact page
- `frontend/src/stores/artifactStore.ts` - Artifact state management
- `frontend/src/api/artifacts.ts` - Artifact API client
- `frontend/src/types/index.ts` - Add artifact types

---

## Task 1: Backend - Artifact Writer Service

**Files:**
- Create: `backend/app/services/artifact_writer.py`
- Test: `backend/tests/test_artifact_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_artifact_writer.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.artifact_writer import ArtifactWriter

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def sample_discussion():
    return {
        "room_id": "test-room-123",
        "goal": "Design login module",
        "messages": [
            {
                "sender_type": "orchestrator",
                "content": "Let's discuss the login module design.",
                "round": 1
            },
            {
                "sender_type": "expert",
                "sender_id": "role_architect",
                "content": "I recommend using JWT tokens for authentication.",
                "round": 1
            },
            {
                "sender_type": "expert", 
                "sender_id": "role_pm",
                "content": "We need to consider password reset flow.",
                "round": 1
            }
        ]
    }

@pytest.mark.asyncio
async def test_generate_artifact(mock_session, sample_discussion):
    writer = ArtifactWriter(mock_session)
    result = await writer.generate_artifact(
        room_id="test-room-123",
        goal="Design login module",
        messages=sample_discussion["messages"],
        output_directory="/tmp/test-output"
    )
    
    assert result is not None
    assert "file_path" in result
    assert "title" in result
    assert result["artifact_type"] == "markdown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_artifact_writer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.artifact_writer'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/artifact_writer.py
"""Artifact writer service for generating structured outputs."""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactWriter:
    """Generates and saves discussion artifacts."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def generate_artifact(
        self,
        room_id: str,
        goal: str,
        messages: List[Dict[str, Any]],
        output_directory: str,
    ) -> Dict[str, Any]:
        """Generate a structured Markdown artifact from discussion messages.
        
        Args:
            room_id: Room ID
            goal: Discussion goal
            messages: List of discussion messages
            output_directory: Directory to save artifact
            
        Returns:
            Dict with artifact metadata
        """
        # Create output directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_goal = "".join(c for c in goal if c.isalnum() or c in (' ', '-', '_')).strip()
        dir_name = f"{timestamp}_{safe_goal}"
        full_output_path = os.path.join(output_directory, dir_name)
        
        os.makedirs(full_output_path, exist_ok=True)
        
        # Generate content
        content = self._build_markdown_content(goal, messages)
        
        # Write to file
        file_path = os.path.join(full_output_path, "final-plan.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Save to database
        artifact = Artifact(
            id=f"artifact_{room_id}_{timestamp}",
            room_id=room_id,
            artifact_type="markdown",
            title=f"技术方案 - {goal}",
            file_path=file_path,
            summary=f"基于讨论生成的技术方案文档，包含{len(messages)}条讨论记录",
        )
        
        self.session.add(artifact)
        await self.session.flush()
        
        logger.info(
            "Artifact generated",
            room_id=room_id,
            file_path=file_path,
            message_count=len(messages),
        )
        
        return {
            "id": artifact.id,
            "file_path": file_path,
            "title": artifact.title,
            "artifact_type": artifact.artifact_type,
        }
    
    def _build_markdown_content(self, goal: str, messages: List[Dict[str, Any]]) -> str:
        """Build structured Markdown content from discussion.
        
        Args:
            goal: Discussion goal
            messages: List of discussion messages
            
        Returns:
            Formatted Markdown string
        """
        lines = []
        lines.append(f"# {goal}\n")
        lines.append("## 1. 背景与目标\n")
        lines.append("基于专家讨论，明确项目背景和核心目标。\n")
        
        lines.append("## 2. 需求拆解\n")
        lines.append("从讨论中提取的关键需求点：\n")
        
        # Extract key points from messages
        expert_messages = [m for m in messages if m.get("sender_type") == "expert"]
        for i, msg in enumerate(expert_messages[:5], 1):
            content = msg.get("content", "")
            # Extract first sentence as key point
            first_sentence = content.split("。")[0] if "。" in content else content[:100]
            lines.append(f"{i}. {first_sentence}\n")
        
        lines.append("## 3. 总体方案\n")
        lines.append("基于讨论的架构设计：\n")
        
        # Find architect messages
        architect_messages = [
            m for m in expert_messages 
            if m.get("sender_id") == "role_architect"
        ]
        if architect_messages:
            lines.append(f"{architect_messages[0].get('content', '')}\n")
        
        lines.append("## 4. 模块设计\n")
        lines.append("## 5. 数据结构 / 接口设计\n")
        lines.append("## 6. 实施步骤\n")
        lines.append("## 7. 测试与验收标准\n")
        lines.append("## 8. 风险与取舍\n")
        lines.append("## 9. 后续迭代建议\n")
        
        lines.append("\n---\n")
        lines.append("## 讨论记录摘要\n")
        
        for msg in messages:
            sender = msg.get("sender_type", "unknown")
            content = msg.get("content", "")
            round_num = msg.get("round", 0)
            
            if sender == "orchestrator":
                lines.append(f"**主持人 (第{round_num}轮):** {content}\n")
            elif sender == "expert":
                role_id = msg.get("sender_id", "")
                role_name = "专家" if "architect" in role_id else "产品经理"
                lines.append(f"**{role_name} (第{round_num}轮):** {content}\n")
        
        return "\n".join(lines)


def create_artifact_writer(session: AsyncSession) -> ArtifactWriter:
    """Create ArtifactWriter instance."""
    return ArtifactWriter(session)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_artifact_writer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/artifact_writer.py backend/tests/test_artifact_writer.py
git commit -m "feat: add artifact writer service for generating structured outputs"
```

---

## Task 2: Backend - Discussion Log Generator

**Files:**
- Create: `backend/app/services/discussion_log.py`
- Test: `backend/tests/test_discussion_log.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_discussion_log.py
import pytest
from unittest.mock import AsyncMock
from app.services.discussion_log import DiscussionLogGenerator

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def sample_messages():
    return [
        {
            "id": "msg1",
            "sender_type": "orchestrator",
            "sender_id": None,
            "content": "Welcome to the discussion.",
            "round": 1,
            "created_at": "2026-05-30T10:00:00"
        },
        {
            "id": "msg2", 
            "sender_type": "expert",
            "sender_id": "role_architect",
            "content": "I suggest a microservices approach.",
            "round": 1,
            "created_at": "2026-05-30T10:01:00"
        }
    ]

@pytest.mark.asyncio
async def test_generate_discussion_log(mock_session, sample_messages):
    generator = DiscussionLogGenerator(mock_session)
    result = await generator.generate_log(
        room_id="test-room-123",
        goal="Design system architecture",
        messages=sample_messages,
        output_directory="/tmp/test-output"
    )
    
    assert result is not None
    assert "file_path" in result
    assert result["artifact_type"] == "text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_discussion_log.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.discussion_log'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/discussion_log.py
"""Discussion log generator service."""

import os
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscussionLogGenerator:
    """Generates formatted discussion logs."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def generate_log(
        self,
        room_id: str,
        goal: str,
        messages: List[Dict[str, Any]],
        output_directory: str,
    ) -> Dict[str, Any]:
        """Generate a formatted discussion log.
        
        Args:
            room_id: Room ID
            goal: Discussion goal
            messages: List of discussion messages
            output_directory: Directory to save log
            
        Returns:
            Dict with log metadata
        """
        # Find output directory (should exist from artifact generation)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_goal = "".join(c for c in goal if c.isalnum() or c in (' ', '-', '_')).strip()
        dir_name = f"{timestamp}_{safe_goal}"
        full_output_path = os.path.join(output_directory, dir_name)
        
        os.makedirs(full_output_path, exist_ok=True)
        
        # Generate content
        content = self._build_log_content(goal, messages)
        
        # Write to file
        file_path = os.path.join(full_output_path, "discussion-log.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Save to database
        artifact = Artifact(
            id=f"log_{room_id}_{timestamp}",
            room_id=room_id,
            artifact_type="text",
            title=f"讨论记录 - {goal}",
            file_path=file_path,
            summary=f"完整讨论记录，包含{len(messages)}条消息",
        )
        
        self.session.add(artifact)
        await self.session.flush()
        
        logger.info(
            "Discussion log generated",
            room_id=room_id,
            file_path=file_path,
            message_count=len(messages),
        )
        
        return {
            "id": artifact.id,
            "file_path": file_path,
            "title": artifact.title,
            "artifact_type": artifact.artifact_type,
        }
    
    def _build_log_content(self, goal: str, messages: List[Dict[str, Any]]) -> str:
        """Build formatted log content.
        
        Args:
            goal: Discussion goal
            messages: List of discussion messages
            
        Returns:
            Formatted log string
        """
        lines = []
        lines.append(f"# 讨论记录: {goal}\n")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")
        
        current_round = 0
        
        for msg in messages:
            round_num = msg.get("round", 0)
            sender_type = msg.get("sender_type", "unknown")
            content = msg.get("content", "")
            created_at = msg.get("created_at", "")
            
            # Add round separator
            if round_num > current_round:
                current_round = round_num
                lines.append(f"\n## 第 {current_round} 轮\n")
            
            # Format sender
            if sender_type == "orchestrator":
                sender_name = "主持人"
            elif sender_type == "expert":
                sender_id = msg.get("sender_id", "")
                if "architect" in sender_id:
                    sender_name = "系统架构师"
                elif "pm" in sender_id:
                    sender_name = "产品经理"
                elif "doc" in sender_id:
                    sender_name = "文档专家"
                else:
                    sender_name = "专家"
            else:
                sender_name = "系统"
            
            # Add message
            lines.append(f"**{sender_name}** ({created_at})")
            lines.append(f"{content}\n")
        
        lines.append("\n---\n")
        lines.append(f"讨论结束。共 {len(messages)} 条消息，{current_round} 轮讨论。\n")
        
        return "\n".join(lines)


def create_discussion_log_generator(session: AsyncSession) -> DiscussionLogGenerator:
    """Create DiscussionLogGenerator instance."""
    return DiscussionLogGenerator(session)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_discussion_log.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/discussion_log.py backend/tests/test_discussion_log.py
git commit -m "feat: add discussion log generator service"
```

---

## Task 3: Backend - Artifact Schemas

**Files:**
- Create: `backend/app/schemas/artifact.py`

- [ ] **Step 1: Create artifact schemas**

```python
# backend/app/schemas/artifact.py
"""Artifact Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArtifactBase(BaseModel):
    """Base artifact schema."""
    artifact_type: str = Field(..., description="Type of artifact: markdown, text, code, csv")
    title: str = Field(..., max_length=200, description="Artifact title")
    file_path: str = Field(..., max_length=500, description="Path to artifact file")
    summary: Optional[str] = Field(None, description="Brief summary of artifact content")


class ArtifactCreate(ArtifactBase):
    """Schema for creating artifacts."""
    room_id: str = Field(..., description="Room ID")


class ArtifactResponse(ArtifactBase):
    """Schema for artifact responses."""
    id: str = Field(..., description="Artifact ID")
    room_id: str = Field(..., description="Room ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class ArtifactContent(BaseModel):
    """Schema for artifact content."""
    id: str = Field(..., description="Artifact ID")
    content: str = Field(..., description="File content")
    file_path: str = Field(..., description="File path")


class SynthesizeRequest(BaseModel):
    """Schema for synthesize request."""
    output_directory: Optional[str] = Field(None, description="Custom output directory")


class SynthesizeResponse(BaseModel):
    """Schema for synthesize response."""
    success: bool = Field(..., description="Whether synthesis succeeded")
    artifacts: list[ArtifactResponse] = Field(default_factory=list, description="Generated artifacts")
    message: str = Field(..., description="Status message")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/artifact.py
git commit -m "feat: add artifact Pydantic schemas"
```

---

## Task 4: Backend - Artifact API Router

**Files:**
- Create: `backend/app/routers/artifacts.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Create artifacts router**

```python
# backend/app/routers/artifacts.py
"""Artifact API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.room import Room, RoomParticipant
from app.models.artifact import Artifact
from app.schemas.artifact import (
    ArtifactResponse,
    ArtifactContent,
    SynthesizeRequest,
    SynthesizeResponse,
)
from app.services.artifact_writer import create_artifact_writer
from app.services.discussion_log import create_discussion_log_generator
from app.services.message_service import message_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["artifacts"])


@router.post("/rooms/{room_id}/synthesize", response_model=SynthesizeResponse)
async def synthesize_artifacts(
    room_id: str,
    request: SynthesizeRequest = SynthesizeRequest(),
    session: AsyncSession = Depends(get_session),
):
    """Generate artifacts from discussion.
    
    Args:
        room_id: Room ID
        request: Synthesize request with optional output directory
        session: Database session
        
    Returns:
        SynthesizeResponse with generated artifacts
    """
    # Get room with participants
    result = await session.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.participants).selectinload(RoomParticipant.role_card),
        )
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Room is in '{room.status}' state, must be 'completed' to synthesize"
        )
    
    # Get messages
    messages = await message_service.get_by_room(session, room_id)
    message_list = [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "sender_id": m.sender_id,
            "content": m.content,
            "round": m.round,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    
    if not message_list:
        raise HTTPException(
            status_code=400,
            detail="No messages found in room"
        )
    
    # Use custom output directory or room's default
    output_dir = request.output_directory or room.output_directory
    
    try:
        # Generate main artifact
        artifact_writer = create_artifact_writer(session)
        artifact_result = await artifact_writer.generate_artifact(
            room_id=room_id,
            goal=room.goal,
            messages=message_list,
            output_directory=output_dir,
        )
        
        # Generate discussion log
        log_generator = create_discussion_log_generator(session)
        log_result = await log_generator.generate_log(
            room_id=room_id,
            goal=room.goal,
            messages=message_list,
            output_directory=output_dir,
        )
        
        await session.commit()
        
        # Get saved artifacts
        artifacts_result = await session.execute(
            select(Artifact).where(Artifact.room_id == room_id)
        )
        artifacts = artifacts_result.scalars().all()
        
        return SynthesizeResponse(
            success=True,
            artifacts=[ArtifactResponse.model_validate(a) for a in artifacts],
            message=f"成功生成 {len(artifacts)} 个产出文件",
        )
        
    except Exception as e:
        logger.error("Synthesis failed", room_id=room_id, error=str(e))
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"产出生成失败: {str(e)}"
        )


@router.get("/rooms/{room_id}/artifacts", response_model=List[ArtifactResponse])
async def get_room_artifacts(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get artifacts for a room.
    
    Args:
        room_id: Room ID
        session: Database session
        
    Returns:
        List of artifacts
    """
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    artifacts_result = await session.execute(
        select(Artifact)
        .where(Artifact.room_id == room_id)
        .order_by(Artifact.created_at.desc())
    )
    artifacts = artifacts_result.scalars().all()
    
    return [ArtifactResponse.model_validate(a) for a in artifacts]


@router.get("/artifacts/{artifact_id}/content", response_model=ArtifactContent)
async def get_artifact_content(
    artifact_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get artifact content.
    
    Args:
        artifact_id: Artifact ID
        session: Database session
        
    Returns:
        Artifact content
    """
    result = await session.execute(
        select(Artifact).where(Artifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    try:
        with open(artifact.file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Artifact file not found on disk"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read artifact: {str(e)}"
        )
    
    return ArtifactContent(
        id=artifact.id,
        content=content,
        file_path=artifact.file_path,
    )
```

- [ ] **Step 2: Add router to main app**

```python
# backend/app/main.py (add to existing routers)
from app.routers.artifacts import router as artifacts_router

app.include_router(artifacts_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/artifacts.py backend/app/main.py
git commit -m "feat: add artifact API endpoints (synthesize, list, content)"
```

---

## Task 5: Frontend - Artifact Types and API Client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/artifacts.ts`

- [ ] **Step 1: Add artifact types**

```typescript
// frontend/src/types/index.ts (add to existing types)

export interface Artifact {
  id: string;
  room_id: string;
  artifact_type: 'markdown' | 'text' | 'code' | 'csv';
  title: string;
  file_path: string;
  summary?: string;
  created_at: string;
}

export interface ArtifactContent {
  id: string;
  content: string;
  file_path: string;
}

export interface SynthesizeResponse {
  success: boolean;
  artifacts: Artifact[];
  message: string;
}
```

- [ ] **Step 2: Create artifact API client**

```typescript
// frontend/src/api/artifacts.ts
import { Artifact, ArtifactContent, SynthesizeResponse } from '../types';

const API_BASE = 'http://localhost:8000/api';

export const artifactApi = {
  /**
   * Generate artifacts from discussion
   */
  async synthesize(roomId: string, outputDirectory?: string): Promise<SynthesizeResponse> {
    const response = await fetch(`${API_BASE}/rooms/${roomId}/synthesize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        output_directory: outputDirectory,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to synthesize artifacts');
    }

    return response.json();
  },

  /**
   * Get artifacts for a room
   */
  async getByRoom(roomId: string): Promise<Artifact[]> {
    const response = await fetch(`${API_BASE}/rooms/${roomId}/artifacts`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get artifacts');
    }

    return response.json();
  },

  /**
   * Get artifact content
   */
  async getContent(artifactId: string): Promise<ArtifactContent> {
    const response = await fetch(`${API_BASE}/artifacts/${artifactId}/content`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get artifact content');
    }

    return response.json();
  },
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/artifacts.ts
git commit -m "feat: add artifact types and API client"
```

---

## Task 6: Frontend - Artifact Store

**Files:**
- Create: `frontend/src/stores/artifactStore.ts`

- [ ] **Step 1: Create artifact store**

```typescript
// frontend/src/stores/artifactStore.ts
import { create } from 'zustand';
import { Artifact, ArtifactContent } from '../types';
import { artifactApi } from '../api/artifacts';

interface ArtifactState {
  artifacts: Artifact[];
  currentContent: ArtifactContent | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchArtifacts: (roomId: string) => Promise<void>;
  fetchContent: (artifactId: string) => Promise<void>;
  synthesize: (roomId: string, outputDirectory?: string) => Promise<boolean>;
  clearContent: () => void;
  clearError: () => void;
}

export const useArtifactStore = create<ArtifactState>((set, get) => ({
  artifacts: [],
  currentContent: null,
  isLoading: false,
  error: null,

  fetchArtifacts: async (roomId: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const artifacts = await artifactApi.getByRoom(roomId);
      set({ artifacts, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch artifacts',
        isLoading: false 
      });
    }
  },

  fetchContent: async (artifactId: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const content = await artifactApi.getContent(artifactId);
      set({ currentContent: content, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch content',
        isLoading: false 
      });
    }
  },

  synthesize: async (roomId: string, outputDirectory?: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const result = await artifactApi.synthesize(roomId, outputDirectory);
      
      if (result.success) {
        set({ 
          artifacts: result.artifacts,
          isLoading: false 
        });
        return true;
      } else {
        set({ 
          error: result.message,
          isLoading: false 
        });
        return false;
      }
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to synthesize',
        isLoading: false 
      });
      return false;
    }
  },

  clearContent: () => {
    set({ currentContent: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/artifactStore.ts
git commit -m "feat: add artifact state management store"
```

---

## Task 7: Frontend - Artifact Preview Component

**Files:**
- Create: `frontend/src/components/artifacts/ArtifactPreview.tsx`

- [ ] **Step 1: Create artifact preview component**

```typescript
// frontend/src/components/artifacts/ArtifactPreview.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArtifactContent } from '../../types';

interface ArtifactPreviewProps {
  content: ArtifactContent | null;
  isLoading: boolean;
  onClose: () => void;
}

export const ArtifactPreview: React.FC<ArtifactPreviewProps> = ({
  content,
  isLoading,
  onClose,
}) => {
  if (!content && !isLoading) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              产出预览
            </h2>
            {content && (
              <p className="text-sm text-gray-500 mt-1">
                {content.file_path}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">加载中...</span>
            </div>
          ) : content ? (
            <div className="prose prose-lg max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => (
                    <h1 className="text-2xl font-bold text-gray-900 mb-4">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-xl font-semibold text-gray-800 mb-3 mt-6">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-medium text-gray-700 mb-2 mt-4">{children}</h3>
                  ),
                  p: ({ children }) => (
                    <p className="text-gray-600 mb-4 leading-relaxed">{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside text-gray-600 mb-4 space-y-1">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside text-gray-600 mb-4 space-y-1">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-gray-600">{children}</li>
                  ),
                  code: ({ children, className }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm">
                          {children}
                        </code>
                      );
                    }
                    return (
                      <code className={className}>
                        {children}
                      </code>
                    );
                  },
                  pre: ({ children }) => (
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto mb-4">
                      {children}
                    </pre>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 mb-4">
                      {children}
                    </blockquote>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto mb-4">
                      <table className="min-w-full divide-y divide-gray-200">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="px-4 py-2 bg-gray-50 text-left text-sm font-medium text-gray-700">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-4 py-2 text-sm text-gray-600 border-t">
                      {children}
                    </td>
                  ),
                }}
              >
                {content.content}
              </ReactMarkdown>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/artifacts/ArtifactPreview.tsx
git commit -m "feat: add artifact preview component with markdown rendering"
```

---

## Task 8: Frontend - Artifact List Component

**Files:**
- Create: `frontend/src/components/artifacts/ArtifactList.tsx`

- [ ] **Step 1: Create artifact list component**

```typescript
// frontend/src/components/artifacts/ArtifactList.tsx
import React from 'react';
import { Artifact } from '../../types';

interface ArtifactListProps {
  artifacts: Artifact[];
  onViewContent: (artifactId: string) => void;
  isLoading?: boolean;
}

export const ArtifactList: React.FC<ArtifactListProps> = ({
  artifacts,
  onViewContent,
  isLoading = false,
}) => {
  if (artifacts.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">暂无产出</h3>
        <p className="mt-1 text-sm text-gray-500">
          讨论完成后生成产出文件
        </p>
      </div>
    );
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'markdown':
        return (
          <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case 'text':
        return (
          <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        );
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'markdown':
        return 'Markdown';
      case 'text':
        return '文本';
      case 'code':
        return '代码';
      case 'csv':
        return 'CSV';
      default:
        return type;
    }
  };

  return (
    <div className="space-y-3">
      {artifacts.map((artifact) => (
        <div
          key={artifact.id}
          className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-0.5">
                {getTypeIcon(artifact.artifact_type)}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 truncate">
                  {artifact.title}
                </h4>
                <div className="mt-1 flex items-center space-x-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                    {getTypeLabel(artifact.artifact_type)}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(artifact.created_at).toLocaleString('zh-CN')}
                  </span>
                </div>
                {artifact.summary && (
                  <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                    {artifact.summary}
                  </p>
                )}
              </div>
            </div>
            
            <button
              onClick={() => onViewContent(artifact.id)}
              disabled={isLoading}
              className="ml-4 flex-shrink-0 px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '加载中...' : '查看'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/artifacts/ArtifactList.tsx
git commit -m "feat: add artifact list component"
```

---

## Task 9: Frontend - Artifact Page

**Files:**
- Create: `frontend/src/pages/ArtifactPage.tsx`
- Modify: `frontend/src/routes.tsx` (add route)

- [ ] **Step 1: Create artifact page**

```typescript
// frontend/src/pages/ArtifactPage.tsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useArtifactStore } from '../stores/artifactStore';
import { ArtifactList } from '../components/artifacts/ArtifactList';
import { ArtifactPreview } from '../components/artifacts/ArtifactPreview';

export const ArtifactPage: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const [showPreview, setShowPreview] = useState(false);
  
  const {
    artifacts,
    currentContent,
    isLoading,
    error,
    fetchArtifacts,
    fetchContent,
    synthesize,
    clearContent,
    clearError,
  } = useArtifactStore();

  useEffect(() => {
    if (roomId) {
      fetchArtifacts(roomId);
    }
  }, [roomId, fetchArtifacts]);

  const handleSynthesize = async () => {
    if (!roomId) return;
    
    const success = await synthesize(roomId);
    if (success) {
      // Refresh artifacts list
      await fetchArtifacts(roomId);
    }
  };

  const handleViewContent = async (artifactId: string) => {
    await fetchContent(artifactId);
    setShowPreview(true);
  };

  const handleClosePreview = () => {
    setShowPreview(false);
    clearContent();
  };

  if (!roomId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium text-gray-900">未找到房间</h2>
          <p className="mt-1 text-sm text-gray-500">请提供有效的房间ID</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => navigate(-1)}
                className="mr-4 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <h1 className="text-lg font-semibold text-gray-900">产出管理</h1>
            </div>
            
            <button
              onClick={handleSynthesize}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  生成中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  生成产出
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">错误</h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{error}</p>
                </div>
                <div className="mt-4">
                  <button
                    onClick={clearError}
                    className="text-sm font-medium text-red-800 hover:text-red-900"
                  >
                    关闭
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Artifacts list */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">产出文件</h2>
            <p className="mt-1 text-sm text-gray-500">
              讨论生成的文档和记录
            </p>
          </div>
          
          <div className="p-6">
            <ArtifactList
              artifacts={artifacts}
              onViewContent={handleViewContent}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>

      {/* Preview modal */}
      {showPreview && (
        <ArtifactPreview
          content={currentContent}
          isLoading={isLoading}
          onClose={handleClosePreview}
        />
      )}
    </div>
  );
};
```

- [ ] **Step 2: Add route to routes.tsx**

```typescript
// frontend/src/routes.tsx (add to existing routes)
import { ArtifactPage } from './pages/ArtifactPage';

// Add to routes array:
{
  path: '/rooms/:roomId/artifacts',
  element: <ArtifactPage />,
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ArtifactPage.tsx frontend/src/routes.tsx
git commit -m "feat: add artifact page with preview functionality"
```

---

## Task 10: Integration - Update Discussion Page

**Files:**
- Modify: `frontend/src/pages/DiscussionPage.tsx`

- [ ] **Step 1: Add artifact generation button to discussion page**

```typescript
// frontend/src/pages/DiscussionPage.tsx (add after discussion completes)

import { useArtifactStore } from '../stores/artifactStore';
import { useNavigate } from 'react-router-dom';

// Add inside component:
const { synthesize, isLoading: isSynthesizing } = useArtifactStore();
const navigate = useNavigate();

const handleGenerateArtifacts = async () => {
  if (!roomId) return;
  
  const success = await synthesize(roomId);
  if (success) {
    navigate(`/rooms/${roomId}/artifacts`);
  }
};

// Add to JSX after discussion completes:
{room?.status === 'completed' && (
  <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
    <div className="flex items-center justify-between">
      <div>
        <h3 className="text-sm font-medium text-blue-800">讨论已完成</h3>
        <p className="mt-1 text-sm text-blue-600">
          生成结构化产出文档
        </p>
      </div>
      <button
        onClick={handleGenerateArtifacts}
        disabled={isSynthesizing}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSynthesizing ? '生成中...' : '生成产出'}
      </button>
    </div>
  </div>
)}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DiscussionPage.tsx
git commit -m "feat: add artifact generation button to discussion page"
```

---

## Verification Steps

### Backend Verification

1. **Run backend tests:**
```bash
cd backend
python -m pytest tests/test_artifact_writer.py tests/test_discussion_log.py -v
```

2. **Start backend server:**
```bash
cd backend
uvicorn app.main:app --reload
```

3. **Test API endpoints:**
```bash
# Synthesize artifacts
curl -X POST http://localhost:8000/api/rooms/{room_id}/synthesize

# Get room artifacts
curl http://localhost:8000/api/rooms/{room_id}/artifacts

# Get artifact content
curl http://localhost:8000/api/artifacts/{artifact_id}/content
```

### Frontend Verification

1. **Start frontend dev server:**
```bash
cd frontend
npm run dev
```

2. **Test artifact flow:**
   - Navigate to a completed discussion
   - Click "生成产出" button
   - Verify artifacts are generated
   - Click "查看" to preview artifact
   - Verify markdown renders correctly

3. **Check artifact list:**
   - Navigate to `/rooms/{roomId}/artifacts`
   - Verify artifacts list displays correctly
   - Test preview modal functionality

### Integration Verification

1. **End-to-end flow:**
   - Create a room with participants
   - Start and complete a discussion
   - Generate artifacts
   - Preview and verify content

2. **File system verification:**
```bash
# Check output directory
ls -la /path/to/output/directory/
# Should contain: final-plan.md, discussion-log.md
```

---

## Success Criteria

- [ ] ArtifactWriter generates structured Markdown from discussion
- [ ] Discussion log generator creates formatted logs
- [ ] Artifact API endpoints work correctly
- [ ] Frontend displays artifact list
- [ ] Artifact preview renders Markdown correctly
- [ ] Integration with discussion flow works
- [ ] Files are saved to specified directory
- [ ] All tests pass
- [ ] No TypeScript/Python errors

---

## Notes

- Follow existing code patterns in the codebase
- Use structlog for logging with appropriate context
- Handle errors gracefully with user-friendly messages
- Ensure proper async/await usage
- Maintain consistent naming conventions
- Add appropriate type hints (Python) and types (TypeScript)
