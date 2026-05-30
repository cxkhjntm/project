# Stage 3: Discussion Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core discussion engine that enables multi-expert conversations with SSE streaming, context management, and orchestration.

**Architecture:** FastAPI backend with SSE streaming via sse-starlette, SQLAlchemy for message persistence, and React frontend with custom SSE hook for real-time updates.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), sse-starlette, httpx, React 18, TypeScript, Zustand

---

## File Structure

### Backend Files (Create/Modify)

| File | Responsibility |
|------|---------------|
| `backend/app/services/model_client.py` | Unified LLM API client with retry logic |
| `backend/app/services/context_builder.py` | System prompt assembly, file injection, rolling summary |
| `backend/app/services/orchestrator.py` | Discussion flow control, round management, convergence detection |
| `backend/app/services/message_service.py` | Message CRUD and persistence |
| `backend/app/routers/discussion.py` | Discussion API endpoints (start, messages, SSE stream) |
| `backend/app/schemas/message.py` | Message Pydantic schemas |
| `backend/app/models/message.py` | Already exists - may need minor updates |

### Frontend Files (Create/Modify)

| File | Responsibility |
|------|---------------|
| `frontend/src/pages/DiscussionPage.tsx` | Discussion workbench page |
| `frontend/src/hooks/useDiscussionSSE.ts` | SSE hook with reconnection logic |
| `frontend/src/components/discussion/` | Discussion UI components |
| `frontend/src/stores/discussionStore.ts` | Discussion state management |

---

## Task 1: Message Schemas and Service

**Files:**
- Create: `backend/app/schemas/message.py`
- Create: `backend/app/services/message_service.py`
- Test: `backend/tests/test_message_service.py`

- [ ] **Step 1: Create message schemas**

```python
# backend/app/schemas/message.py
"""Message schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation reference to source material."""
    source_id: str = Field(..., description="Source ID")
    file: Optional[str] = Field(None, description="File name")
    snippet: Optional[str] = Field(None, description="Relevant snippet")


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    room_id: str = Field(..., description="Room ID")
    sender_type: str = Field(..., description="Sender type: user|expert|orchestrator|system")
    sender_id: Optional[str] = Field(None, description="Role card ID for experts")
    content: str = Field(..., min_length=1, description="Message content")
    citations: Optional[List[Citation]] = Field(None, description="Citations")
    round: int = Field(..., ge=0, description="Discussion round number")


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: str
    room_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content: str
    citations: Optional[List[Citation]] = None
    round: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListItem(BaseModel):
    """Schema for message list item."""
    id: str
    room_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content: str
    round: int
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Write failing test for message service**

```python
# backend/tests/test_message_service.py
"""Tests for message service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.message import MessageCreate
from app.services.message_service import message_service


@pytest.mark.asyncio
async def test_create_message(db_session: AsyncSession):
    """Test creating a message."""
    # Arrange
    data = MessageCreate(
        room_id="test-room-id",
        sender_type="expert",
        sender_id="role-architect",
        content="This is a test message",
        round=1,
    )

    # Act
    message = await message_service.create(db_session, data)

    # Assert
    assert message.id is not None
    assert message.room_id == "test-room-id"
    assert message.sender_type == "expert"
    assert message.sender_id == "role-architect"
    assert message.content == "This is a test message"
    assert message.round == 1


@pytest.mark.asyncio
async def test_get_messages_by_room(db_session: AsyncSession):
    """Test getting messages by room ID."""
    # Arrange
    room_id = "test-room-id"
    for i in range(3):
        data = MessageCreate(
            room_id=room_id,
            sender_type="expert",
            sender_id=f"role-{i}",
            content=f"Message {i}",
            round=1,
        )
        await message_service.create(db_session, data)

    # Act
    messages = await message_service.get_by_room(db_session, room_id)

    # Assert
    assert len(messages) == 3
    assert all(m.room_id == room_id for m in messages)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_message_service.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.message_service'"

- [ ] **Step 4: Implement message service**

```python
# backend/app/services/message_service.py
"""Message service for CRUD operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.schemas.message import MessageCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MessageService:
    """Service for message CRUD operations."""

    async def create(self, session: AsyncSession, data: MessageCreate) -> Message:
        """Create a new message.
        
        Args:
            session: Database session
            data: Message creation data
            
        Returns:
            Created message
        """
        import uuid
        
        citations_dict = None
        if data.citations:
            citations_dict = [c.model_dump() for c in data.citations]
        
        message = Message(
            id=str(uuid.uuid4()),
            room_id=data.room_id,
            sender_type=data.sender_type,
            sender_id=data.sender_id,
            content=data.content,
            citations=citations_dict,
            round=data.round,
        )
        
        session.add(message)
        await session.flush()
        
        logger.info(
            "Created message",
            message_id=message.id,
            room_id=message.room_id,
            sender_type=message.sender_type,
            round=message.round,
        )
        return message

    async def get_by_room(
        self, 
        session: AsyncSession, 
        room_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Message]:
        """Get messages by room ID.
        
        Args:
            session: Database session
            room_id: Room ID
            limit: Optional limit
            offset: Optional offset
            
        Returns:
            List of messages
        """
        query = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.round.asc(), Message.created_at.asc())
        )
        
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(
        self, session: AsyncSession, message_id: str
    ) -> Optional[Message]:
        """Get message by ID.
        
        Args:
            session: Database session
            message_id: Message ID
            
        Returns:
            Message or None
        """
        result = await session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_round(
        self, session: AsyncSession, room_id: str
    ) -> int:
        """Get the latest round number for a room.
        
        Args:
            session: Database session
            room_id: Room ID
            
        Returns:
            Latest round number (0 if no messages)
        """
        from sqlalchemy import func
        
        result = await session.execute(
            select(func.max(Message.round))
            .where(Message.room_id == room_id)
        )
        max_round = result.scalar_one_or_none()
        return max_round or 0

    async def count_by_room(self, session: AsyncSession, room_id: str) -> int:
        """Count messages in a room.
        
        Args:
            session: Database session
            room_id: Room ID
            
        Returns:
            Message count
        """
        from sqlalchemy import func
        
        result = await session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.room_id == room_id)
        )
        return result.scalar_one()


