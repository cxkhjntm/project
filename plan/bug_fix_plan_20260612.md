# 专家团讨论系统 Bug 修复计划

> 生成时间：2026-06-12
> 分析范围：完整后端 + 前端代码审计
> 核心问题：设置了 5 轮讨论但 2 轮就提前结束

---

## Bug 总览

| # | 严重度 | Bug 描述 | 影响范围 | 涉及文件 |
|---|--------|----------|----------|----------|
| 1 | 🔴 严重 | 关键词收敛误判导致讨论提前结束 | 核心流程 | `orchestrator.py` |
| 2 | 🔴 严重 | 主持人 LLM 可随时发 converge/synthesize 提前终止 | 核心流程 | `orchestrator.py` |
| 3 | 🟡 中等 | 重新讨论时不清理旧消息，rolling_summary 混乱 | 讨论质量 | `discussion.py`, `orchestrator.py` |
| 4 | 🟡 中等 | 前端 startDiscussion reset 后立即 loadHistory 导致旧消息回显 | 前端显示 | `useDiscussionSSE.ts` |
| 5 | 🟡 中等 | DiscussionStatusResponse.current_round 始终返回 0 | 前端状态 | `routers/discussion.py` |
| 6 | 🟢 低 | `_build_role_definition` 方法重复定义 | 代码质量 | `context_builder.py` |
| 7 | 🟢 低 | `_build_file_contents_with_budget` 方法重复定义 | 代码质量 | `context_builder.py` |
| 8 | 🟢 低 | rolling_summary 截断策略丢失早期上下文 | 讨论质量 | `context_builder.py` |
| 9 | 🟢 低 | 主持人 prompt 收敛引导过于激进 | 讨论质量 | `context_builder.py` |

---

## Bug 1 🔴 关键词收敛误判导致讨论提前结束

### 问题描述
`orchestrator.py` 的 `_check_convergence()` 方法使用硬编码关键词列表判断讨论是否收敛。只要第 2 轮之后，有 ≥2 个专家的消息中包含"同意"、"可行"、"没问题"等关键词，就会立即终止讨论。

专家在正常讨论中经常会使用"这个方案可行，但需要注意..."这样的措辞，导致误触发收敛判断。

### 代码定位

**文件**: `backend/app/services/orchestrator.py`

```python
# L18-31: 关键词列表（过于宽泛）
CONVERGENCE_KEYWORDS = [
    "可行", "同意", "没有异议", "建议直接", "没问题",
    "LGTM", "一致", "共识", "确认", "通过", "赞成", "支持",
]

# L66-81: 基于关键词的收敛检测
def check_convergence(messages, min_consensus=2):
    # ...只要 2 个专家消息包含关键词就返回 True

# L737-742: 在每轮结束时调用
def _check_convergence(self):
    if self.current_round >= self.max_rounds:
        return True
    if self.current_round < 2:
        return False
    return check_convergence(self.all_messages)  # ← 第 2 轮就可能触发
```

**文件**: `backend/app/services/orchestrator.py` L333-334
```python
if self._check_convergence():
    break  # ← 直接退出主循环
```

### 修复方案

**目标**: 用 LLM 模型替代关键词匹配，输出"方向整体同意度"和"方案冲突度"两个数值，用户可配置门槛。

#### 步骤 1: 新增全局设置模型 — 数据库字段

**文件**: 新建 `backend/app/models/settings.py`

```python
"""Global application settings model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    """Application-level key-value settings."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
```

需要在数据库初始化时创建此表，并预设默认值：
- `convergence_provider_id`: 空字符串（表示未配置）
- `convergence_model_override`: 空字符串（使用 provider 默认模型）

#### 步骤 2: 新增全局设置 API

**文件**: 新建 `backend/app/routers/settings.py`

```python
router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("")
async def get_settings(session) -> dict:
    """获取所有全局设置"""
    ...

@router.put("")
async def update_settings(session, data: dict) -> dict:
    """更新全局设置"""
    ...
```

#### 步骤 3: Room 模型新增收敛参数字段

**文件**: `backend/app/models/room.py`

在 `Room` 模型中新增以下字段：

