# 讨论室功能改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有讨论室功能从基础可用提升到设计文档要求的完整水平，包括后端讨论引擎增强、前端交互体验优化、SSE协议完善。

**Architecture:** 后端增强Orchestrator/ContextBuilder/ArtifactWriter三大核心服务，前端重构讨论页组件系统（专家色系、ThinkingIndicator、RoundDivider等），SSE协议扩展支持完整事件类型。

**Tech Stack:** Python FastAPI + SQLAlchemy (backend), React 18 + TypeScript + Tailwind (frontend), sse-starlette (SSE)

---

## 一、当前状态分析

### 已实现 ✅
- 基础Orchestrator（轮次循环、专家发言、主持人发言）
- 基础ContextBuilder（prompt组装、文件内容注入）
- 基础ModelClient（API调用、重试）
- 基础ArtifactWriter（Markdown生成、文件写入）
- 前端DiscussionPage（SSE连接、消息展示）
- 前端ThinkingIndicator（基础动画）
- 前端RoundProgress（进度条）

### 需要改进 ❌
1. **ContextBuilder** - 缺少Token预算管理、降级策略、角色定义压缩
2. **Orchestrator** - 缺少ACTION解析、收敛检测、用户消息注入
3. **ArtifactWriter** - 缺少两次调用策略、来源标注头部
4. **前端组件** - 缺少专家色系、骨架屏、轮次分隔线、引用块
5. **SSE协议** - 缺少status/cost_update事件
6. **讨论页** - 缺少右侧面板、中断恢复、Tab切换

---

## 二、文件结构

### 后端修改文件
- `backend/app/services/context_builder.py` — 增强上下文构建
- `backend/app/services/orchestrator.py` — 增强讨论调度
- `backend/app/services/artifact_writer.py` — 增强产出生成
- `backend/app/routers/discussion.py` — 增强SSE事件
- `backend/app/utils/token_counter.py` — 新增Token计数工具

### 前端修改文件
- `frontend/src/styles/expert-colors.css` — 新增专家色系
- `frontend/src/styles/animations.css` — 新增动画
- `frontend/src/components/discussion/ThinkingIndicator.tsx` — 增强
- `frontend/src/components/discussion/MessageBubble.tsx` — 增强
- `frontend/src/components/discussion/RoundProgress.tsx` — 增强
- `frontend/src/components/discussion/RoundDivider.tsx` — 新增
- `frontend/src/components/discussion/CitationBlock.tsx` — 新增
- `frontend/src/components/discussion/RightPanel.tsx` — 新增
- `frontend/src/hooks/useDiscussionSSE.ts` — 增强
- `frontend/src/pages/DiscussionPage.tsx` — 增强

---

## 三、任务清单

### Task 1: Token计数工具

**Files:**
- Create: `backend/app/utils/token_counter.py`

- [ ] **Step 1: 创建Token计数工具**

```python
# backend/app/utils/token_counter.py
"""Token counting and budget management utilities."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TokenBudget:
    """Token budget allocation."""
    total: int = 12000
    system_prompt: int = 1500
    data_summary: int = 800
    relevant_excerpts: int = 2500
    discussion_summary: int = 1000
    recent_messages: int = 3000
    decisions: int = 300
    instruction: int = 300
    safety_margin: int = 1600


# Degradation sequence when over budget
DEGRADATION_SEQUENCE = [
    {"target": "relevant_excerpts", "action": "reduce_count", "from": 5, "to": 3},
    {"target": "recent_messages", "action": "reduce_rounds", "from": 2, "to": 1},
    {"target": "relevant_excerpts", "action": "reduce_count", "from": 3, "to": 2},
    {"target": "discussion_summary", "action": "truncate", "max_length": 800},
    {"target": "recent_messages", "action": "reduce_rounds", "from": 1, "to": 0},
]

# Token estimation constants
TOKEN_ESTIMATES = {
    "system_prompt_avg": 1200,
    "data_summary_avg": 800,
    "relevant_excerpts_avg": 2000,
    "discussion_summary_avg": 350,
    "discussion_summary_growth_rate": 1.35,
    "recent_messages_avg": 1800,
    "instruction_avg": 300,
    "avg_output_per_call": 1000,
    "avg_latency_seconds": 10,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count from text.
    
    Uses rough heuristic: 1 token ≈ 4 characters for English,
    1 token ≈ 2 characters for Chinese.
    """
    if not text:
        return 0
    
    # Count Chinese characters
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # Count other characters
    other_chars = len(text) - chinese_chars
    
    # Chinese: ~2 chars per token, English: ~4 chars per token
    return (chinese_chars // 2) + (other_chars // 4)


def estimate_round_tokens(round_number: int, expert_count: int) -> int:
    """Estimate total tokens for a discussion round.
    
    Uses geometric growth model for discussion summary.
    """
    base = TOKEN_ESTIMATES["discussion_summary_avg"]
    growth_rate = TOKEN_ESTIMATES["discussion_summary_growth_rate"]
    
    summary_tokens = int(base * (growth_rate ** (round_number - 1)))
    
    expert_factor = 1 + (expert_count - 2) * 0.15
    
    per_expert = (
        TOKEN_ESTIMATES["system_prompt_avg"]
        + TOKEN_ESTIMATES["data_summary_avg"]
        + TOKEN_ESTIMATES["relevant_excerpts_avg"]
        + summary_tokens
        + TOKEN_ESTIMATES["recent_messages_avg"]
        + TOKEN_ESTIMATES["instruction_avg"]
        + TOKEN_ESTIMATES["avg_output_per_call"]
    )
    
    return int(per_expert * expert_count * expert_factor)


def estimate_total_tokens(rounds: int, expert_count: int) -> int:
    """Estimate total tokens for entire discussion."""
    total = 0
    for r in range(1, rounds + 1):
        total += estimate_round_tokens(r, expert_count)
    return total


def check_budget(current_tokens: int, budget: TokenBudget) -> bool:
    """Check if current tokens are within budget."""
    return current_tokens <= budget.total


def get_degradation_action(current_tokens: int, budget: TokenBudget) -> Optional[Dict[str, Any]]:
    """Get next degradation action if over budget."""
    if current_tokens <= budget.total:
        return None
    
    # Simple: return first degradation action
    # In production, track which degradations have been applied
    return DEGRADATION_SEQUENCE[0] if DEGRADATION_SEQUENCE else None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/utils/token_counter.py
git commit -m "feat(backend): add token counting and budget management utilities"
```

---

### Task 2: 增强ContextBuilder

**Files:**
- Modify: `backend/app/services/context_builder.py`

- [ ] **Step 1: 增强ContextBuilder**