# Singleton instance
message_service = MessageService()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_message_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/message.py backend/app/services/message_service.py backend/tests/test_message_service.py
git commit -m "feat: add message schemas and service"
```

---

## Task 2: ModelClient Unified LLM Client

**Files:**
- Create: `backend/app/services/model_client.py`
- Test: `backend/tests/test_model_client.py`

- [ ] **Step 1: Write failing test for model client**

```python
# backend/tests/test_model_client.py
"""Tests for model client."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.model_client import ModelClient, ModelResponse


@pytest.mark.asyncio
async def test_model_client_chat_completion():
    """Test chat completion call."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "Test response"
                }
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
    }
    
    # Act
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
        )
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
    
    # Assert
    assert isinstance(result, ModelResponse)
    assert result.content == "Test response"
    assert result.usage["total_tokens"] == 15


@pytest.mark.asyncio
async def test_model_client_retry_on_failure():
    """Test retry logic on API failure."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        max_retries=2,
    )
    
    # Act
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [
            Exception("Connection error"),
            AsyncMock(
                status_code=200,
                json=lambda: {
                    "choices": [{"message": {"content": "Retry success"}}],
                    "usage": {"total_tokens": 10},
                },
            ),
        ]
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
    
    # Assert
    assert result.content == "Retry success"
    assert mock_post.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_model_client.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.model_client'"

- [ ] **Step 3: Implement model client**

```python
# backend/app/services/model_client.py
"""Unified LLM API client with retry logic."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelResponse:
    """Response from LLM API."""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: Optional[str] = None


class ModelClientError(Exception):
    """Base exception for model client errors."""
    pass