```python
# 收敛判断参数
convergence_agreement_threshold: Mapped[int] = mapped_column(
    Integer, default=85  # 方向整体同意度阈值，百分比
)
convergence_conflict_threshold: Mapped[int] = mapped_column(
    Integer, default=5   # 方案冲突度阈值，百分比
)
convergence_provider_id: Mapped[str | None] = mapped_column(
    String(36), ForeignKey("providers.id"), nullable=True  # 房间级覆盖
)
convergence_model_override: Mapped[str | None] = mapped_column(
    String(100), nullable=True  # 房间级覆盖模型
)
```

同步更新：
- `backend/app/schemas/room.py` — `RoomCreate`、`RoomUpdate`、`RoomResponse` 增加对应字段
- `frontend/src/types/index.ts` — `RoomCreate`、`Room` 类型增加对应字段

#### 步骤 4: 新增收敛判断服务

**文件**: 新建 `backend/app/services/convergence_judge.py`

```python
"""LLM-based convergence judge for expert discussions."""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

class ConvergenceResult:
    """收敛判断结果"""
    agreement_score: int      # 方向整体同意度 0-100
    conflict_score: int       # 方案冲突度 0-100
    should_converge: bool     # 是否满足收敛条件
    reasoning: str            # 判断理由

class ConvergenceJudge:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def judge(
        self,
        messages: list[dict[str, Any]],
        current_round: int,
        goal: str,
        agreement_threshold: int = 85,
        conflict_threshold: int = 5,
        provider_id: str | None = None,
        model_override: str | None = None,
    ) -> ConvergenceResult:
        """
        调用 LLM 分析当前轮次所有专家的发言，判断收敛程度。
        
        LLM prompt 要求输出 JSON:
        {
            "agreement_score": 75,    // 0-100
            "conflict_score": 10,     // 0-100
            "reasoning": "专家A和B在架构方向上一致，但C对数据库选择有不同意见..."
        }
        
        收敛条件: agreement_score >= agreement_threshold AND conflict_score <= conflict_threshold
        """
        ...

    async def _get_client(self, provider_id, model_override):
        """
        获取收敛判断用的 LLM client。
        优先级: 房间级 provider_id > 全局设置 convergence_provider_id > 第一个 participant 的 provider
        """
        ...

    def _build_prompt(self, messages, current_round, goal) -> str:
        """
        构建收敛判断 prompt。
        要求 LLM 分析本轮所有专家发言，输出结构化 JSON。
        prompt 中要强调:
        - "同意某个观点" 不等于 "整体方向收敛"
        - 需要分析所有专家的核心立场是否一致
        - 方案冲突指存在互斥的技术路线或根本分歧
        """
        return f"""你是一个讨论收敛判断分析器。请分析以下专家讨论，判断讨论的收敛程度。

## 讨论目标
{goal}

## 当前轮次
第 {current_round} 轮

## 本轮专家发言
{self._format_messages(messages)}

## 输出要求
请严格输出以下 JSON 格式（不要输出其他内容）：
```json
{{
    "agreement_score": <0-100的整数，表示专家们在核心方向上的一致程度>,
    "conflict_score": <0-100的整数，表示专家之间存在的方案冲突程度>,
    "reasoning": "<简要说明判断依据，50字以内>"
}}
```

## 判断标准
- agreement_score: 所有专家对核心问题的方向是否一致。注意"同意某个细节"不代表整体收敛。
- conflict_score: 是否存在互斥的技术路线、根本性分歧或未解决的关键争议。
- 仅当所有专家都对核心方向明确表态一致时，agreement_score 才应 >= 85。
- 如果任何专家提出了未被回应的重大反对意见，conflict_score 应 >= 20。"""
```

#### 步骤 5: 修改 Orchestrator 使用新的收敛判断

**文件**: `backend/app/services/orchestrator.py`

**修改点 1**: 删除旧的关键词收敛逻辑

```python
# 删除以下代码:
# - CONVERGENCE_KEYWORDS 列表 (L18-31)
# - check_convergence 函数 (L66-81)
```

**修改点 2**: 修改 `__init__` 方法，加载收敛参数

```python
def __init__(self, session, room, on_event=None):
    # ... 现有代码 ...
    
    # 新增: 收敛参数
    self.agreement_threshold = getattr(room, 'convergence_agreement_threshold', 85)
    self.conflict_threshold = getattr(room, 'convergence_conflict_threshold', 5)
    self.convergence_provider_id = getattr(room, 'convergence_provider_id', None)
    self.convergence_model_override = getattr(room, 'convergence_model_override', None)
```