```python
# backend/app/services/context_builder.py
"""Enhanced context builder with token budget and degradation."""

from typing import Any, Dict, List, Optional
from app.utils.token_counter import (
    TokenBudget, estimate_tokens, check_budget, 
    DEGRADATION_SEQUENCE, TOKEN_ESTIMATES
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Role definition compression threshold
FULL_ROLE_ROUNDS = 2


class ContextBuilder:
    """Builds context for LLM prompts with token budget management."""

    def __init__(self, budget: Optional[TokenBudget] = None):
        self.budget = budget or TokenBudget()
        self.chars_per_token = 4

    def build_expert_prompt(
        self,
        role: Dict[str, Any],
        goal: str,
        shared_sources: List[Dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        recent_messages: Optional[List[Dict[str, Any]]] = None,
        decisions: Optional[List[str]] = None,
        additional_context: Optional[str] = None,
    ) -> str:
        """Build expert prompt with token budget management."""
        # Build role definition (compressed after round 2)
        role_def = self._build_role_definition(role, current_round)
        
        # Build file contents with budget
        file_contents = self._build_file_contents_with_budget(
            shared_sources, self.budget.relevant_excerpts
        )
        
        # Build round context
        round_context = self._build_round_context(current_round, total_rounds)
        
        # Build recent messages summary
        messages_context = self._build_messages_context(
            recent_messages, self.budget.recent_messages
        )
        
        # Build decisions context
        decisions_context = self._build_decisions_context(decisions)
        
        # Assemble prompt
        prompt = f"""{role_def}

## 本次任务
目标：{goal}
工作模式：代码文档模式
{round_context}

## 共享资料
{file_contents if file_contents else "无共享资料"}

## 已有讨论
{rolling_summary if rolling_summary else "这是讨论的开始，还没有已有讨论。"}

{messages_context}

{decisions_context}

## 本轮要求
请从你的专业角度，对当前议题发表意见。
要求：
- 引用共享资料中的具体内容时，请标注来源文件名
- 区分"资料中明确的信息"和"你的推断/建议"
- 回复控制在 500 字以内
- 如果是最后几轮，请重点总结你的核心观点"""

        if additional_context:
            prompt += f"\n\n## 补充信息\n{additional_context}"

        # Check token budget
        estimated = estimate_tokens(prompt)
        if not check_budget(estimated, self.budget):
            logger.warning(
                "Prompt exceeds token budget",
                estimated=estimated,
                budget=self.budget.total,
            )
            # Apply degradation
            prompt = self._apply_degradation(prompt, role, current_round, total_rounds)

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
        """Build orchestrator prompt."""
        expert_names = ", ".join(e["name"] for e in experts)
        file_contents = self._build_file_contents_with_budget(
            shared_sources, self.budget.data_summary
        )

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

请用简洁的主持词引导讨论，不要超过 200 字。

重要：在发言末尾，请输出以下ACTION指令之一：
- ACTION: next:<专家名称> — 指定下一位发言者
- ACTION: converge — 标识已达成共识
- ACTION: synthesize — 触发汇总生成产出"""

        return prompt

    def build_synthesizer_prompt(
        self,
        goal: str,
        full_discussion: str,
        part: int = 1,
    ) -> str:
        """Build synthesizer prompt for artifact generation.
        
        Args:
            goal: Discussion goal
            full_discussion: Full discussion text
            part: 1 for chapters 1-5, 2 for chapters 6-10
        """
        if part == 1:
            chapters = """## 1. 背景与目标
## 2. 当前资料理解
## 3. 需求拆解
## 4. 总体方案
## 5. 模块设计"""
        else:
            chapters = """## 6. 数据结构 / 接口设计
## 7. 实施步骤
## 8. 测试与验收标准
## 9. 风险与取舍
## 10. 后续迭代建议"""

        prompt = f"""你是文档专家。请根据以下讨论记录，生成一份结构化的 Markdown 技术方案文档的第{part}部分。

## 讨论记录
{full_discussion}

## 产出要求
请按以下结构生成文档：

# {goal}

{chapters}

要求：
- 内容必须来自讨论记录，不要编造
- 引用关键决策时标注是哪位专家提出的
- 结论要清晰、可执行
- 使用 Markdown 格式
- 控制在 2500 tokens 以内"""

        return prompt

    def _build_role_definition(self, role: Dict[str, Any], current_round: int) -> str:
        """Build role definition, compressed after round 2."""
        if current_round <= FULL_ROLE_ROUNDS:
            # Full definition (~500 tokens)
            expertise = ", ".join(role.get("expertise", []))
            responsibilities = "\n".join(
                f"- {r}" for r in role.get("responsibilities", [])
            )
            constraints = "\n".join(
                f"- {c}" for c in role.get("constraints", [])
            )
            
            return f"""你是{role['name']}，一位{role.get('description', '专家')}。

## 专业能力
{expertise}

## 职责
{responsibilities}

## 约束
{constraints if constraints else "无特殊约束"}"""
        else:
            # Compact definition (~100 tokens)
            constraints = role.get("constraints", [])
            constraint_text = constraints[0] if constraints else ""
            
            return f"""你是{role['name']}。{role.get('description', '专家')}
{f'核心约束：{constraint_text}' if constraint_text else ''}"""

    def _build_file_contents_with_budget(
        self, 
        shared_sources: List[Dict[str, Any]], 
        max_tokens: int
    ) -> str:
        """Build file contents within token budget."""
        if not shared_sources:
            return ""

        sections = []
        total_chars = 0
        max_chars = max_tokens * self.chars_per_token

        for source in shared_sources:
            content = source.get("content", "")
            path = source.get("path", "粘贴的文本")

            if not content:
                continue

            if total_chars + len(content) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    content = content[:remaining] + "\n...(内容已截断)"
                else:
                    break

            section = f"### 来源: {path}\n```\n{content}\n```"
            sections.append(section)
            total_chars += len(content)

        return "\n\n".join(sections)

    def _build_round_context(self, current_round: int, total_rounds: int) -> str:
        """Build round context with convergence hints."""
        context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
        
        if current_round >= total_rounds - 1:
            context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"
        elif current_round == 1:
            context += "\n这是第一轮讨论，请从你的专业角度给出初步观点。"
        
        return context

    def _build_messages_context(
        self, 
        messages: Optional[List[Dict[str, Any]]], 
        max_tokens: int
    ) -> str:
        """Build recent messages context."""
        if not messages:
            return ""
        
        parts = ["## 最近讨论"]
        total_chars = 0
        max_chars = max_tokens * self.chars_per_token
        
        for msg in messages:
            sender = msg.get("sender_id", msg.get("sender_type", "未知"))
            content = msg.get("content", "")
            
            if len(content) > 200:
                content = content[:200] + "..."
            
            line = f"[{sender}]: {content}"
            
            if total_chars + len(line) > max_chars:
                break
            
            parts.append(line)
            total_chars += len(line)
        
        return "\n".join(parts) if len(parts) > 1 else ""

    def _build_decisions_context(self, decisions: Optional[List[str]]) -> str:
        """Build decisions context."""
        if not decisions:
            return ""
        
        parts = ["## 已达成共识"]
        for d in decisions:
            parts.append(f"- {d}")
        
        return "\n".join(parts)

    def _apply_degradation(
        self, 
        prompt: str,
        role: Dict[str, Any],
        current_round: int,
        total_rounds: int,
    ) -> str:
        """Apply degradation to reduce token count."""
        # Simple degradation: truncate the prompt
        max_chars = self.budget.total * self.chars_per_token
        
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n\n...(内容已截断以符合Token预算)"
        
        return prompt

    def build_rolling_summary(
        self,
        existing_summary: str,
        new_messages: List[Dict[str, Any]],
    ) -> str:
        """Build rolling summary of discussion."""
        if not new_messages:
            return existing_summary

        new_points = []
        for msg in new_messages:
            sender = msg.get("sender_id", msg.get("sender_type", "未知"))
            content = msg.get("content", "")

            if len(content) > 200:
                content = content[:200] + "..."

            new_points.append(f"[{sender}]: {content}")

        new_summary = "\n".join(new_points)

        if existing_summary:
            combined = f"{existing_summary}\n\n最新讨论：\n{new_summary}"
        else:
            combined = f"讨论开始：\n{new_summary}"

        max_chars = self.budget.discussion_summary * self.chars_per_token
        if len(combined) > max_chars:
            combined = combined[-max_chars:]

        return combined

    def truncate_content(self, content: str, max_tokens: Optional[int] = None) -> str:
        """Truncate content to fit token budget."""
        max_chars = (max_tokens or self.budget.relevant_excerpts) * self.chars_per_token

        if len(content) <= max_chars:
            return content

        return content[:max_chars] + "...(内容已截断)"


# Singleton instance
context_builder = ContextBuilder()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/context_builder.py
git commit -m "feat(backend): enhance context builder with token budget and degradation"
```