class ModelClient:
    """Unified client for OpenAI-compatible LLM APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 1,
        timeout: float = 120.0,
    ):
        """Initialize model client.
        
        Args:
            base_url: API base URL (e.g., https://api.openai.com/v1)
            api_key: API key for authentication
            model: Model name (e.g., gpt-4o)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_retries: Number of retries on failure
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.timeout = timeout

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> ModelResponse:
        """Send chat completion request.
        
        Args:
            messages: List of message dicts with role and content
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences
            
        Returns:
            ModelResponse with content and usage
            
        Raises:
            ModelClientError: On API failure after retries
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if stop:
            payload["stop"] = stop
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    
                    if response.status_code != 200:
                        error_text = response.text[:500]
                        raise ModelClientError(
                            f"API returned status {response.status_code}: {error_text}"
                        )
                    
                    data = response.json()
                    
                    return ModelResponse(
                        content=data["choices"][0]["message"]["content"],
                        usage=data.get("usage", {}),
                        model=data.get("model", self.model),
                        finish_reason=data["choices"][0].get("finish_reason"),
                    )
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        "LLM API call failed, retrying",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "LLM API call failed after retries",
                        attempts=self.max_retries + 1,
                        error=str(e),
                    )
        
        raise ModelClientError(f"Failed after {self.max_retries + 1} attempts: {last_error}")

    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection.
        
        Returns:
            Dict with success, message, latency_ms
        """
        import time
        
        start_time = time.time()
        
        try:
            response = await self.chat_completion(
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "message": "Connection successful",
                "latency_ms": round(latency_ms, 2),
                "model": response.model,
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "message": str(e),
                "latency_ms": round(latency_ms, 2),
            }


# Factory function
def create_model_client(
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> ModelClient:
    """Create a model client instance.
    
    Args:
        base_url: API base URL
        api_key: API key
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens
        
    Returns:
        ModelClient instance
    """
    return ModelClient(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_model_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/model_client.py backend/tests/test_model_client.py
git commit -m "feat: add unified model client with retry logic"
```

---

## Task 3: ContextBuilder

**Files:**
- Create: `backend/app/services/context_builder.py`
- Test: `backend/tests/test_context_builder.py`

- [ ] **Step 1: Write failing test for context builder**

```python
# backend/tests/test_context_builder.py
"""Tests for context builder."""

import pytest

from app.services.context_builder import ContextBuilder


def test_build_expert_prompt():
    """Test building expert prompt with context."""
    # Arrange
    builder = ContextBuilder()
    role_data = {
        "name": "系统架构师",
        "description": "设计模块、技术边界和整体流程",
        "expertise": ["架构设计", "模块拆分"],
        "responsibilities": ["设计整体架构", "拆分模块边界"],
        "constraints": ["避免过度设计"],
    }
    
    # Act
    prompt = builder.build_expert_prompt(
        role=role_data,
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=1,
        total_rounds=5,
    )
    
    # Assert
    assert "系统架构师" in prompt
    assert "设计登录模块" in prompt
    assert "架构设计" in prompt


def test_truncate_content():
    """Test content truncation."""
    # Arrange
    builder = ContextBuilder(max_file_tokens=100)
    long_content = "word " * 1000  # ~5000 chars
    
    # Act
    truncated = builder.truncate_content(long_content)
    
    # Assert
    assert len(truncated) < len(long_content)
    assert truncated.endswith("...")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_context_builder.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.context_builder'"

- [ ] **Step 3: Implement context builder**

```python
# backend/app/services/context_builder.py
"""Context builder for discussion prompts."""

from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContextBuilder:
    """Builds context for LLM prompts in discussions."""

    def __init__(
        self,
        max_file_tokens: int = 4000,
        max_summary_tokens: int = 1000,
    ):
        """Initialize context builder.
        
        Args:
            max_file_tokens: Maximum tokens for file content
            max_summary_tokens: Maximum tokens for rolling summary
        """
        self.max_file_tokens = max_file_tokens
        self.max_summary_tokens = max_summary_tokens
        # Approximate chars per token (varies by language/model)
        self.chars_per_token = 4

    def build_expert_prompt(
        self,
        role: Dict[str, Any],
        goal: str,
        shared_sources: List[Dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        additional_context: Optional[str] = None,
    ) -> str:
        """Build prompt for an expert role.
        
        Args:
            role: Role card data
            goal: Discussion goal
            shared_sources: List of shared source dicts with content
            rolling_summary: Summary of previous discussion
            current_round: Current round number
            total_rounds: Total rounds planned
            additional_context: Optional additional context
            
        Returns:
            Assembled prompt string
        """
        # Build expertise section
        expertise = ", ".join(role.get("expertise", []))
        responsibilities = "\n".join(
            f"- {r}" for r in role.get("responsibilities", [])
        )
        constraints = "\n".join(
            f"- {c}" for c in role.get("constraints", [])
        )
        
        # Build file contents section
        file_contents = self._build_file_contents(shared_sources)
        
        # Build round context
        round_context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
        if current_round >= total_rounds - 1:
            round_context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"
        
        # Assemble prompt
        prompt = f"""你是{role['name']}，一位{role['description']}。

## 专业能力
{expertise}

## 职责
{responsibilities}

## 约束
{constraints if constraints else "无特殊约束"}

## 本次任务
目标：{goal}
工作模式：代码文档模式
{round_context}

## 共享资料
{file_contents if file_contents else "无共享资料"}

## 已有讨论
{rolling_summary if rolling_summary else "这是讨论的开始，还没有已有讨论。"}

## 本轮要求
请从你的专业角度，对当前议题发表意见。
要求：
- 引用共享资料中的具体内容时，请标注来源文件名
- 区分"资料中明确的信息"和"你的推断/建议"
- 回复控制在 500 字以内
- 如果是最后几轮，请重点总结你的核心观点"""

        if additional_context:
            prompt += f"\n\n## 补充信息\n{additional_context}"

        return prompt

    def build_orchestrator_prompt(
        self,
        goal: str,
        shared_sources: List[Dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        experts: List[Dict[str, Any]],
    ) -> str:
        """Build prompt for the orchestrator role.
        
        Args:
            goal: Discussion goal
            shared_sources: List of shared sources
            rolling_summary: Summary of previous discussion
            current_round: Current round number
            total_rounds: Total rounds planned
            experts: List of expert role dicts
            
        Returns:
            Orchestrator prompt
        """
        expert_names = ", ".join(e["name"] for e in experts)
        file_contents = self._build_file_contents(shared_sources)
        
        prompt = f"""你是专家群聊主持人。你的任务是控制讨论流程，而不是替专家完成全部内容。

本次任务目标：{goal}
当前工作模式：代码文档模式
当前轮次：第 {current_round}/{total_rounds} 轮
参与专家：{expert_names}

共享资料摘要：
{file_contents if file_contents else "无共享资料"}

已有讨论摘要：
{rolling_summary if rolling_summary else "这是讨论的开始。"}

你需要：
1. 根据任务目标安排专家发言顺序
2. 识别讨论中的冲突、遗漏和风险
3. 在信息足够时推动结论收敛
4. 如果是最后两轮，请明确要求专家总结核心观点

请用简洁的主持词引导讨论，不要超过 200 字。"""

        return prompt

    def build_synthesizer_prompt(
        self,
        goal: str,
        full_discussion: str,
    ) -> str:
        """Build prompt for synthesizing final artifact.
        
        Args:
            goal: Discussion goal
            full_discussion: Full discussion history
            
        Returns:
            Synthesizer prompt
        """
        prompt = f"""你是文档专家。请根据以下讨论记录，生成一份结构化的 Markdown 技术方案文档。

## 讨论记录
{full_discussion}

## 产出要求
请按以下结构生成文档：

# {goal}

## 1. 背景与目标
## 2. 需求拆解
## 3. 总体方案
## 4. 模块设计
## 5. 数据结构 / 接口设计
## 6. 实施步骤
## 7. 测试与验收标准
## 8. 风险与取舍
## 9. 后续迭代建议

要求：
- 内容必须来自讨论记录，不要编造
- 引用关键决策时标注是哪位专家提出的
- 结论要清晰、可执行
- 使用 Markdown 格式"""

        return prompt

    def _build_file_contents(self, shared_sources: List[Dict[str, Any]]) -> str:
        """Build file contents section.
        
        Args:
            shared_sources: List of shared source dicts
            
        Returns:
            Formatted file contents string
        """
        if not shared_sources:
            return ""
        
        sections = []
        total_chars = 0
        max_chars = self.max_file_tokens * self.chars_per_token
        
        for source in shared_sources:
            content = source.get("content", "")
            source_type = source.get("source_type", "text")
            path = source.get("path", "粘贴的文本")
            
            if not content:
                continue
            
            # Truncate if needed
            if total_chars + len(content) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:  # Only add if meaningful content fits
                    content = content[:remaining] + "\n...(内容已截断)"
                else:
                    break
            
            section = f"### 来源: {path}\n```\n{content}\n```"
            sections.append(section)
            total_chars += len(content)
        
        return "\n\n".join(sections)

    def truncate_content(self, content: str, max_tokens: Optional[int] = None) -> str:
        """Truncate content to fit token limit.
        
        Args:
            content: Content to truncate
            max_tokens: Override default max tokens
            
        Returns:
            Truncated content
        """
        max_chars = (max_tokens or self.max_file_tokens) * self.chars_per_token
        
        if len(content) <= max_chars:
            return content
        
        return content[:max_chars] + "...(内容已截断)"

    def build_rolling_summary(
        self,
        existing_summary: str,
        new_messages: List[Dict[str, Any]],
    ) -> str:
        """Build updated rolling summary.
        
        Args:
            existing_summary: Existing summary text
            new_messages: New messages to incorporate
            
        Returns:
            Updated summary
        """
        if not new_messages:
            return existing_summary
        
        # Extract key points from new messages
        new_points = []
        for msg in new_messages:
            sender = msg.get("sender_id", msg.get("sender_type", "未知"))
            content = msg.get("content", "")
            
            # Take first 200 chars as summary
            if len(content) > 200:
                content = content[:200] + "..."
            
            new_points.append(f"[{sender}]: {content}")
        
        new_summary = "\n".join(new_points)
        
        if existing_summary:
            # Combine and truncate
            combined = f"{existing_summary}\n\n最新讨论：\n{new_summary}"
        else:
            combined = f"讨论开始：\n{new_summary}"
        
        # Truncate to max summary tokens
        max_chars = self.max_summary_tokens * self.chars_per_token
        if len(combined) > max_chars:
            combined = combined[-max_chars:]  # Keep most recent
        
        return combined


# Singleton instance
context_builder = ContextBuilder()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_context_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/context_builder.py backend/tests/test_context_builder.py
git commit -m "feat: add context builder for discussion prompts"
```

---

## Task 4: Orchestrator Discussion Engine

**Files:**
- Create: `backend/app/services/orchestrator.py`
- Test: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test for orchestrator**

```python
# backend/tests/test_orchestrator.py
"""Tests for orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.orchestrator import Orchestrator, DiscussionState


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    # Arrange
    mock_session = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                role_card=MagicMock(name="Expert 1"),
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )
    
    # Act
    orchestrator = Orchestrator(session=mock_session, room=room)
    
    # Assert
    assert orchestrator.room_id == "room-1"
    assert orchestrator.goal == "Test goal"
    assert orchestrator.max_rounds == 3
    assert orchestrator.current_round == 0
    assert orchestrator.state == DiscussionState.INITIALIZED


@pytest.mark.asyncio
async def test_orchestrator_should_continue():
    """Test round limit enforcement."""
    # Arrange
    mock_session = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[MagicMock()],
    )
    orchestrator = Orchestrator(session=mock_session, room=room)
    
    # Act & Assert
    assert orchestrator.should_continue() == True
    
    orchestrator.current_round = 2
    assert orchestrator.should_continue() == True
    
    orchestrator.current_round = 3
    assert orchestrator.should_continue() == False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.orchestrator'"

- [ ] **Step 3: Implement orchestrator**

```python
# backend/app/services/orchestrator.py
"""Discussion orchestrator for managing multi-expert conversations."""

import asyncio
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room, RoomParticipant
from app.schemas.message import MessageCreate
from app.services.context_builder import context_builder
from app.services.message_service import message_service
from app.services.model_client import ModelClient, ModelClientError, create_model_client
from app.services.crypto import crypto_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscussionState(str, Enum):
    """Discussion state enum."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    CONVERGING = "converging"
    COMPLETED = "completed"
    FAILED = "failed"


class SSEEventType(str, Enum):
    """SSE event types."""
    THINKING = "thinking"
    MESSAGE = "message"
    ARTIFACT = "artifact"
    ERROR = "error"
    DONE = "done"


class Orchestrator:
    """Orchestrates multi-expert discussions."""

    def __init__(
        self,
        session: AsyncSession,
        room: Room,
        on_event: Optional[Callable] = None,
    ):
        """Initialize orchestrator.
        
        Args:
            session: Database session
            room: Room instance with participants loaded
            on_event: Callback for SSE events
        """
        self.session = session
        self.room = room
        self.on_event = on_event
        
        self.room_id = room.id
        self.goal = room.goal
        self.max_rounds = room.round_limit
        self.current_round = 0
        self.state = DiscussionState.INITIALIZED
        
        # Build participant list with providers
        self.participants = []
        for p in room.participants:
            self.participants.append({
                "role_card_id": p.role_card_id,
                "name": p.role_card.name if p.role_card else "Unknown",
                "provider_id": p.provider_id,
                "model": p.model_override or p.provider.default_model,
                "base_url": p.provider.base_url,
            })
        
        # Track discussion
        self.rolling_summary = ""
        self.shared_sources = []
        self.total_messages = 0

    def should_continue(self) -> bool:
        """Check if discussion should continue.
        
        Returns:
            True if discussion should continue
        """
        return self.current_round < self.max_rounds

    async def load_shared_sources(self) -> None:
        """Load shared sources for the room."""
        from sqlalchemy import select
        from app.models.shared_source import SharedSource
        
        result = await self.session.execute(
            select(SharedSource).where(SharedSource.room_id == self.room_id)
        )
        sources = list(result.scalars().all())
        
        self.shared_sources = [
            {
                "id": s.id,
                "source_type": s.source_type,
                "path": s.path,
                "content": s.content,
            }
            for s in sources
        ]
        
        logger.info(
            "Loaded shared sources",
            room_id=self.room_id,
            count=len(self.shared_sources),
        )

    async def emit_event(self, event_type: SSEEventType, data: Dict[str, Any]) -> None:
        """Emit SSE event.
        
        Args:
            event_type: Event type
            data: Event data
        """
        if self.on_event:
            await self.on_event(event_type, data)
        
        logger.debug("SSE event emitted", type=event_type, data=data)

    async def run_discussion(self) -> Dict[str, Any]:
        """Run the complete discussion flow.
        
        Returns:
            Discussion result summary
        """
        try:
            self.state = DiscussionState.RUNNING
            await self.load_shared_sources()
            
            while self.should_continue():
                self.current_round += 1
                
                logger.info(
                    "Starting discussion round",
                    room_id=self.room_id,
                    round=self.current_round,
                    max_rounds=self.max_rounds,
                )
                
                # Run orchestrator turn
                await self._run_orchestrator_turn()
                
                # Run each expert turn
                for participant in self.participants:
                    await self._run_expert_turn(participant)
                
                # Update rolling summary
                await self._update_rolling_summary()
                
                # Check for convergence
                if self._check_convergence():
                    logger.info(
                        "Discussion converged",
                        room_id=self.room_id,
                        round=self.current_round,
                    )
                    break
            
            self.state = DiscussionState.COMPLETED
            
            # Emit done event
            await self.emit_event(SSEEventType.DONE, {
                "room_id": self.room_id,
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
                "artifact_count": 0,  # Will be set by artifact writer
            })
            
            return {
                "success": True,
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
            }
            
        except Exception as e:
            self.state = DiscussionState.FAILED
            logger.error(
                "Discussion failed",
                room_id=self.room_id,
                error=str(e),
                round=self.current_round,
            )
            
            # Emit error event
            await self.emit_event(SSEEventType.ERROR, {
                "room_id": self.room_id,
                "error": str(e),
                "recoverable": False,
            })
            
            return {
                "success": False,
                "error": str(e),
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
            }

    async def _run_orchestrator_turn(self) -> None:
        """Run orchestrator's turn to guide discussion."""
        # Emit thinking event
        await self.emit_event(SSEEventType.THINKING, {
            "room_id": self.room_id,
            "role": "主持人",
            "status": "思考中",
        })
        
        # Build orchestrator prompt
        prompt = context_builder.build_orchestrator_prompt(
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            experts=[{"name": p["name"]} for p in self.participants],
        )
        
        # Use first participant's provider for orchestrator
        # In a more complex system, orchestrator would have its own provider
        if self.participants:
            provider = self.participants[0]
            api_key = await self._get_api_key(provider["provider_id"])
            
            client = create_model_client(
                base_url=provider["base_url"],
                api_key=api_key,
                model=provider["model"],
            )
            
            try:
                response = await client.chat_completion(
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Save orchestrator message
                message_data = MessageCreate(
                    room_id=self.room_id,
                    sender_type="orchestrator",
                    sender_id=None,
                    content=response.content,
                    round=self.current_round,
                )
                
                message = await message_service.create(self.session, message_data)
                self.total_messages += 1
                
                # Emit message event
                await self.emit_event(SSEEventType.MESSAGE, {
                    "id": message.id,
                    "room_id": self.room_id,
                    "sender_type": "orchestrator",
                    "sender_id": None,
                    "content": response.content,
                    "citations": [],
                    "round": self.current_round,
                })
                
            except ModelClientError as e:
                logger.error(
                    "Orchestrator turn failed",
                    error=str(e),
                    round=self.current_round,
                )
                # Continue with other experts even if orchestrator fails

    async def _run_expert_turn(self, participant: Dict[str, Any]) -> None:
        """Run an expert's turn.
        
        Args:
            participant: Participant dict with role info
        """
        role_card_id = participant["role_card_id"]
        role_name = participant["name"]
        
        # Emit thinking event
        await self.emit_event(SSEEventType.THINKING, {
            "room_id": self.room_id,
            "role": role_name,
            "status": "思考中",
        })
        
        # Get role card data
        from app.services.role_card_service import role_card_service
        role_card = await role_card_service.get_by_id(self.session, role_card_id)
        
        if not role_card:
            logger.warning("Role card not found", role_card_id=role_card_id)
            return
        
        role_data = {
            "name": role_card.name,
            "description": role_card.description,
            "expertise": role_card.expertise or [],
            "responsibilities": role_card.responsibilities or [],
            "constraints": role_card.constraints or [],
        }
        
        # Build expert prompt
        prompt = context_builder.build_expert_prompt(
            role=role_data,
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
        )
        
        # Get API key
        api_key = await self._get_api_key(participant["provider_id"])
        
        # Create client and call
        client = create_model_client(
            base_url=participant["base_url"],
            api_key=api_key,
            model=participant["model"],
        )
        
        try:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Save expert message
            message_data = MessageCreate(
                room_id=self.room_id,
                sender_type="expert",
                sender_id=role_card_id,
                content=response.content,
                round=self.current_round,
            )
            
            message = await message_service.create(self.session, message_data)
            self.total_messages += 1
            
            # Emit message event
            await self.emit_event(SSEEventType.MESSAGE, {
                "id": message.id,
                "room_id": self.room_id,
                "sender_type": "expert",
                "sender_id": role_card_id,
                "content": response.content,
                "citations": [],
                "round": self.current_round,
            })
            
        except ModelClientError as e:
            logger.error(
                "Expert turn failed",
                role=role_name,
                error=str(e),
                round=self.current_round,
            )
            
            # Emit error but continue
            await self.emit_event(SSEEventType.ERROR, {
                "room_id": self.room_id,
                "error": f"{role_name}发言失败: {str(e)}",
                "recoverable": True,
            })

    async def _get_api_key(self, provider_id: str) -> str:
        """Get decrypted API key for provider.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Decrypted API key
        """
        from app.services.provider_service import provider_service
        
        provider = await provider_service.get_by_id(self.session, provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")
        
        return crypto_service.decrypt(provider.api_key_encrypted)

    async def _update_rolling_summary(self) -> None:
        """Update rolling summary with recent messages."""
        # Get messages from current round
        messages = await message_service.get_by_room(
            self.session,
            self.room_id,
            limit=len(self.participants) + 1,  # +1 for orchestrator
        )
        
        # Filter to current round
        current_messages = [
            {
                "sender_type": m.sender_type,
                "sender_id": m.sender_id,
                "content": m.content,
            }
            for m in messages
            if m.round == self.current_round
        ]
        
        # Update summary
        self.rolling_summary = context_builder.build_rolling_summary(
            existing_summary=self.rolling_summary,
            new_messages=current_messages,
        )

    def _check_convergence(self) -> bool:
        """Check if discussion has converged.
        
        Returns:
            True if discussion should end
        """
        # Simple convergence: check if we've reached max rounds
        # In a more complex system, this would analyze message content
        if self.current_round >= self.max_rounds:
            return True
        
        # Could add content-based convergence detection here
        # For MVP, just use round limit
        return False


# Factory function
def create_orchestrator(
    session: AsyncSession,
    room: Room,
    on_event: Optional[Callable] = None,
) -> Orchestrator:
    """Create an orchestrator instance.
    
    Args:
        session: Database session
        room: Room with participants loaded
        on_event: SSE event callback
        
    Returns:
        Orchestrator instance
    """
    return Orchestrator(session=session, room=room, on_event=on_event)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: add discussion orchestrator with round management"
```

---

## Task 5: Discussion API Router

**Files:**
- Create: `backend/app/routers/discussion.py`
- Modify: `backend/app/main.py` (add router)
- Test: Manual testing with curl

- [ ] **Step 1: Create discussion router**

```python
# backend/app/routers/discussion.py
"""Discussion API endpoints."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.room import Room
from app.schemas.message import MessageResponse
from app.services.message_service import message_service
from app.services.orchestrator import Orchestrator, SSEEventType, create_orchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rooms", tags=["discussion"])


@router.post("/{room_id}/start")
async def start_discussion(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Start a discussion in a room.
    
    This endpoint initiates the discussion and returns an SSE stream.
    
    Args:
        room_id: Room ID
        session: Database session
        
    Returns:
        SSE stream of discussion events
    """
    from sse_starlette.sse import EventSourceResponse
    
    # Load room with participants
    result = await session.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.participants).selectinload("role_card"),
            selectinload(Room.participants).selectinload("provider"),
        )
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status not in ("draft", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Room is in '{room.status}' state, cannot start discussion"
        )
    
    if not room.participants:
        raise HTTPException(
            status_code=400,
            detail="Room has no participants"
        )
    
    # Update room status
    room.status = "running"
    await session.flush()
    
    # Create event queue
    event_queue = asyncio.Queue()
    
    async def on_event(event_type: SSEEventType, data: dict):
        """Callback to queue SSE events."""
        await event_queue.put((event_type.value, data))
    
    # Create orchestrator
    orchestrator = create_orchestrator(
        session=session,
        room=room,
        on_event=on_event,
    )
    
    async def run_discussion():
        """Run discussion in background."""
        try:
            result = await orchestrator.run_discussion()
            
            # Update room status
            room.status = "completed" if result["success"] else "failed"
            await session.commit()
            
        except Exception as e:
            logger.error("Discussion failed", error=str(e))
            room.status = "failed"
            await session.commit()
        finally:
            # Signal end of stream
            await event_queue.put(None)
    
    # Start discussion in background
    asyncio.create_task(run_discussion())
    
    async def event_generator():
        """Generate SSE events."""
        while True:
            event = await event_queue.get()
            
            if event is None:
                break
            
            event_type, data = event
            yield {
                "event": event_type,
                "data": json.dumps(data, ensure_ascii=False),
            }
    
    return EventSourceResponse(event_generator())


@router.get("/{room_id}/messages")
async def get_messages(
    room_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    """Get messages for a room.
    
    Args:
        room_id: Room ID
        limit: Optional limit
        offset: Optional offset
        session: Database session
        
    Returns:
        List of messages
    """
    # Verify room exists
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    messages = await message_service.get_by_room(
        session, room_id, limit=limit, offset=offset
    )
    
    return [
        MessageResponse.model_validate(m)
        for m in messages
    ]


@router.get("/{room_id}/messages/stream")
async def stream_messages(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Stream messages via SSE.
    
    This endpoint streams new messages as they are created.
    
    Args:
        room_id: Room ID
        session: Database session
        
    Returns:
        SSE stream of messages
    """
    from sse_starlette.sse import EventSourceResponse
    
    # Verify room exists
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Track last seen message
    last_message_count = 0
    
    async def event_generator():
        """Generate SSE events for new messages."""
        nonlocal last_message_count
        
        while True:
            # Get current messages
            messages = await message_service.get_by_room(session, room_id)
            
            # Check for new messages
            if len(messages) > last_message_count:
                new_messages = messages[last_message_count:]
                last_message_count = len(messages)
                
                for msg in new_messages:
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            MessageResponse.model_validate(msg).model_dump(),
                            ensure_ascii=False,
                        ),
                    }
            
            # Wait before checking again
            await asyncio.sleep(1)
    
    return EventSourceResponse(event_generator())
```

- [ ] **Step 2: Add router to main.py**

```python
# backend/app/main.py - Add this import and include
from app.routers import providers, role_cards, rooms, sources, discussion

# In create_app() function, add:
app.include_router(discussion.router)
```

- [ ] **Step 3: Test the endpoints**

```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# Test start discussion (will fail without valid room, but should return 404)
curl -X POST http://localhost:8000/api/rooms/nonexistent/start

# Test get messages
curl http://localhost:8000/api/rooms/nonexistent/messages
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/discussion.py backend/app/main.py
git commit -m "feat: add discussion API endpoints with SSE streaming"
```

---

## Task 6: Frontend SSE Hook

**Files:**
- Create: `frontend/src/hooks/useDiscussionSSE.ts`
- Create: `frontend/src/types/discussion.ts`

- [ ] **Step 1: Create discussion types**

```typescript
// frontend/src/types/discussion.ts
/** Discussion-related TypeScript types */

export interface DiscussionMessage {
  id: string;
  room_id: string;
  sender_type: 'user' | 'expert' | 'orchestrator' | 'system';
  sender_id: string | null;
  content: string;
  citations: Citation[] | null;
  round: number;
  created_at: string;
}

export interface Citation {
  source_id: string;
  file?: string;
  snippet?: string;
}

export interface ThinkingEvent {
  room_id: string;
  role: string;
  status: string;
}

export interface ErrorEvent {
  room_id: string;
  error: string;
  recoverable: boolean;
}

export interface DoneEvent {
  room_id: string;
  total_rounds: number;
  total_messages: number;
  artifact_count: number;
}

export type DiscussionEventType = 'thinking' | 'message' | 'artifact' | 'error' | 'done';

export interface UseDiscussionSSEReturn {
  messages: DiscussionMessage[];
  thinking: Record<string, boolean>;
  error: string | null;
  isComplete: boolean;
  startDiscussion: (roomId: string) => Promise<void>;
  reset: () => void;
}
```

- [ ] **Step 2: Create SSE hook**

```typescript
// frontend/src/hooks/useDiscussionSSE.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscussionMessage,
  DoneEvent,
  ErrorEvent,
  ThinkingEvent,
  UseDiscussionSSEReturn,
} from '../types/discussion';

/**
 * Hook for managing SSE connection to discussion stream.
 * Handles reconnection, event parsing, and state management.
 */
export function useDiscussionSSE(): UseDiscussionSSEReturn {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [thinking, setThinking] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      closeConnection();
    };
  }, []);

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const connect = useCallback((roomId: string) => {
    closeConnection();
    
    const url = `/api/rooms/${roomId}/start`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('SSE connection opened');
      reconnectAttemptsRef.current = 0;
    };

    // Handle thinking events
    eventSource.addEventListener('thinking', (event) => {
      try {
        const data: ThinkingEvent = JSON.parse(event.data);
        setThinking((prev) => ({
          ...prev,
          [data.role]: true,
        }));
      } catch (e) {
        console.error('Failed to parse thinking event:', e);
      }
    });

    // Handle message events
    eventSource.addEventListener('message', (event) => {
      try {
        const data: DiscussionMessage = JSON.parse(event.data);
        setMessages((prev) => [...prev, data]);
        
        // Clear thinking for this sender
        if (data.sender_id) {
          setThinking((prev) => ({
            ...prev,
            [data.sender_id!]: false,
          }));
        }
      } catch (e) {
        console.error('Failed to parse message event:', e);
      }
    });

    // Handle error events
    eventSource.addEventListener('error_event', (event) => {
      try {
        const data: ErrorEvent = JSON.parse(event.data);
        if (!data.recoverable) {
          setError(data.error);
          closeConnection();
        } else {
          console.warn('Recoverable error:', data.error);
        }
      } catch (e) {
        console.error('Failed to parse error event:', e);
      }
    });

    // Handle done events
    eventSource.addEventListener('done', (event) => {
      try {
        const data: DoneEvent = JSON.parse(event.data);
        console.log('Discussion complete:', data);
        setIsComplete(true);
        closeConnection();
      } catch (e) {
        console.error('Failed to parse done event:', e);
      }
    });

    // Handle generic errors
    eventSource.onerror = (event) => {
      console.error('SSE error:', event);
      
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
        
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          connect(roomId);
        }, delay);
      } else {
        setError('Connection lost. Please refresh the page.');
        closeConnection();
      }
    };
  }, [closeConnection]);

  const startDiscussion = useCallback(async (roomId: string) => {
    // Reset state
    setMessages([]);
    setThinking({});
    setError(null);
    setIsComplete(false);
    reconnectAttemptsRef.current = 0;
    
    // Connect to SSE stream
    connect(roomId);
  }, [connect]);

  const reset = useCallback(() => {
    closeConnection();
    setMessages([]);
    setThinking({});
    setError(null);
    setIsComplete(false);
    reconnectAttemptsRef.current = 0;
  }, [closeConnection]);

  return {
    messages,
    thinking,
    error,
    isComplete,
    startDiscussion,
    reset,
  };
}
```

- [ ] **Step 3: Create hooks directory if needed**

```bash
mkdir -p frontend/src/hooks
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useDiscussionSSE.ts frontend/src/types/discussion.ts
git commit -m "feat: add SSE hook for discussion streaming"
```

---

## Task 7: Discussion Page UI

**Files:**
- Create: `frontend/src/pages/DiscussionPage.tsx`
- Create: `frontend/src/components/discussion/` (components)

- [ ] **Step 1: Create discussion components**

```tsx
// frontend/src/components/discussion/MessageBubble.tsx
import React from 'react';
import type { DiscussionMessage } from '../../types/discussion';

interface MessageBubbleProps {
  message: DiscussionMessage;
  roleColor?: string;
}

const senderLabels: Record<string, string> = {
  orchestrator: '主持人',
  expert: '专家',
  user: '用户',
  system: '系统',
};

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  roleColor = '#6366f1',
}) => {
  const isOrchestrator = message.sender_type === 'orchestrator';
  const isSystem = message.sender_type === 'system';
  
  return (
    <div
      className={`flex ${isOrchestrator ? 'justify-center' : 'justify-start'} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isOrchestrator
            ? 'bg-yellow-50 border border-yellow-200'
            : isSystem
            ? 'bg-gray-100 text-gray-600'
            : 'bg-white shadow-sm border'
        }`}
      >
        {/* Sender info */}
        <div className="flex items-center gap-2 mb-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: isOrchestrator ? '#f59e0b' : roleColor }}
          />
          <span className="text-sm font-medium text-gray-700">
            {message.sender_id || senderLabels[message.sender_type] || '未知'}
          </span>
          <span className="text-xs text-gray-400">
            第 {message.round} 轮
          </span>
        </div>
        
        {/* Content */}
        <div className="text-gray-800 whitespace-pre-wrap">
          {message.content}
        </div>
        
        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            <div className="text-xs text-gray-500">
              引用: {message.citations.map((c) => c.file).join(', ')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
```

```tsx
// frontend/src/components/discussion/ThinkingIndicator.tsx
import React from 'react';

interface ThinkingIndicatorProps {
  role: string;
  isVisible: boolean;
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  role,
  isVisible,
}) => {
  if (!isVisible) return null;
  
  return (
    <div className="flex items-center gap-2 text-gray-500 mb-4 animate-pulse">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-sm">{role} 正在思考...</span>
    </div>
  );
};
```

```tsx
// frontend/src/components/discussion/RoundProgress.tsx
import React from 'react';

interface RoundProgressProps {
  currentRound: number;
  maxRounds: number;
}

export const RoundProgress: React.FC<RoundProgressProps> = ({
  currentRound,
  maxRounds,
}) => {
  const progress = (currentRound / maxRounds) * 100;
  
  return (
    <div className="mb-4">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>讨论进度</span>
        <span>第 {currentRound} / {maxRounds} 轮</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};
```

```tsx
// frontend/src/components/discussion/index.ts
export { MessageBubble } from './MessageBubble';
export { ThinkingIndicator } from './ThinkingIndicator';
export { RoundProgress } from './RoundProgress';
```

- [ ] **Step 2: Create DiscussionPage**

```tsx
// frontend/src/pages/DiscussionPage.tsx
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDiscussionSSE } from '../hooks/useDiscussionSSE';
import {
  MessageBubble,
  ThinkingIndicator,
  RoundProgress,
} from '../components/discussion';

export const DiscussionPage: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  
  const {
    messages,
    thinking,
    error,
    isComplete,
    startDiscussion,
    reset,
  } = useDiscussionSSE();

  // Start discussion on mount
  useEffect(() => {
    if (roomId) {
      startDiscussion(roomId);
    }
    
    return () => {
      reset();
    };
  }, [roomId, startDiscussion, reset]);

  // Auto-scroll to bottom
  useEffect(() => {
    const container = document.getElementById('messages-container');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  if (!roomId) {
    return <div>Room ID is required</div>;
  }

  // Get current round from latest message
  const currentRound = messages.length > 0 
    ? messages[messages.length - 1].round 
    : 0;
  const maxRounds = 5; // TODO: Get from room data

  // Get unique roles that are thinking
  const thinkingRoles = Object.entries(thinking)
    .filter(([_, isThinking]) => isThinking)
    .map(([role]) => role);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              专家讨论
            </h1>
            <p className="text-sm text-gray-500">
              Room: {roomId}
            </p>
          </div>
          
          {isComplete && (
            <button
              onClick={() => navigate(`/rooms/${roomId}/artifacts`)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              查看产出
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      <div className="px-6 pt-4">
        <RoundProgress
          currentRound={currentRound}
          maxRounds={maxRounds}
        />
      </div>

      {/* Messages */}
      <div
        id="messages-container"
        className="flex-1 overflow-y-auto px-6 py-4"
      >
        {messages.length === 0 && !error && (
          <div className="text-center text-gray-500 py-8">
            讨论即将开始...
          </div>
        )}
        
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
          />
        ))}
        
        {/* Thinking indicators */}
        {thinkingRoles.map((role) => (
          <ThinkingIndicator
            key={role}
            role={role}
            isVisible={true}
          />
        ))}
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-4">
          <div className="flex items-center gap-2 text-red-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Completion message */}
      {isComplete && (
        <div className="bg-green-50 border-t border-green-200 px-6 py-4">
          <div className="flex items-center gap-2 text-green-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>讨论已完成！共 {messages.length} 条消息</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DiscussionPage;
```

- [ ] **Step 3: Add route to App.tsx**

```tsx
// frontend/src/routes.tsx - Add DiscussionPage route
import DiscussionPage from './pages/DiscussionPage';

// Add to routes array:
{
  path: '/rooms/:roomId/discussion',
  element: <DiscussionPage />,
}
```

- [ ] **Step 4: Test the UI**

```bash
cd frontend && npm run dev
# Navigate to http://localhost:5173/rooms/test-room-id/discussion
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DiscussionPage.tsx frontend/src/components/discussion/
git commit -m "feat: add discussion page with SSE streaming UI"
```

---

## Task 8: Integration Testing

**Files:**
- Create: `docs/stage3-test.md`

- [ ] **Step 1: Create test documentation**

```markdown
# Stage 3 Verification Guide

## Backend Verification

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Discussion API
```bash
# First, create a room with participants
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Discussion",
    "goal": "设计登录模块",
    "mode": "code_document",
    "output_directory": "/tmp/output",
    "participants": [
      {"role_card_id": "role_orchestrator", "provider_id": "YOUR_PROVIDER_ID"},
      {"role_card_id": "role_pm", "provider_id": "YOUR_PROVIDER_ID"},
      {"role_card_id": "role_architect", "provider_id": "YOUR_PROVIDER_ID"}
    ]
  }'

# Start discussion (SSE stream)
curl -N http://localhost:8000/api/rooms/{room_id}/start

# Get messages
curl http://localhost:8000/api/rooms/{room_id}/messages
```

### Expected Behavior
- [ ] Discussion starts and streams SSE events
- [ ] Thinking events appear before each expert speaks
- [ ] Messages are persisted to database
- [ ] Round counter increments
- [ ] Discussion completes after max rounds

## Frontend Verification

### Discussion Page
- [ ] Page loads and starts discussion
- [ ] Messages appear in real-time
- [ ] Thinking indicators show for each expert
- [ ] Round progress bar updates
- [ ] Error messages display if API fails
- [ ] Completion state shows correctly

## API Documentation

Interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### SSE Connection Issues
- Check CORS configuration
- Verify backend is running on port 8000
- Check browser console for errors

### Database Issues
- Ensure messages table exists
- Check for migration errors
```

- [ ] **Step 2: Commit**

```bash
git add docs/stage3-test.md
git commit -m "docs: add stage 3 verification guide"
```

---

## Summary

This plan implements the core discussion engine for the Expert Room application:

1. **Message Service** - CRUD operations for discussion messages
2. **ModelClient** - Unified LLM API client with retry logic
3. **ContextBuilder** - Prompt assembly with context management
4. **Orchestrator** - Discussion flow control and round management
5. **Discussion API** - SSE streaming endpoints
6. **SSE Hook** - Frontend hook for real-time updates
7. **Discussion UI** - User interface for viewing discussions

### Key Design Decisions

- **SSE for real-time**: Using sse-starlette for efficient streaming
- **Retry logic**: ModelClient retries once on failure before reporting error
- **Rolling summary**: Context is summarized each round to manage token limits
- **Round limit**: Hard limit of 5 rounds with convergence detection
- **Error recovery**: Recoverable errors don't stop the discussion

### Next Steps

After completing Stage 3:
- Stage 4: Artifact generation and saving
- Stage 5: Integration testing and security hardening