**修改点 3**: 重写 `_check_convergence` 方法

```python
async def _check_convergence(self) -> bool:
    """使用 LLM 判断收敛，替代关键词匹配。"""
    if self.current_round >= self.max_rounds:
        return True
    if self.current_round < 2:
        return False
    
    from app.services.convergence_judge import ConvergenceJudge
    
    judge = ConvergenceJudge(self.session)
    # 取当前轮的专家消息
    current_round_messages = [
        m for m in self.all_messages 
        if m.get("round") == self.current_round and m.get("sender_type") == "expert"
    ]
    if len(current_round_messages) < 2:
        return False
    
    try:
        result = await judge.judge(
            messages=current_round_messages,
            current_round=self.current_round,
            goal=self.goal,
            agreement_threshold=self.agreement_threshold,
            conflict_threshold=self.conflict_threshold,
            provider_id=self.convergence_provider_id,
            model_override=self.convergence_model_override,
        )
        
        if result.should_converge:
            logger.info(
                "LLM convergence judge: converged",
                agreement=result.agreement_score,
                conflict=result.conflict_score,
                reasoning=result.reasoning,
            )
        return result.should_converge
    except Exception as e:
        logger.warning("Convergence judge failed, continuing discussion", error=str(e))
        return False  # 出错时不收敛，继续跑
```

**修改点 4**: `_check_convergence` 调用变为 async

由于 `_check_convergence` 现在是 async 方法，`run_discussion` 中的调用需要改为：

```python
# 原来 (L333):
if self._check_convergence():
    break

# 改为:
if await self._check_convergence():
    break
```

**修改点 5**: 主持人 converge/synthesize 指令改为双重确认

```python
# 原来 (L327-331):
if action and action.get("type") == "converge":
    break
if action and action.get("type") == "synthesize":
    break

# 改为:
if action and action.get("type") in ("converge", "synthesize"):
    # 双重确认：主持人认为可以收敛，再用模型确认
    if await self._check_convergence():
        break
    else:
        logger.info(
            "Host suggested convergence but LLM judge disagreed, continuing",
            round=self.current_round,
        )
```

---

## Bug 2 🔴 主持人 prompt 收敛引导过于激进

### 问题描述

`context_builder.py` L191-203 中，当 `current_round >= total_rounds - 1` 时（即倒数第二轮），prompt 就会告诉主持人"当前已是最后几轮，请优先评估是否满足收敛条件"。

这意味着对于 5 轮讨论，第 4 轮就开始引导收敛。结合 Bug 1 的关键词误判，很容易在第 2-3 轮就结束。

### 代码定位

**文件**: `backend/app/services/context_builder.py` L191-203

```python
is_near_end = current_round >= total_rounds - 1  # 5轮讨论中第4轮就触发

convergence_section = """
## 收敛判断标准
当以下条件满足时，判断讨论已收敛：
- 专家们的观点已经达成一致...
"""

if is_near_end:
    convergence_section += """
注意：当前已是最后几轮，请优先评估是否满足收敛条件。"""
```

### 修复方案

**文件**: `backend/app/services/context_builder.py`

1. 收敛引导的时机改为最后一轮（`current_round >= total_rounds`），而非倒数第二轮
2. 删除 prompt 中的收敛判断标准，因为收敛判断已由独立的 LLM 收敛判断服务负责
3. 主持人 prompt 只负责引导讨论方向，不负责判断是否收敛

```python
# 修改 build_orchestrator_prompt 方法:

# 1. 去掉 convergence_section，替换为简单的轮次提示
round_hint = ""
if current_round >= total_rounds:
    round_hint = "\n注意：这是最后一轮讨论，请引导专家们做最终总结。"
elif current_round >= total_rounds - 1:
    round_hint = "\n提示：讨论即将进入最后阶段。"

# 2. 从 ACTION 指令中删除 converge 和 synthesize
# 主持人不应该有权直接终止讨论，收敛判断由独立服务负责
# 修改输出格式要求:
"""
## 输出格式要求
你的回复必须以 ACTION 指令结尾，格式如下：
- `ACTION: focus:<专家名称1,专家名称2>` — 指定本轮必须重点回应的专家
- `ACTION: continue` — 继续正常讨论

请用简洁的主持词引导讨论（不超过 200 字），并在末尾输出 ACTION 指令。
"""
```