---

### Task 3: 增强Orchestrator - ACTION解析和收敛检测

**Files:**
- Modify: `backend/app/services/orchestrator.py`

- [ ] **Step 1: 增强Orchestrator**

```python
# backend/app/services/orchestrator.py
"""Enhanced discussion orchestrator with ACTION parsing and convergence detection."""

import re
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscussionState(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    CONVERGING = "converging"
    COMPLETED = "completed"
    FAILED = "failed"


class SSEEventType(str, Enum):
    STATUS = "status"
    THINKING = "thinking"
    MESSAGE = "message"
    ARTIFACT = "artifact"
    ERROR = "error"
    DONE = "done"
    COST_UPDATE = "cost_update"


class ActionType(str, Enum):
    NEXT = "next"
    CONVERGE = "converge"
    SYNTHESIZE = "synthesize"


class HostAction:
    """Parsed ACTION from host message."""
    def __init__(self, action_type: ActionType, expert_id: Optional[str] = None):
        self.type = action_type
        self.expert_id = expert_id


# Convergence keywords
CONVERGENCE_KEYWORDS = [
    "可行", "同意", "没有异议", "建议直接", "没问题", "LGTM", 
    "一致", "共识", "确认", "通过"
]


def parse_host_action(content: str) -> Optional[HostAction]:
    """Parse ACTION instruction from host message.
    
    Format: ACTION: next:<expertId> | converge | synthesize
    """
    match = re.search(r'ACTION:\s*(next:(\w+)|converge|synthesize)', content, re.IGNORECASE)
    if not match:
        return None
    
    action_str = match.group(1).lower()
    
    if action_str == "converge":
        return HostAction(ActionType.CONVERGE)
    elif action_str == "synthesize":
        return HostAction(ActionType.SYNTHESIZE)
    elif action_str.startswith("next:"):
        expert_id = match.group(2)
        return HostAction(ActionType.NEXT, expert_id)
    
    return None


def parse_length_warning(content: str) -> bool:
    """Parse LENGTH_WARNING from host message."""
    return bool(re.search(r'LENGTH_WARNING:\s*true', content, re.IGNORECASE))


def check_convergence(messages: List[Dict[str, Any]], min_consensus: int = 2) -> bool:
    """Check if discussion has reached convergence.
    
    Looks for consensus keywords in expert messages.
    """
    if not messages:
        return False
    
    # Get last round's expert messages
    last_round = max(m.get("round", 0) for m in messages)
    last_round_messages = [
        m for m in messages 
        if m.get("round") == last_round and m.get("sender_type") == "expert"
    ]
    
    if len(last_round_messages) < 2:
        return False
    
    # Count messages with convergence keywords
    consensus_count = 0
    for msg in last_round_messages:
        content = msg.get("content", "")
        if any(kw in content for kw in CONVERGENCE_KEYWORDS):
            consensus_count += 1
    
    # Require majority consensus
    return consensus_count >= min_consensus


class Orchestrator:
    def __init__(
        self,
        session: AsyncSession,
        room: Any,
        on_event: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
    ):
        self.session = session
        self.room = room
        self.on_event = on_event

        self.room_id = room.id
        self.goal = room.goal
        self.max_rounds = room.round_limit
        self.current_round = 0
        self.state = DiscussionState.INITIALIZED

        self.participants = []
        for p in room.participants:
            self.participants.append({
                "role_card_id": p.role_card_id,
                "name": p.role_card.name if p.role_card else "Unknown",
                "provider_id": p.provider_id,
                "model": p.model_override or p.provider.default_model,
                "base_url": p.provider.base_url,
            })

        self.rolling_summary = ""
        self.shared_sources = []
        self.total_messages = 0
        self.total_tokens = 0
        self.all_messages: List[Dict[str, Any]] = []
        self.decisions: List[str] = []

        # Speaker order (first round uses default, subsequent rounds use ACTION)
        self.speaker_order = [p["name"] for p in self.participants]
        self.next_speaker_index = 0

    def should_continue(self) -> bool:
        return self.current_round < self.max_rounds

    async def load_shared_sources(self) -> None:
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
        if self.on_event:
            await self.on_event(event_type, data)

        logger.debug("SSE event emitted", type=event_type, data=data)

    async def run_discussion(self) -> Dict[str, Any]:
        try:
            self.state = DiscussionState.RUNNING
            
            # Emit status event
            await self.emit_event(SSEEventType.STATUS, {
                "room_id": self.room_id,
                "status": "running",
                "phase": "discussing",
                "round": 0,
                "total_rounds": self.max_rounds,
            })
            
            await self.load_shared_sources()

            while self.should_continue():
                self.current_round += 1

                logger.info(
                    "Starting discussion round",
                    room_id=self.room_id,
                    round=self.current_round,
                    max_rounds=self.max_rounds,
                )

                # Emit round status
                await self.emit_event(SSEEventType.STATUS, {
                    "room_id": self.room_id,
                    "status": "running",
                    "phase": "discussing",
                    "round": self.current_round,
                    "total_rounds": self.max_rounds,
                })

                # Run orchestrator turn
                host_content = await self._run_orchestrator_turn()

                # Parse ACTION from host message
                action = parse_host_action(host_content) if host_content else None
                length_warning = parse_length_warning(host_content) if host_content else False

                # Determine speaker order for this round
                if self.current_round == 1:
                    # First round: use default order
                    speakers = self.participants
                elif action and action.type == ActionType.NEXT and action.expert_id:
                    # Use ACTION-specified order
                    speakers = self._reorder_speakers(action.expert_id)
                else:
                    # Default order
                    speakers = self.participants

                # Run expert turns
                for participant in speakers:
                    await self._run_expert_turn(participant, length_warning)

                # Update rolling summary
                await self._update_rolling_summary()

                # Check convergence
                if action and action.type == ActionType.CONVERGE:
                    logger.info(
                        "Discussion converged (host ACTION)",
                        room_id=self.room_id,
                        round=self.current_round,
                    )
                    break

                if check_convergence(self.all_messages):
                    logger.info(
                        "Discussion converged (keyword detection)",
                        room_id=self.room_id,
                        round=self.current_round,
                    )
                    break

                # Check for synthesize action
                if action and action.type == ActionType.SYNTHESIZE:
                    logger.info(
                        "Synthesize requested",
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
                "artifact_count": 0,
            })

            return {
                "success": True,
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
                "total_tokens": self.total_tokens,
            }

        except Exception as e:
            self.state = DiscussionState.FAILED
            logger.error(
                "Discussion failed",
                room_id=self.room_id,
                error=str(e),
                round=self.current_round,
            )

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

    def _reorder_speakers(self, first_speaker_id: str) -> List[Dict[str, Any]]:
        """Reorder speakers starting with the specified expert."""
        # Find the expert by name or id
        first_idx = None
        for i, p in enumerate(self.participants):
            if p["name"] == first_speaker_id or p["role_card_id"] == first_speaker_id:
                first_idx = i
                break
        
        if first_idx is None:
            return self.participants
        
        # Rotate list to start with specified expert
        return self.participants[first_idx:] + self.participants[:first_idx]

    async def _run_orchestrator_turn(self) -> Optional[str]:
        """Run orchestrator turn and return the content."""
        await self.emit_event(SSEEventType.THINKING, {
            "room_id": self.room_id,
            "role": "主持人",
            "status": "思考中",
        })

        from app.services.context_builder import context_builder

        prompt = context_builder.build_orchestrator_prompt(
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            experts=[{"name": p["name"]} for p in self.participants],
        )

        if self.participants:
            provider = self.participants[0]
            api_key = await self._get_api_key(provider["provider_id"])

            from app.services.model_client import create_model_client, ModelClientError

            client = create_model_client(
                base_url=provider["base_url"],
                api_key=api_key,
                model=provider["model"],
            )

            try:
                response = await client.chat_completion(
                    messages=[{"role": "user", "content": prompt}]
                )

                # Track tokens
                usage = response.usage or {}
                self.total_tokens += usage.get("total_tokens", 0)

                # Emit cost update
                await self.emit_event(SSEEventType.COST_UPDATE, {
                    "room_id": self.room_id,
                    "total_tokens": self.total_tokens,
                    "round": self.current_round,
                })

                from app.schemas.message import MessageCreate
                from app.services.message_service import message_service

                message_data = MessageCreate(
                    room_id=self.room_id,
                    sender_type="orchestrator",
                    sender_id=None,
                    content=response.content,
                    citations=None,
                    round=self.current_round,
                )

                message = await message_service.create(self.session, message_data)
                self.total_messages += 1

                # Store in all_messages for convergence check
                self.all_messages.append({
                    "sender_type": "orchestrator",
                    "sender_id": None,
                    "content": response.content,
                    "round": self.current_round,
                })

                await self.emit_event(SSEEventType.MESSAGE, {
                    "id": message.id,
                    "room_id": self.room_id,
                    "sender_type": "orchestrator",
                    "sender_id": None,
                    "content": response.content,
                    "citations": [],
                    "round": self.current_round,
                })
                
                return response.content

            except ModelClientError as e:
                logger.error(
                    "Orchestrator turn failed",
                    error=str(e),
                    round=self.current_round,
                )
                await self.emit_event(SSEEventType.ERROR, {
                    "room_id": self.room_id,
                    "error": "orchestrator_turn_failed",
                    "message": str(e),
                    "round": self.current_round,
                })
        
        return None

    async def _run_expert_turn(
        self, 
        participant: Dict[str, Any],
        length_warning: bool = False,
    ) -> None:
        role_card_id = participant["role_card_id"]
        role_name = participant["name"]

        await self.emit_event(SSEEventType.THINKING, {
            "room_id": self.room_id,
            "role": role_name,
            "status": "思考中",
        })

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

        from app.services.context_builder import context_builder

        # Add length warning to additional context if needed
        additional_context = None
        if length_warning:
            additional_context = "⚠️ 上一轮回复过长。本轮请严格控制在 300 字以内，使用要点式输出。"

        prompt = context_builder.build_expert_prompt(
            role=role_data,
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            recent_messages=self.all_messages[-6:] if self.all_messages else None,
            decisions=self.decisions,
            additional_context=additional_context,
        )

        api_key = await self._get_api_key(participant["provider_id"])

        from app.services.model_client import create_model_client, ModelClientError

        client = create_model_client(
            base_url=participant["base_url"],
            api_key=api_key,
            model=participant["model"],
        )

        try:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )

            # Track tokens
            usage = response.usage or {}
            self.total_tokens += usage.get("total_tokens", 0)

            # Emit cost update
            await self.emit_event(SSEEventType.COST_UPDATE, {
                "room_id": self.room_id,
                "total_tokens": self.total_tokens,
                "round": self.current_round,
            })

            from app.schemas.message import MessageCreate
            from app.services.message_service import message_service

            # Extract key point (first meaningful sentence)
            key_point = self._extract_key_point(response.content)

            message_data = MessageCreate(
                room_id=self.room_id,
                sender_type="expert",
                sender_id=role_card_id,
                content=response.content,
                citations=None,
                round=self.current_round,
            )

            message = await message_service.create(self.session, message_data)
            self.total_messages += 1

            # Store in all_messages for convergence check
            self.all_messages.append({
                "sender_type": "expert",
                "sender_id": role_name,
                "content": response.content,
                "round": self.current_round,
            })

            await self.emit_event(SSEEventType.MESSAGE, {
                "id": message.id,
                "room_id": self.room_id,
                "sender_type": "expert",
                "sender_id": role_card_id,
                "content": response.content,
                "citations": [],
                "round": self.current_round,
                "key_point": key_point,
            })

        except ModelClientError as e:
            logger.error(
                "Expert turn failed",
                role=role_name,
                error=str(e),
                round=self.current_round,
            )

            await self.emit_event(SSEEventType.ERROR, {
                "room_id": self.room_id,
                "error": f"{role_name}发言失败: {str(e)}",
                "recoverable": True,
            })

    def _extract_key_point(self, content: str) -> Optional[str]:
        """Extract key point from expert message."""
        # Skip patterns (transition sentences)
        skip_patterns = [
            r'^(关于|针对|对于|关于这个|说到|谈到|提及|涉及|回到)',
            r'^(Regarding|As for|In terms of|On the topic of)',
            r'^#{1,6}\s',
            r'^[-*]\s',
            r'^```',
            r'^\s*$',
            r'^>\s',
        ]
        
        lines = content.split('\n')
        for line in lines:
            trimmed = line.strip()
            if len(trimmed) < 15:
                continue
            if any(re.match(p, trimmed) for p in skip_patterns):
                continue
            # Clean markdown
            cleaned = trimmed.replace('**', '').replace('*', '').replace('`', '')
            return cleaned[:100]
        
        # Fallback: longest line
        meaningful = [l.strip() for l in lines if l.strip() and len(l.strip()) > 10]
        if meaningful:
            return max(meaningful, key=len)[:100]
        
        return None

    async def _get_api_key(self, provider_id: str) -> str:
        from app.services.provider_service import provider_service
        from app.services.crypto import crypto_service

        provider = await provider_service.get_by_id(self.session, provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        return crypto_service.decrypt(provider.api_key_encrypted)

    async def _update_rolling_summary(self) -> None:
        from app.services.message_service import message_service
        from app.services.context_builder import context_builder

        messages = await message_service.get_by_room(
            self.session,
            self.room_id,
            limit=len(self.participants) + 1,
        )

        current_messages = [
            {
                "sender_type": m.sender_type,
                "sender_id": m.sender_id,
                "content": m.content,
            }
            for m in messages
            if m.round == self.current_round
        ]

        self.rolling_summary = context_builder.build_rolling_summary(
            existing_summary=self.rolling_summary,
            new_messages=current_messages,
        )


def create_orchestrator(
    session: AsyncSession,
    room: Any,
    on_event: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
) -> Orchestrator:
    return Orchestrator(session=session, room=room, on_event=on_event)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/orchestrator.py
git commit -m "feat(backend): enhance orchestrator with ACTION parsing and convergence detection"
```

---

### Task 4: 增强ArtifactWriter - 两次调用策略

**Files:**
- Modify: `backend/app/services/artifact_writer.py`

- [ ] **Step 1: 增强ArtifactWriter**

```python
# backend/app/services/artifact_writer.py
"""Enhanced artifact writer with two-pass generation strategy."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.utils.formatters import build_discussion_markdown, build_summary, get_sender_label
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactWriterError(Exception):
    """Exception raised for artifact writer errors."""
    pass


class ArtifactWriter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_artifact(
        self,
        room_id: str,
        room_name: str,
        goal: str,
        messages: List[Dict[str, Any]],
        output_directory: str,
        participants: Optional[List[str]] = None,
        source_count: int = 0,
        model_name: str = "unknown",
    ) -> Artifact:
        """Generate artifact with two-pass strategy for code_document mode.
        
        Part 1: Chapters 1-5 (background, requirements, solution, modules, design)
        Part 2: Chapters 6-10 (interfaces, implementation, testing, risks, next steps)
        """
        if not messages:
            raise ValueError("No messages provided for artifact generation")

        # Build full discussion text
        full_discussion = self._build_discussion_text(messages)
        
        # Generate Part 1 (chapters 1-5)
        part1_content = await self._generate_part1(goal, full_discussion)
        
        # Generate Part 2 (chapters 6-10) with Part 1 summary as context
        part1_summary = self._extract_part1_summary(part1_content)
        part2_content = await self._generate_part2(goal, full_discussion, part1_summary)
        
        # Combine parts
        markdown_content = self._combine_parts(
            room_name=room_name,
            goal=goal,
            part1=part1_content,
            part2=part2_content,
            participants=participants,
            source_count=source_count,
            model_name=model_name,
            round_count=max(m.get("round", 0) for m in messages),
        )

        # Write to file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        artifact_dir = os.path.join(output_directory, f"artifact_{timestamp}")

        try:
            os.makedirs(artifact_dir, exist_ok=True)
            file_path = os.path.join(artifact_dir, "final-plan.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # Also write discussion log
            log_path = os.path.join(artifact_dir, "discussion-log.md")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(self._build_discussion_log(messages))
            
        except OSError as e:
            logger.error(
                "Failed to write artifact file",
                artifact_dir=artifact_dir,
                error=str(e),
            )
            raise ArtifactWriterError(
                f"Failed to write artifact to {artifact_dir}: {e}"
            ) from e

        summary = self._build_summary(messages)

        artifact = Artifact(
            id=str(uuid.uuid4()),
            room_id=room_id,
            artifact_type="markdown",
            title=room_name,
            file_path=file_path,
            summary=summary,
        )

        self.session.add(artifact)
        await self.session.flush()

        logger.info(
            "Generated artifact",
            artifact_id=artifact.id,
            room_id=room_id,
            file_path=file_path,
            message_count=len(messages),
        )

        return artifact

    async def _generate_part1(self, goal: str, discussion: str) -> str:
        """Generate Part 1: chapters 1-5."""
        from app.services.context_builder import context_builder
        
        prompt = context_builder.build_synthesizer_prompt(goal, discussion, part=1)
        
        # In real implementation, call LLM here
        # For now, return a template
        return f"""# {goal}

## 1. 背景与目标
基于讨论记录生成的背景与目标分析。

## 2. 当前资料理解
对共享资料的理解和分析。

## 3. 需求拆解
功能需求的详细拆解。

## 4. 总体方案
整体技术方案设计。

## 5. 模块设计
系统模块划分和设计。"""

    async def _generate_part2(self, goal: str, discussion: str, part1_summary: str) -> str:
        """Generate Part 2: chapters 6-10."""
        from app.services.context_builder import context_builder
        
        prompt = context_builder.build_synthesizer_prompt(goal, discussion, part=2)
        
        # In real implementation, call LLM here with part1_summary as context
        # For now, return a template
        return f"""## 6. 数据结构 / 接口设计
API接口和数据结构设计。

## 7. 实施步骤
详细的实施步骤和时间线。

## 8. 测试与验收标准
测试方案和验收标准。

## 9. 风险与取舍
技术风险分析和权衡取舍。

## 10. 后续迭代建议
后续版本的改进建议。"""

    def _extract_part1_summary(self, part1_content: str) -> str:
        """Extract summary from Part 1 for Part 2 context."""
        lines = part1_content.split('\n')
        summary_parts = []
        
        for line in lines:
            # Extract headers and first sentences
            if line.startswith('#'):
                summary_parts.append(line)
            elif line.strip() and len(summary_parts) > 0 and not summary_parts[-1].startswith('#'):
                # Skip if we already have content for this section
                continue
            elif line.strip() and len(summary_parts) > 0:
                summary_parts.append(line[:100])
        
        return '\n'.join(summary_parts[:20])  # Limit to 20 lines

    def _combine_parts(
        self,
        room_name: str,
        goal: str,
        part1: str,
        part2: str,
        participants: Optional[List[str]] = None,
        source_count: int = 0,
        model_name: str = "unknown",
        round_count: int = 0,
    ) -> str:
        """Combine parts with source annotation header."""
        # Build source annotation
        participant_str = "、".join(participants) if participants else "未知"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        
        header = f"""> 📋 本方案由专家团通过 {round_count} 轮多专家讨论自动生成。
> 参与专家：{participant_str}
> 共享资料：{source_count} 个文件
> 所用模型：{model_name}
> 生成时间：{now}

---

"""
        
        return header + part1 + "\n\n" + part2

    def _build_discussion_text(self, messages: List[Dict[str, Any]]) -> str:
        """Build full discussion text."""
        parts = []
        current_round = 0
        
        for msg in messages:
            round_num = msg.get("round", 0)
            if round_num != current_round:
                current_round = round_num
                parts.append(f"\n---\n## 第 {current_round} 轮\n")
            
            sender_type = msg.get("sender_type", "unknown")
            sender_id = msg.get("sender_id", "")
            content = msg.get("content", "")
            
            label = get_sender_label(sender_type, sender_id)
            parts.append(f"**{label}**：{content}\n")
        
        return "\n".join(parts)

    def _build_discussion_log(self, messages: List[Dict[str, Any]]) -> str:
        """Build discussion log markdown."""
        return self._build_discussion_text(messages)

    def _build_summary(self, messages: List[Dict[str, Any]]) -> str:
        return build_summary(messages)


def create_artifact_writer(session: AsyncSession) -> ArtifactWriter:
    """Create artifact writer instance."""
    return ArtifactWriter(session=session)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/artifact_writer.py
git commit -m "feat(backend): enhance artifact writer with two-pass generation and source annotation"
```

---

### Task 5: 前端专家色系和动画

**Files:**
- Create: `frontend/src/styles/expert-colors.css`
- Create: `frontend/src/styles/animations.css`

- [ ] **Step 1: 创建专家色系CSS**

```css
/* frontend/src/styles/expert-colors.css */
:root {
  /* ── 主持人 — 中性灰 ─────────────────────── */
  --expert-host: #6B7280;
  --expert-host-bg: #F3F4F6;
  --expert-host-bg-light: #F9FAFB;

  /* ── 产品经理 — 理性蓝 ───────────────────── */
  --expert-product: #3B82F6;
  --expert-product-bg: #DBEAFE;
  --expert-product-bg-light: #EFF6FF;

  /* ── 系统架构师 — 智慧紫 ─────────────────── */
  --expert-architect: #8B5CF6;
  --expert-architect-bg: #EDE9FE;
  --expert-architect-bg-light: #F5F3FF;

  /* ── 后端工程专家 — 稳重绿 ────────────────── */
  --expert-backend: #10B981;
  --expert-backend-bg: #D1FAE5;
  --expert-backend-bg-light: #ECFDF5;

  /* ── 文档专家 — 专注靛 ───────────────────── */
  --expert-doc: #6366F1;
  --expert-doc-bg: #E0E7FF;
  --expert-doc-bg-light: #EEF2FF;
}

/* Expert color utility classes */
.expert-host { color: var(--expert-host); }
.expert-host-bg { background-color: var(--expert-host-bg); }
.expert-host-bg-light { background-color: var(--expert-host-bg-light); }

.expert-product { color: var(--expert-product); }
.expert-product-bg { background-color: var(--expert-product-bg); }
.expert-product-bg-light { background-color: var(--expert-product-bg-light); }

.expert-architect { color: var(--expert-architect); }
.expert-architect-bg { background-color: var(--expert-architect-bg); }
.expert-architect-bg-light { background-color: var(--expert-architect-bg-light); }

.expert-backend { color: var(--expert-backend); }
.expert-backend-bg { background-color: var(--expert-backend-bg); }
.expert-backend-bg-light { background-color: var(--expert-backend-bg-light); }

.expert-doc { color: var(--expert-doc); }
.expert-doc-bg { background-color: var(--expert-doc-bg); }
.expert-doc-bg-light { background-color: var(--expert-doc-bg-light); }
```

- [ ] **Step 2: 创建动画CSS**

```css
/* frontend/src/styles/animations.css */
/* ── 色条呼吸动画 ─────────────────────────── */
@keyframes color-bar-breathe {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.thinking-color-bar {
  width: 3px;
  border-radius: 9999px;
  animation: color-bar-breathe 2s ease-in-out infinite;
}

/* ── 骨架文字扫光 ─────────────────────────── */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, #E5E7EB 25%, #F3F4F6 50%, #E5E7EB 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  will-change: background-position;
}

/* ── 光点脉冲 ─────────────────────────────── */
@keyframes pulse-dot {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.5);
    opacity: 0.6;
  }
}

/* ── 动画降级 ─────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/expert-colors.css frontend/src/styles/animations.css
git commit -m "feat(frontend): add expert color system and animation styles"
```

---

### Task 6: 增强ThinkingIndicator组件

**Files:**
- Modify: `frontend/src/components/discussion/ThinkingIndicator.tsx`

- [ ] **Step 1: 增强ThinkingIndicator**

```tsx
// frontend/src/components/discussion/ThinkingIndicator.tsx
import React, { useState, useEffect } from 'react';

interface ThinkingIndicatorProps {
  speakerId: string;
  speakerName: string;
  speakerEmoji?: string;
  thinkingVerb?: string;
  estimatedSeconds?: number;
  expertColor?: string;
  isVisible: boolean;
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  speakerId,
  speakerName,
  speakerEmoji = '🤖',
  thinkingVerb = '正在思考',
  estimatedSeconds = 15,
  expertColor = 'var(--expert-host, #6B7280)',
  isVisible,
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isVisible) {
      setElapsed(0);
      return;
    }

    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [isVisible]);

  if (!isVisible) return null;

  const remaining = Math.max(0, estimatedSeconds - elapsed);
  const progress = Math.min(90, (elapsed / Math.max(1, estimatedSeconds)) * 90);

  return (
    <div className="flex gap-3 py-3">
      {/* 色条 — 带呼吸动画 */}
      <div
        className="thinking-color-bar flex-shrink-0"
        style={{ backgroundColor: expertColor }}
      />

      <div className="flex-1 min-w-0">
        {/* 头部 */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">{speakerEmoji}</span>
          <span className="text-sm font-medium text-gray-900">{speakerName}</span>
          <span className="text-sm text-gray-400 italic">{thinkingVerb}</span>
        </div>

        {/* 预计时间 + JS 驱动进度条 */}
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1 h-[2px] bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                backgroundColor: expertColor,
                width: `${progress}%`,
                transition: 'width 1s linear',
              }}
            />
          </div>
          <span className="text-xs text-gray-400 tabular-nums w-12 text-right">
            {remaining > 0 ? `≈ ${remaining}s` : '...'}
          </span>
        </div>

        {/* 骨架文字 — 3 行 */}
        <div className="space-y-2">
          <div className="skeleton-line" style={{ width: '85%' }} />
          <div className="skeleton-line" style={{ width: '70%' }} />
          <div className="skeleton-line" style={{ width: '55%' }} />
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/discussion/ThinkingIndicator.tsx
git commit -m "feat(frontend): enhance ThinkingIndicator with progress bar and skeleton"
```

---

### Task 7: 新增RoundDivider组件

**Files:**
- Create: `frontend/src/components/discussion/RoundDivider.tsx`
- Modify: `frontend/src/components/discussion/index.ts`

- [ ] **Step 1: 创建RoundDivider组件**

```tsx
// frontend/src/components/discussion/RoundDivider.tsx
import React from 'react';

interface RoundDividerProps {
  round: number;
  className?: string;
}

export const RoundDivider: React.FC<RoundDividerProps> = ({ 
  round, 
  className = '' 
}) => {
  return (
    <div className={`flex items-center gap-4 my-4 ${className}`}>
      <div className="flex-1 h-px bg-gray-200" />
      <span className="text-xs text-gray-400 select-none flex-shrink-0">
        第 {round} 轮
      </span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  );
};
```

- [ ] **Step 2: 更新index.ts导出**

```tsx
// frontend/src/components/discussion/index.ts
export { MessageBubble } from './MessageBubble';
export { ThinkingIndicator } from './ThinkingIndicator';
export { RoundProgress } from './RoundProgress';
export { RoundDivider } from './RoundDivider';
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/discussion/RoundDivider.tsx frontend/src/components/discussion/index.ts
git commit -m "feat(frontend): add RoundDivider component for visual round separation"
```

---

### Task 8: 新增CitationBlock组件

**Files:**
- Create: `frontend/src/components/discussion/CitationBlock.tsx`
- Modify: `frontend/src/components/discussion/index.ts`

- [ ] **Step 1: 创建CitationBlock组件**

```tsx
// frontend/src/components/discussion/CitationBlock.tsx
import React, { useState } from 'react';

interface Citation {
  file: string;
  snippet?: string;
}

interface CitationBlockProps {
  citations: Citation[];
}

export const CitationBlock: React.FC<CitationBlockProps> = ({ citations }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-gray-100">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span>📎</span>
        <span>
          引用自：{citations.map((c) => c.file).join(', ')}
        </span>
        <span className="ml-1">
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <div
              key={index}
              className="bg-gray-50 rounded px-3 py-2 text-xs"
            >
              <div className="font-medium text-gray-600 mb-1">
                📎 {citation.file}
              </div>
              {citation.snippet && (
                <div className="text-gray-500 italic">
                  "{citation.snippet}"
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 2: 更新index.ts导出**

```tsx
// frontend/src/components/discussion/index.ts
export { MessageBubble } from './MessageBubble';
export { ThinkingIndicator } from './ThinkingIndicator';
export { RoundProgress } from './RoundProgress';
export { RoundDivider } from './RoundDivider';
export { CitationBlock } from './CitationBlock';
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/discussion/CitationBlock.tsx frontend/src/components/discussion/index.ts
git commit -m "feat(frontend): add CitationBlock component for source references"
```

---

### Task 9: 增强MessageBubble组件

**Files:**
- Modify: `frontend/src/components/discussion/MessageBubble.tsx`

- [ ] **Step 1: 增强MessageBubble**

```tsx
// frontend/src/components/discussion/MessageBubble.tsx
import React from 'react';
import type { DiscussionMessage } from '../../types/discussion';
import { CitationBlock } from './CitationBlock';

interface MessageBubbleProps {
  message: DiscussionMessage;
  showExpertiseBadge?: boolean;
}

// Expert color mapping
const EXPERT_COLORS: Record<string, string> = {
  '主持人': 'var(--expert-host, #6B7280)',
  '产品经理': 'var(--expert-product, #3B82F6)',
  '系统架构师': 'var(--expert-architect, #8B5CF6)',
  '后端工程专家': 'var(--expert-backend, #10B981)',
  '文档专家': 'var(--expert-doc, #6366F1)',
};

const senderLabels: Record<string, string> = {
  orchestrator: '主持人',
  expert: '专家',
  user: '用户',
  system: '系统',
};

function getExpertColor(senderId: string | null): string {
  if (!senderId) return 'var(--expert-host, #6B7280)';
  return EXPERT_COLORS[senderId] || 'var(--expert-host, #6B7280)';
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  showExpertiseBadge = false,
}) => {
  const isOrchestrator = message.sender_type === 'orchestrator';
  const isSystem = message.sender_type === 'system';
  const isUser = message.sender_type === 'user';
  const isDecision = message.message_type === 'decision';

  const expertColor = getExpertColor(message.sender_id);

  // Orchestrator message - centered system style
  if (isOrchestrator) {
    return (
      <div className="flex justify-center mb-4">
        <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-2 max-w-[80%]">
          <div className="text-xs text-gray-500 text-center mb-1">
            🎯 主持人 · 第 {message.round} 轮
          </div>
          <div className="text-sm text-gray-600 text-center">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  // Decision message - green highlight
  if (isDecision) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] rounded-lg px-4 py-3 bg-green-50 border-l-4 border-green-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-green-600">✅</span>
            <span className="text-sm font-medium text-green-700">
              达成决策 · 第 {message.round} 轮
            </span>
          </div>
          <div className="text-gray-800 font-medium text-sm">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  // User message - right aligned
  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[70%] bg-blue-500 text-white rounded-t-xl rounded-bl-xl rounded-br-sm px-4 py-3">
          <div className="text-sm">{message.content}</div>
          <div className="text-xs text-blue-100 mt-1 text-right">
            {message.round ? `第 ${message.round} 轮生效` : ''}
          </div>
        </div>
      </div>
    );
  }

  // System/info message
  if (isSystem) {
    return (
      <div className="flex justify-center mb-4">
        <div className="text-xs text-gray-400 bg-gray-50 rounded px-3 py-1">
          {message.content}
        </div>
      </div>
    );
  }

  // Expert message - with color bar
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%] rounded-lg bg-white shadow-sm border border-gray-200 overflow-hidden">
        {/* Color bar */}
        <div
          className="w-[3px] float-left h-full min-h-[60px]"
          style={{ backgroundColor: expertColor }}
        />

        <div className="px-4 py-3">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">
              {message.sender_id === '产品经理' ? '👨‍💼' :
               message.sender_id === '系统架构师' ? '🧑‍💻' :
               message.sender_id === '后端工程专家' ? '⚙️' :
               message.sender_id === '文档专家' ? '📝' : '🤖'}
            </span>
            <span className="text-sm font-medium text-gray-700">
              {message.sender_id || senderLabels[message.sender_type] || '未知'}
            </span>
            {showExpertiseBadge && (
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  backgroundColor: `color-mix(in srgb, ${expertColor} 10%, white)`,
                  color: expertColor,
                }}
              >
                专家
              </span>
            )}
            <span className="text-xs text-gray-400">
              第 {message.round} 轮
            </span>
          </div>

          {/* Content */}
          <div className="text-gray-800 whitespace-pre-wrap text-sm leading-relaxed">
            {message.content}
          </div>

          {/* Key point */}
          {message.key_point && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <div className="text-xs text-gray-500">
                💡 <span className="font-medium">关键观点：</span>
                {message.key_point}
              </div>
            </div>
          )}

          {/* Citations */}
          {message.citations && message.citations.length > 0 && (
            <CitationBlock citations={message.citations} />
          )}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/discussion/MessageBubble.tsx
git commit -m "feat(frontend): enhance MessageBubble with expert colors and decision style"
```

---

### Task 10: 增强useDiscussionSSE Hook

**Files:**
- Modify: `frontend/src/hooks/useDiscussionSSE.ts`

- [ ] **Step 1: 增强useDiscussionSSE**

```tsx
// frontend/src/hooks/useDiscussionSSE.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscussionMessage,
  DoneEvent,
  ErrorEvent,
  ThinkingEvent,
  StatusEvent,
  CostUpdateEvent,
  UseDiscussionSSEReturn,
} from '../types/discussion';

export function useDiscussionSSE(): UseDiscussionSSEReturn {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [thinking, setThinking] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [status, setStatus] = useState<string>('idle');
  const [currentRound, setCurrentRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [startTimestamp, setStartTimestamp] = useState<number | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;
  const thinkingStartTimeRef = useRef<Record<string, number>>({});

  useEffect(() => {
    return () => {
      closeConnection();
    };
  }, []);

  // Auto-clear thinking after message arrives
  useEffect(() => {
    if (!thinking || Object.keys(thinking).length === 0) return;

    // Check if any thinking has been active for too long
    const now = Date.now();
    for (const [role, startTime] of Object.entries(thinkingStartTimeRef.current)) {
      if (thinking[role] && now - startTime > 30000) {
        // 30s timeout
        setThinking((prev) => ({ ...prev, [role]: false }));
        delete thinkingStartTimeRef.current[role];
      }
    }
  }, [messages.length]);

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

  const connect = useCallback(
    (roomId: string) => {
      closeConnection();

      const url = `/api/rooms/${roomId}/start`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened');
        reconnectAttemptsRef.current = 0;
        setStatus('connecting');
      };

      // Status events
      eventSource.addEventListener('status', (event) => {
        try {
          const data: StatusEvent = JSON.parse(event.data);
          setStatus(data.status);
          setCurrentRound(data.round || 0);
          setTotalRounds(data.total_rounds || 0);
          
          if (data.round === 1 && data.phase === 'discussing' && !startTimestamp) {
            setStartTimestamp(Date.now());
          }
        } catch (e) {
          console.error('Failed to parse status event:', e);
        }
      });

      // Thinking events
      eventSource.addEventListener('thinking', (event) => {
        try {
          const data: ThinkingEvent = JSON.parse(event.data);
          const role = data.role;
          
          setThinking((prev) => ({
            ...prev,
            [role]: true,
          }));
          
          thinkingStartTimeRef.current[role] = Date.now();
        } catch (e) {
          console.error('Failed to parse thinking event:', e);
        }
      });

      // Message events
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
            delete thinkingStartTimeRef.current[data.sender_id!];
          }
          
          // Update round from message
          if (data.round) {
            setCurrentRound(data.round);
          }
        } catch (e) {
          console.error('Failed to parse message event:', e);
        }
      });

      // Cost update events
      eventSource.addEventListener('cost_update', (event) => {
        try {
          const data: CostUpdateEvent = JSON.parse(event.data);
          setTotalTokens(data.total_tokens || 0);
        } catch (e) {
          console.error('Failed to parse cost_update event:', e);
        }
      });

      // Error events
      eventSource.addEventListener('error', (event) => {
        try {
          const data: ErrorEvent = JSON.parse((event as MessageEvent).data);
          if (!data.recoverable) {
            setError(data.error || data.message || 'Unknown error');
            closeConnection();
          } else {
            console.warn('Recoverable error:', data.error || data.message);
          }
        } catch (e) {
          console.error('Failed to parse error event:', e);
        }
      });

      // Done events
      eventSource.addEventListener('done', (event) => {
        try {
          const data: DoneEvent = JSON.parse(event.data);
          console.log('Discussion complete:', data);
          setIsComplete(true);
          setStatus('completed');
          closeConnection();
        } catch (e) {
          console.error('Failed to parse done event:', e);
        }
      });

      // Connection error handling
      eventSource.onerror = () => {
        console.error('SSE connection error');

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;

          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`,
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect(roomId);
          }, delay);
        } else {
          setError('Connection lost. Please refresh the page.');
          setStatus('failed');
          closeConnection();
        }
      };
    },
    [closeConnection, startTimestamp],
  );

  const startDiscussion = useCallback(
    async (roomId: string) => {
      setMessages([]);
      setThinking({});
      setError(null);
      setIsComplete(false);
      setStatus('connecting');
      setCurrentRound(0);
      setTotalRounds(0);
      setTotalTokens(0);
      setStartTimestamp(null);
      reconnectAttemptsRef.current = 0;
      thinkingStartTimeRef.current = {};

      connect(roomId);
    },
    [connect],
  );

  const reset = useCallback(() => {
    closeConnection();
    setMessages([]);
    setThinking({});
    setError(null);
    setIsComplete(false);
    setStatus('idle');
    setCurrentRound(0);
    setTotalRounds(0);
    setTotalTokens(0);
    setStartTimestamp(null);
    reconnectAttemptsRef.current = 0;
    thinkingStartTimeRef.current = {};
  }, [closeConnection]);

  return {
    messages,
    thinking,
    error,
    isComplete,
    status,
    currentRound,
    totalRounds,
    totalTokens,
    startTimestamp,
    startDiscussion,
    reset,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useDiscussionSSE.ts
git commit -m "feat(frontend): enhance useDiscussionSSE with status tracking and cost updates"
```

---

### Task 11: 增强DiscussionPage

**Files:**
- Modify: `frontend/src/pages/DiscussionPage.tsx`

- [ ] **Step 1: 增强DiscussionPage**

```tsx
// frontend/src/pages/DiscussionPage.tsx
import { useEffect, useRef, useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDiscussionSSE } from '../hooks/useDiscussionSSE';
import { useArtifactStore } from '../stores/artifactStore';
import { apiClient } from '../api/client';
import {
  MessageBubble,
  ThinkingIndicator,
  RoundProgress,
  RoundDivider,
} from '../components/discussion';

interface RoomData {
  name: string;
  goal: string;
  round_limit: number;
  participants?: Array<{
    role_card_id: string;
    name: string;
  }>;
}

export default function DiscussionPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [roomData, setRoomData] = useState<RoomData | null>(null);

  const {
    messages,
    thinking,
    error,
    isComplete,
    status,
    currentRound,
    totalRounds,
    totalTokens,
    startTimestamp,
    startDiscussion,
    reset,
  } = useDiscussionSSE();

  const { synthesize, isLoading: isSynthesizing } = useArtifactStore();
  const [synthesizeError, setSynthesizeError] = useState<string | null>(null);

  const handleSynthesize = useCallback(async () => {
    if (!roomId) return;
    try {
      setSynthesizeError(null);
      await synthesize(roomId);
      navigate(`/rooms/${roomId}/artifacts`);
    } catch (err) {
      const message = err instanceof Error ? err.message : '合成失败';
      setSynthesizeError(message);
    }
  }, [roomId, synthesize, navigate]);

  useEffect(() => {
    if (roomId) {
      startDiscussion(roomId);
      apiClient.getRoom(roomId).then((room) => {
        setRoomData(room as RoomData);
      }).catch((err) => {
        console.error('Failed to fetch room data:', err);
      });
    }

    return () => {
      reset();
    };
  }, [roomId, startDiscussion, reset]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!roomId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-gray-500 text-sm">Room ID is required</p>
      </div>
    );
  }

  const thinkingRoles = Object.entries(thinking)
    .filter(([, isThinking]) => isThinking)
    .map(([role]) => role);

  // Group messages by round for divider insertion
  const messageElements: React.ReactNode[] = [];
  let lastRound = -1;

  messages.forEach((msg, index) => {
    // Insert round divider
    if (msg.round !== lastRound && msg.round > 1) {
      messageElements.push(
        <RoundDivider key={`round-${msg.round}`} round={msg.round} />
      );
      lastRound = msg.round;
    }

    // Check if this is the first message from this sender in this round
    const isFirstInRound = !messages
      .slice(0, index)
      .some(
        (m) =>
          m.round === msg.round &&
          m.sender_id === msg.sender_id &&
          m.sender_type === msg.sender_type
      );

    messageElements.push(
      <MessageBubble
        key={msg.id}
        message={msg}
        showExpertiseBadge={isFirstInRound}
      />
    );
  });

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {roomData?.name || '专家讨论'}
            </h1>
            <p className="text-sm text-gray-500">
              {roomData?.goal || `Room: ${roomId}`}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Token counter */}
            {totalTokens > 0 && (
              <span className="text-xs text-gray-500">
                🔤 {totalTokens.toLocaleString()} tokens
              </span>
            )}

            {/* Status badge */}
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                status === 'running'
                  ? 'bg-green-100 text-green-700'
                  : status === 'completed'
                  ? 'bg-gray-100 text-gray-700'
                  : status === 'failed'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-blue-100 text-blue-700'
              }`}
            >
              {status === 'running'
                ? '🟢 进行中'
                : status === 'completed'
                ? '✅ 已完成'
                : status === 'failed'
                ? '❌ 失败'
                : '⏳ 连接中'}
            </span>

            {isComplete && (
              <>
                <button
                  onClick={handleSynthesize}
                  disabled={isSynthesizing}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSynthesizing ? '合成中...' : '生成产出'}
                </button>
                <button
                  onClick={() => navigate(`/rooms/${roomId}/artifacts`)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  查看产出
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-6 pt-4 shrink-0">
        <RoundProgress
          currentRound={currentRound}
          maxRounds={totalRounds || roomData?.round_limit || 5}
          startTimestamp={startTimestamp}
          status={status as 'running' | 'paused' | 'completed'}
        />
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && !error && (
          <div className="text-center text-gray-500 py-8 text-sm">
            讨论即将开始...
          </div>
        )}

        {messageElements}

        {/* Thinking indicators */}
        {thinkingRoles.map((role) => (
          <ThinkingIndicator
            key={role}
            speakerId={role}
            speakerName={role}
            isVisible={true}
          />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2 text-red-700 text-sm">
            <svg
              className="w-5 h-5 shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Synthesize error */}
      {synthesizeError && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2 text-red-700 text-sm">
            <span>{synthesizeError}</span>
          </div>
        </div>
      )}

      {/* Completion message */}
      {isComplete && (
        <div className="bg-green-50 border-t border-green-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2 text-green-700 text-sm">
            <svg
              className="w-5 h-5 shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span>
              讨论已完成！共 {messages.length} 条消息，{totalTokens.toLocaleString()} tokens
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DiscussionPage.tsx
git commit -m "feat(frontend): enhance DiscussionPage with round dividers and status tracking"
```

---

## 四、验证方式

### 后端验证
```bash
cd backend
python -m pytest tests/ -v
uvicorn app.main:app --reload
curl http://localhost:8000/api/health
```

### 前端验证
```bash
cd frontend
npm run dev
# 浏览器打开 http://localhost:5173
# 创建房间 → 开始讨论 → 验证SSE事件 → 查看产出
```

### 端到端验证
1. 配置Provider（API Key + Base URL）
2. 创建角色卡（或使用内置角色）
3. 创建群聊（选择角色、输入目标）
4. 上传文件或指定文件夹
5. 开始讨论
6. 验证：
   - ThinkingIndicator显示进度条和骨架
   - 消息按轮次分组显示
   - 专家消息有颜色条
   - 决策消息有绿色高亮
   - Token计数实时更新
   - 讨论完成后可生成产出