> **注意**: 保留 `converge` 和 `synthesize` 的 parse 能力（因为 LLM 可能仍会生成），但在 orchestrator 中会经过双重确认（Bug 1 的修复方案）。

---

## Bug 3 🟡 重新讨论时不清理旧消息

### 问题描述

当用户点击"重新讨论"按钮时，`discussion.py` 的 `start_discussion` 路由只是将房间状态设为 `running` 并启动新任务，**不会清理数据库中该房间的旧消息**。

这导致：
1. Orchestrator 的 `_update_rolling_summary` 会从数据库加载**所有历史消息**（包括上一次讨论的），rolling_summary 中混入旧内容
2. 前端加载历史消息时也会显示上一次讨论的消息

### 代码定位

**文件**: `backend/app/routers/discussion.py` L40-46

```python
async def _mark_running_and_start_task(room: Room, session: AsyncSession) -> None:
    if not room.participants:
        raise HTTPException(status_code=400, detail="Room has no participants")
    room.status = "running"
    await session.commit()
    discussion_runtime.ensure_started(room.id)
    # ← 没有清理旧消息！
```

### 修复方案

**文件**: `backend/app/routers/discussion.py`

在 `_mark_running_and_start_task` 中，当房间从终态（`completed`/`failed`/`stopped`）重新开始时，清理旧消息：

```python
async def _mark_running_and_start_task(room: Room, session: AsyncSession) -> None:
    if not room.participants:
        raise HTTPException(status_code=400, detail="Room has no participants")
    
    # 如果是从终态重新开始，清理旧消息
    if room.status in STARTABLE_STATUSES - {"draft", "idle"}:
        from app.models.message import Message
        await session.execute(
            delete(Message).where(Message.room_id == room.id)
        )
    
    room.status = "running"
    await session.commit()
    discussion_runtime.ensure_started(room.id)
```

需要 `from sqlalchemy import delete` 在文件顶部。

---

## Bug 4 🟡 前端 startDiscussion reset 后立即 loadHistory

### 问题描述

`useDiscussionSSE.ts` 的 `startDiscussion` 方法中，当 `reset: true` 时先清空 messages，然后立即调用 `loadHistory`。如果数据库中还有旧消息（Bug 3 未修复的情况下），清空后的 messages 状态会被旧消息覆盖。

### 代码定位

**文件**: `frontend/src/hooks/useDiscussionSSE.ts` L275-307

```typescript
const startDiscussion = useCallback(async (roomId, options) => {
    if (shouldReset) {
        setMessages([]);        // ← 先清空
        // ...
    }
    // ...
    await loadHistory(roomId, options.initialStatus);  // ← 立即从数据库加载旧消息
    if (shouldConnect) {
        connect(roomId);
    }
}, ...);
```

### 修复方案

**文件**: `frontend/src/hooks/useDiscussionSSE.ts`

当 `reset: true` 时，不应调用 `loadHistory`：

```typescript
const startDiscussion = useCallback(async (roomId, options) => {
    const shouldReset = options.reset ?? true;
    const shouldConnect = options.connect ?? true;

    if (shouldReset) {
        setMessages([]);
        setTotalTokens(0);
        setStartTimestamp(null);
        setArtifact(null);
        setArtifacts([]);
        setDiscussionLog(null);
        setFallbackUsed(false);
    }
    setThinking({});
    clearTokenBuffer();
    setError(null);
    setIsComplete(false);
    setStatus(options.initialStatus || 'connecting');
    setCurrentRound(0);
    setTotalRounds(0);
    reconnectAttemptsRef.current = 0;

    // 修改: 只有非 reset 模式才加载历史
    if (!shouldReset) {
        await loadHistory(roomId, options.initialStatus);
    }
    
    if (shouldConnect) {
        connect(roomId);
    }
}, [clearTokenBuffer, connect, loadHistory]);
```

---

## Bug 5 🟡 DiscussionStatusResponse.current_round 始终返回 0

### 问题描述

`discussion.py` 的 `get_discussion_status` 端点中，`current_round` 被硬编码为 `0`，永远不反映实际轮次。

### 代码定位

**文件**: `backend/app/routers/discussion.py` L380-400

```python
@router.get("/{room_id}/status", response_model=DiscussionStatusResponse)
async def get_discussion_status(room_id, session):
    # ...
    return DiscussionStatusResponse(
        room_id=room.id,
        status=room.status,
        current_round=0,           # ← 硬编码为 0
        total_rounds=room.round_limit,
        # ...
    )
```

### 修复方案

**文件**: `backend/app/routers/discussion.py`

```python
return DiscussionStatusResponse(
    room_id=room.id,
    status=room.status,
    current_round=await message_service.get_latest_round(session, room_id),  # ← 读取实际轮次
    total_rounds=room.round_limit,
    is_paused=room.status == "paused",
    can_pause=room.status == "running",
    can_resume=room.status == "paused",
    can_stop=room.status in ("running", "paused"),
)
```

---

## Bug 6 🟢 `_build_role_definition` 方法重复定义

### 问题描述

`context_builder.py` 中 `_build_role_definition` 方法被定义了两次（L262-281 和 L320-341），代码完全相同。Python 后定义会覆盖前定义，不会报错但造成代码冗余和维护风险。

### 代码定位

**文件**: `backend/app/services/context_builder.py`

- 第一次定义: L262-281
- 第二次定义: L320-341（完全相同）

### 修复方案

删除第二次定义（L320-341），保留第一次定义（L262-281）。

---

## Bug 7 🟢 `_build_file_contents_with_budget` 方法重复定义

### 问题描述

同 Bug 6，`_build_file_contents_with_budget` 方法被定义了两次（L343-370 和 L400-421），代码完全相同。

### 代码定位

**文件**: `backend/app/services/context_builder.py`

- 第一次定义: L343-370
- 第二次定义: L400-421（完全相同）

### 修复方案

删除第二次定义（L400-421），保留第一次定义（L343-370）。

---

## Bug 8 🟢 rolling_summary 截断策略丢失早期上下文

### 问题描述

`context_builder.py` 的 `build_rolling_summary` 方法中，当 summary 超长时的截断策略有问题：

```python
# L457-458
if len(combined) > max_chars:
    combined = combined[-max_chars:]  # ← 从尾部保留，丢失头部
```

这意味着当讨论进行到后面几轮时，早期轮次的重要上下文（如初始共识、核心分歧）会被完全丢弃。

### 修复方案

**文件**: `backend/app/services/context_builder.py`

改为保留头部摘要 + 尾部最新内容的策略：

```python
def build_rolling_summary(self, existing_summary, new_messages):
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

    max_chars = self.max_summary_tokens * self.chars_per_token
    if len(combined) > max_chars:
        # 保留头部 30% 作为早期上下文 + 尾部 70% 作为最新讨论
        head_budget = int(max_chars * 0.3)
        tail_budget = max_chars - head_budget
        head = combined[:head_budget]
        tail = combined[-tail_budget:]
        combined = head + "\n\n...(中间内容已省略)...\n\n" + tail

    return combined
```

---

## Bug 9 🟢 主持人 prompt 收敛引导过于激进（补充说明）

此 bug 的修复方案已包含在 Bug 2 中。这里补充具体的代码变更。

### 代码定位

**文件**: `backend/app/services/context_builder.py` L141-143

```python
round_context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
if current_round >= total_rounds - 1:
    round_context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"
```

### 修复方案

```python
round_context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
if current_round >= total_rounds:
    round_context += "\n注意：这是最后一轮讨论，请做最终总结。"
elif current_round == total_rounds - 1:
    round_context += "\n提示：下一轮是最后一轮讨论。"
elif current_round == 1:
    round_context += "\n这是第一轮讨论，请从你的专业角度给出初步观点。"
```

---

## 前端配套修改

### 1. Room 创建表单增加收敛参数

**文件**: `frontend/src/components/room/RoomForm.tsx`

在创建房间表单中增加两个配置项：
- **方向整体同意度阈值** (agreement_threshold): 滑块或数字输入框，默认 85，范围 50-100
- **方案冲突度阈值** (conflict_threshold): 滑块或数字输入框，默认 5，范围 0-50

UI 建议放在"高级设置"折叠面板中，附带说明文字：
> 当所有专家的方向整体同意度 ≥ 设定值，且方案冲突度 ≤ 设定值时，讨论将自动收敛结束。建议使用默认值。

### 2. 设置页增加收敛判断模型选择

**文件**: `frontend/src/pages/SettingsPage.tsx`

在 Provider 列表下方增加一个"全局设置"区域：
- **收敛判断模型**: 下拉框，从已有 Provider 列表中选择，附带提示："建议选择响应快的轻量级模型（如 gpt-4o-mini），以减少每轮收敛判断的等待时间"

### 3. 前端类型更新

**文件**: `frontend/src/types/index.ts`

```typescript
export interface RoomCreate {
    name: string;
    goal: string;
    mode?: RoomMode;
    output_directory: string;
    round_limit?: number;
    participants: ParticipantInput[];
    // 新增:
    convergence_agreement_threshold?: number;  // 默认 85
    convergence_conflict_threshold?: number;   // 默认 5
    convergence_provider_id?: string;
    convergence_model_override?: string;
}
```

### 4. API Client 更新

**文件**: `frontend/src/api/client.ts`

新增设置相关 API 方法：

```typescript
// === Settings ===
async getSettings(): Promise<Record<string, string>> {
    return this.request('/settings');
}

async updateSettings(data: Record<string, string>): Promise<Record<string, string>> {
    return this.request('/settings', { method: 'PUT', body: data });
}
```

---

## 后端 Schema 修改汇总

### `backend/app/schemas/room.py`

```python
class RoomCreate(BaseModel):
    # ... 现有字段 ...
    convergence_agreement_threshold: int = Field(85, ge=50, le=100, description="方向整体同意度阈值")
    convergence_conflict_threshold: int = Field(5, ge=0, le=50, description="方案冲突度阈值")

class RoomUpdate(BaseModel):
    # ... 现有字段 ...
    convergence_agreement_threshold: int | None = Field(None, ge=50, le=100)
    convergence_conflict_threshold: int | None = Field(None, ge=0, le=50)

class RoomResponse(BaseModel):
    # ... 现有字段 ...
    convergence_agreement_threshold: int
    convergence_conflict_threshold: int
    convergence_provider_id: str | None = None
    convergence_model_override: str | None = None
```

---

## 数据库迁移

需要执行以下数据库变更：

1. **新建** `app_settings` 表
2. **修改** `rooms` 表，增加 4 个字段:
   - `convergence_agreement_threshold` INTEGER DEFAULT 85
   - `convergence_conflict_threshold` INTEGER DEFAULT 5
   - `convergence_provider_id` VARCHAR(36) NULLABLE
   - `convergence_model_override` VARCHAR(100) NULLABLE

由于项目使用 SQLite（`expert_room.db`），可以在应用启动时通过 `ALTER TABLE` 或重建数据库来迁移。

---

## 修复优先级与依赖关系

```
阶段1: 核心收敛 Bug 修复 (Bug 1 + Bug 2)
    ├── 1.1 新建 app_settings 模型和 API
    ├── 1.2 Room 模型增加收敛参数字段
    ├── 1.3 新建 convergence_judge.py 收敛判断服务
    ├── 1.4 修改 orchestrator.py 使用新的收敛判断
    └── 1.5 修改 context_builder.py 主持人 prompt

阶段2: 讨论流程 Bug 修复 (Bug 3 + Bug 4 + Bug 5)
    ├── 2.1 修改 discussion.py 重新讨论时清理旧消息
    ├── 2.2 修改 useDiscussionSSE.ts reset 逻辑
    └── 2.3 修改 discussion.py current_round 返回值

阶段3: 代码质量修复 (Bug 6 + Bug 7 + Bug 8 + Bug 9)
    ├── 3.1 删除 context_builder.py 重复方法定义
    ├── 3.2 优化 rolling_summary 截断策略
    └── 3.3 调整专家 prompt 中的收敛提示时机

阶段4: 前端配套 UI
    ├── 4.1 RoomForm 增加收敛参数配置
    ├── 4.2 SettingsPage 增加收敛判断模型选择
    └── 4.3 前端类型和 API Client 更新
```

---

## 验证清单

- [ ] 设置 5 轮讨论，确认确实跑满 5 轮（除非 LLM 收敛判断确认收敛）
- [ ] 设置不同的 agreement/conflict 阈值，验证收敛判断行为正确
- [ ] 测试"重新讨论"功能，确认旧消息被清理
- [ ] 测试暂停/继续讨论功能正常
- [ ] 验证前端轮次显示正确
- [ ] 验证产出物正常生成
- [ ] 收敛判断模型 API 调用失败时，应降级为继续讨论（不收敛）
- [ ] 全局设置和房间级覆盖的优先级正确
