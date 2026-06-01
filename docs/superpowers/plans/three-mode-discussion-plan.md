# 三模式讨论功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现专家团的三模式讨论功能，支持代码文档模式、纯文档模式和代码模式，修复讨论室详情页路由问题。

**Architecture:** 扩展 ContextBuilder 支持三种模式的 prompt 模板，扩展 ArtifactWriter 支持不同格式的产出生成，修复前端路由让讨论室详情页正确显示讨论界面。

**Tech Stack:** Python FastAPI + SQLAlchemy (backend), React 18 + TypeScript + Tailwind (frontend)

---

## 一、当前状态分析

### 已实现 ✅
- 讨论页 (`/rooms/:roomId/discussion`) - 完整的 DiscussionPage 组件
- 后端讨论引擎 - orchestrator.py 基本讨论调度
- ContextBuilder - 支持"代码文档模式"的 prompt 构建
- ArtifactWriter - 生成 Markdown 格式产出

### 需要实现 ❌
1. **路由问题** - `rooms/:id` 显示 PlaceholderPage 而非讨论界面
2. **模式支持** - ContextBuilder 硬编码"代码文档模式"
3. **产出格式** - ArtifactWriter 只生成 Markdown
4. **模式选择** - 前端缺少模式切换 UI

---

## 二、文件结构

### 后端修改文件
- `backend/app/services/context_builder.py` — 添加模式参数，支持三种 prompt 模板
- `backend/app/services/artifact_writer.py` — 添加模式参数，支持不同格式产出
- `backend/app/services/orchestrator.py` — 传递模式参数

### 前端修改文件
- `frontend/src/routes.tsx` — 修复路由，讨论室详情页重定向
- `frontend/src/pages/DiscussionPage.tsx` — 显示当前模式信息
- `frontend/src/pages/RoomCreatePage.tsx` — 模式选择 UI 已存在

---

## 三、任务清单

### Task 1: 修复路由 - 讨论室详情页重定向

**Files:**
- Modify: `frontend/src/routes.tsx`

- [ ] **Step 1: 修改路由配置**

```tsx
// frontend/src/routes.tsx
import { createBrowserRouter, Navigate } from 'react-router-dom';
import Layout from '@/components/shared/Layout';
import HomePage from '@/pages/HomePage';
import SettingsPage from '@/pages/SettingsPage';
import RoleCardsPage from '@/pages/RoleCardsPage';
import RoomsPage from '@/pages/RoomsPage';
import RoomCreatePage from '@/pages/RoomCreatePage';
import DiscussionPage from '@/pages/DiscussionPage';
import ArtifactPage from '@/pages/ArtifactPage';

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
      // 重定向到讨论页
      { 
        path: 'rooms/:id', 
        element: <Navigate to="/rooms/:id/discussion" replace /> 
      },
    ],
  },
  {
    path: '/rooms/:roomId/discussion',
    element: <DiscussionPage />,
  },
  {
    path: '/rooms/:roomId/artifacts',
    element: <ArtifactPage />,
  },
]);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes.tsx
git commit -m "fix(frontend): redirect room detail page to discussion page"
```

---

### Task 2: 扩展 ContextBuilder 支持三种模式

**Files:**
- Modify: `backend/app/services/context_builder.py`

- [ ] **Step 1: 添加模式常量和 prompt 模板**

```python
# backend/app/services/context_builder.py
"""Context builder for discussion prompts with token budget management."""

from typing import Any, Dict, List, Optional
from enum import Enum

from app.utils.logger import get_logger
from app.utils.token_counter import (
    TokenBudget,
    estimate_tokens,
    check_budget,
    get_degradation_action,
    TOKEN_ESTIMATES,
)

logger = get_logger(__name__)

# Role definition compression threshold
FULL_ROLE_ROUNDS = 2


class DiscussionMode(str, Enum):
    """讨论模式枚举"""
    CODE_DOCUMENT = "code_document"  # 代码文档模式
    DOCUMENT = "document"            # 纯文档模式
    CODE = "code"                    # 代码模式


# 模式特定的 prompt 模板
MODE_TEMPLATES = {
    DiscussionMode.CODE_DOCUMENT: {
        "name": "代码文档模式",
        "description": "产出适合交给 AI 编辑器或开发人员执行的 Markdown 技术方案",
        "expert_instruction": """
请从你的专业角度，对当前议题发表意见。
要求：
- 引用共享资料中的具体内容时，请标注来源文件名
- 区分"资料中明确的信息"和"你的推断/建议"
- 回复控制在 500 字以内
- 如果是最后几轮，请重点总结你的核心观点
- 重点关注技术实现方案、架构设计、接口定义""",
        "synthesizer_chapters": """
## 1. 背景与目标
## 2. 当前资料理解
## 3. 需求拆解
## 4. 总体方案
## 5. 模块设计
## 6. 数据结构 / 接口设计
## 7. 实施步骤
## 8. 测试与验收标准
## 9. 风险与取舍
## 10. 后续迭代建议""",
        "output_format": "Markdown 技术方案文档",
    },
    DiscussionMode.DOCUMENT: {
        "name": "纯文档模式",
        "description": "产出适合阅读、汇报、归档的文档或表格",
        "expert_instruction": """
请从你的专业角度，对当前议题发表意见。
要求：
- 引用共享资料中的具体内容时，请标注来源文件名
- 区分"资料中明确的信息"和"你的推断/建议"
- 回复控制在 500 字以内
- 如果是最后几轮，请重点总结你的核心观点
- 重点关注可读性、结论明确、结构清晰、适合汇报""",
        "synthesizer_chapters": """
## 1. 执行摘要
## 2. 背景与目标
## 3. 现状分析
## 4. 核心发现
## 5. 结论与建议
## 6. 数据来源说明
## 7. 附录""",
        "output_format": "可阅读的文档报告",
    },
    DiscussionMode.CODE: {
        "name": "代码模式",
        "description": "产出核心代码草案，用于快速判断技术方向是否可行",
        "expert_instruction": """
请从你的专业角度，对当前议题发表意见。
要求：
- 引用共享资料中的具体内容时，请标注来源文件名
- 区分"资料中明确的信息"和"你的推断/建议"
- 回复控制在 500 字以内
- 如果是最后几轮，请重点总结你的核心观点
- 重点关注核心代码实现、算法设计、数据结构""",
        "synthesizer_chapters": """
## 1. 实现概述
## 2. 核心代码
## 3. 使用示例
## 4. 依赖说明
## 5. 集成方式
## 6. 注意事项
## 7. 测试建议""",
        "output_format": "核心代码草案和说明文档",
    },
}


class ContextBuilder:
    """Builds context for LLM prompts with token budget management."""

    def __init__(
        self,
        max_file_tokens: int = 4000,
        max_summary_tokens: int = 1000,
        budget: Optional[TokenBudget] = None,
    ):
        self.max_file_tokens = max_file_tokens
        self.max_summary_tokens = max_summary_tokens
        self.chars_per_token = TOKEN_ESTIMATES["english_chars_per_token"]
        self.budget = budget or TokenBudget()

    def build_expert_prompt(
        self,
        role: Dict[str, Any],
        goal: str,
        shared_sources: List[Dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        mode: str = "code_document",
        additional_context: Optional[str] = None,
    ) -> str:
        """构建专家 prompt，支持三种模式"""
        role_def = self._build_role_definition(role, current_round)
        file_contents = self._build_file_contents_with_budget(
            shared_sources, int(self.budget.shared_data * self.chars_per_token)
        )

        # 获取模式配置
        try:
            discussion_mode = DiscussionMode(mode)
        except ValueError:
            discussion_mode = DiscussionMode.CODE_DOCUMENT
            logger.warning(f"Unknown mode '{mode}', falling back to code_document")

        mode_config = MODE_TEMPLATES[discussion_mode]

        round_context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
        if current_round >= total_rounds - 1:
            round_context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"

        prompt = f"""{role_def}

## 本次任务
目标：{goal}
工作模式：{mode_config['name']} - {mode_config['description']}
{round_context}

## 共享资料
{file_contents if file_contents else "无共享资料"}

## 已有讨论
{rolling_summary if rolling_summary else "这是讨论的开始，还没有已有讨论。"}

## 本轮要求
{mode_config['expert_instruction']}"""

        if additional_context:
            prompt += f"\n\n## 补充信息\n{additional_context}"

        estimated = estimate_tokens(prompt)
        budget_check = check_budget(estimated, self.budget)
        if not budget_check["within_budget"]:
            logger.warning(
                "Prompt exceeds token budget",
                estimated=estimated,
                usage_pct=budget_check["usage_pct"],
            )

        return prompt

    def build_orchestrator_prompt(
        self,
        goal: str,
        shared_sources: List[Dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        experts: List[Dict[str, Any]],
        mode: str = "code_document",
    ) -> str:
        """构建主持人 prompt，支持三种模式"""
        expert_names = ", ".join(e["name"] for e in experts)
        file_contents = self._build_file_contents(shared_sources)

        # 获取模式配置
        try:
            discussion_mode = DiscussionMode(mode)
        except ValueError:
            discussion_mode = DiscussionMode.CODE_DOCUMENT

        mode_config = MODE_TEMPLATES[discussion_mode]

        prompt = f"""你是专家群聊主持人。你的任务是控制讨论流程，而不是替专家完成全部内容。

本次任务目标：{goal}
当前工作模式：{mode_config['name']} - {mode_config['description']}
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
        mode: str = "code_document",
    ) -> str:
        """构建汇总者 prompt，支持三种模式"""
        # 获取模式配置
        try:
            discussion_mode = DiscussionMode(mode)
        except ValueError:
            discussion_mode = DiscussionMode.CODE_DOCUMENT

        mode_config = MODE_TEMPLATES[discussion_mode]

        prompt = f"""你是文档专家。请根据以下讨论记录，生成一份{mode_config['output_format']}。

## 讨论记录
{full_discussion}

## 产出要求
请按以下结构生成文档：

# {goal}

{mode_config['synthesizer_chapters']}

要求：
- 内容必须来自讨论记录，不要编造
- 引用关键决策时标注是哪位专家提出的
- 结论要清晰、可执行
- 产出格式：{mode_config['output_format']}"""

        return prompt

    def _build_role_definition(self, role: Dict[str, Any], current_round: int) -> str:
        if current_round <= FULL_ROLE_ROUNDS:
            expertise = ", ".join(role.get("expertise", []))
            responsibilities = "\n".join(f"- {r}" for r in role.get("responsibilities", []))
            constraints = "\n".join(f"- {c}" for c in role.get("constraints", []))
            return f"""你是{role['name']}，一位{role.get('description', '专家')}。

## 专业能力
{expertise}

## 职责
{responsibilities}

## 约束
{constraints if constraints else "无特殊约束"}"""
        else:
            constraints = role.get("constraints", [])
            constraint_text = constraints[0] if constraints else ""
            return f"""你是{role['name']}。{role.get('description', '专家')}
{f'核心约束：{constraint_text}' if constraint_text else ''}"""

    def _build_round_context(self, current_round: int, total_rounds: int) -> str:
        context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
        if current_round >= total_rounds - 1:
            context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"
        elif current_round == 1:
            context += "\n这是第一轮讨论，请从你的专业角度给出初步观点。"
        return context

    def _build_messages_context(self, messages: Optional[List[Dict[str, Any]]]) -> str:
        if not messages:
            return ""
        parts = ["## 最近讨论"]
        for msg in messages[-6:]:
            sender = msg.get("sender_id", msg.get("sender_type", "未知"))
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            parts.append(f"[{sender}]: {content}")
        return "\n".join(parts)

    def _build_decisions_context(self, decisions: Optional[List[str]]) -> str:
        if not decisions:
            return ""
        parts = ["## 已达成共识"]
        for d in decisions:
            parts.append(f"- {d}")
        return "\n".join(parts)

    def _apply_degradation(self, prompt: str, estimated_tokens: int) -> str:
        action = get_degradation_action(estimated_tokens, self.budget)
        if action:
            logger.info("Applying degradation", action=action[0], description=action[1])
            max_chars = self.budget.total * int(self.chars_per_token)
            if len(prompt) > max_chars:
                prompt = prompt[:max_chars] + "\n\n...(内容已截断以符合Token预算)"
        return prompt

    def _build_file_contents_with_budget(
        self, shared_sources: List[Dict[str, Any]], max_chars: int
    ) -> str:
        if not shared_sources:
            return ""

        sections = []
        total_chars = 0

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

    def _build_file_contents(self, shared_sources: List[Dict[str, Any]]) -> str:
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

    def truncate_content(self, content: str, max_tokens: Optional[int] = None) -> str:
        max_chars = (max_tokens or self.max_file_tokens) * self.chars_per_token

        if len(content) <= max_chars:
            return content

        return content[:max_chars] + "...(内容已截断)"

    def build_rolling_summary(
        self,
        existing_summary: str,
        new_messages: List[Dict[str, Any]],
    ) -> str:
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
            combined = combined[-max_chars:]

        return combined


context_builder = ContextBuilder()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/context_builder.py
git commit -m "feat(backend): add three-mode support to context builder"
```

---

### Task 3: 扩展 ArtifactWriter 支持三种模式

**Files:**
- Modify: `backend/app/services/artifact_writer.py`

- [ ] **Step 1: 添加模式支持**

```python
# backend/app/services/artifact_writer.py
"""Artifact writer service for generating structured outputs in multiple formats."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.utils.formatters import build_discussion_markdown, build_summary, get_sender_label
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactFormat(str, Enum):
    """产出格式枚举"""
    MARKDOWN = "markdown"
    TEXT = "text"
    CODE = "code"


# 模式到格式的映射
MODE_FORMAT_MAP = {
    "code_document": ArtifactFormat.MARKDOWN,
    "document": ArtifactFormat.TEXT,
    "code": ArtifactFormat.CODE,
}


class ArtifactWriterError(Exception):
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
        mode: str = "code_document",
        participants: Optional[List[str]] = None,
        source_count: int = 0,
        model_name: str = "unknown",
    ) -> Artifact:
        """生成产出文件，支持三种模式"""
        if not messages:
            raise ValueError("No messages provided for artifact generation")

        # 获取产出格式
        artifact_format = MODE_FORMAT_MAP.get(mode, ArtifactFormat.MARKDOWN)

        discussion_text = self._build_discussion_text(messages)

        # 根据模式生成内容
        if artifact_format == ArtifactFormat.MARKDOWN:
            content = self._generate_markdown(goal, discussion_text)
            file_extension = ".md"
            file_name = "final-plan.md"
        elif artifact_format == ArtifactFormat.TEXT:
            content = self._generate_text(goal, discussion_text)
            file_extension = ".txt"
            file_name = "final-report.txt"
        else:  # CODE
            content = self._generate_code(goal, discussion_text)
            file_extension = ".md"
            file_name = "code-draft.md"

        round_count = max(m.get("round", 0) for m in messages)
        header = self._build_source_annotation(
            room_name, participants or [], source_count, model_name, round_count, mode
        )

        final_content = header + content

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        artifact_dir = os.path.join(output_directory, f"artifact_{timestamp}")

        try:
            os.makedirs(artifact_dir, exist_ok=True)
            file_path = os.path.join(artifact_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_content)

            log_path = os.path.join(artifact_dir, "discussion-log.md")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(discussion_text)
        except OSError as e:
            logger.error("Failed to write artifact file", artifact_dir=artifact_dir, error=str(e))
            raise ArtifactWriterError(f"Failed to write artifact to {artifact_dir}: {e}") from e

        summary = self._build_summary(messages)

        artifact = Artifact(
            id=str(uuid.uuid4()),
            room_id=room_id,
            artifact_type=artifact_format.value,
            title=room_name,
            file_path=file_path,
            summary=summary,
        )

        self.session.add(artifact)
        await self.session.flush()

        logger.info("Generated artifact", artifact_id=artifact.id, room_id=room_id, file_path=file_path, mode=mode)
        return artifact

    def _generate_markdown(self, goal: str, discussion: str) -> str:
        """生成代码文档模式的 Markdown 产出"""
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
系统模块划分和设计。

## 6. 数据结构 / 接口设计
API接口和数据结构设计。

## 7. 实施步骤
详细的实施步骤和时间线。

## 8. 测试与验收标准
测试方案和验收标准。

## 9. 风险与取舍
技术风险分析和权衡取舍。

## 10. 后续迭代建议
后续版本的改进建议。"""

    def _generate_text(self, goal: str, discussion: str) -> str:
        """生成纯文档模式的文本产出"""
        return f"""{goal}
{'='*60}

执行摘要
--------
基于专家讨论的核心结论和建议。

背景与目标
----------
讨论的背景和要达成的目标。

现状分析
--------
对当前情况的分析和理解。

核心发现
--------
讨论中的关键发现和洞察。

结论与建议
----------
最终结论和可执行的建议。

数据来源说明
----------
讨论中引用的数据和资料来源。

附录
----
补充信息和参考资料。"""

    def _generate_code(self, goal: str, discussion: str) -> str:
        """生成代码模式的代码草案产出"""
        return f"""# {goal}

## 实现概述
核心功能的实现思路和架构设计。

## 核心代码

```python
# 核心功能实现示例
# 请根据讨论结果填充具体代码

def main():
    """
    主函数 - 核心逻辑实现
    基于专家讨论的方案
    """
    pass

if __name__ == "__main__":
    main()
```

## 使用示例
```bash
# 安装依赖
pip install -r requirements.txt

# 运行示例
python main.py
```

## 依赖说明
- Python 3.8+
- 其他依赖项

## 集成方式
如何将此代码集成到现有项目中。

## 注意事项
- 使用前请先阅读说明
- 注意配置参数

## 测试建议
建议的测试方案和测试用例。"""

    def _build_source_annotation(
        self, room_name: str, participants: List[str], source_count: int, 
        model_name: str, round_count: int, mode: str = "code_document"
    ) -> str:
        participant_str = "、".join(participants) if participants else "未知"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        mode_names = {
            "code_document": "代码文档模式",
            "document": "纯文档模式",
            "code": "代码模式",
        }
        mode_name = mode_names.get(mode, mode)

        return f"""> 📋 本方案由专家团通过 {round_count} 轮多专家讨论自动生成。
> 讨论模式：{mode_name}
> 参与专家：{participant_str}
> 共享资料：{source_count} 个文件
> 所用模型：{model_name}
> 生成时间：{now}

---

"""

    def _build_discussion_text(self, messages: List[Dict[str, Any]]) -> str:
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

    def _build_markdown_content(self, room_name: str, goal: str, messages: List[Dict[str, Any]]) -> str:
        return build_discussion_markdown(room_name=room_name, goal=goal, messages=messages, include_summary=False)

    def _get_sender_label(self, sender_type: str, sender_id: Optional[str]) -> str:
        return get_sender_label(sender_type, sender_id)

    def _build_summary(self, messages: List[Dict[str, Any]]) -> str:
        return build_summary(messages)


def create_artifact_writer(session: AsyncSession) -> ArtifactWriter:
    return ArtifactWriter(session=session)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/artifact_writer.py
git commit -m "feat(backend): add three-mode support to artifact writer"
```

---

### Task 4: 更新 Orchestrator 传递模式参数

**Files:**
- Modify: `backend/app/services/orchestrator.py`

- [ ] **Step 1: 添加模式参数支持**

```python
# 在 Orchestrator.__init__ 中添加 mode 属性
class Orchestrator:
    def __init__(
        self,
        session: AsyncSession,
        room: Any,
        on_event: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
    ):
        # ... 现有代码 ...
        self.mode = room.mode if hasattr(room, 'mode') else "code_document"
        # ... 现有代码 ...

    # 修改 _run_orchestrator_turn 方法
    async def _run_orchestrator_turn(self) -> Optional[str]:
        # ... 现有代码 ...
        prompt = context_builder.build_orchestrator_prompt(
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            experts=[{"name": p["name"]} for p in self.participants],
            mode=self.mode,  # 添加 mode 参数
        )
        # ... 现有代码 ...

    # 修改 _run_expert_turn 方法
    async def _run_expert_turn(self, participant: Dict[str, Any], length_warning: bool = False) -> None:
        # ... 现有代码 ...
        prompt = context_builder.build_expert_prompt(
            role=role_data,
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            mode=self.mode,  # 添加 mode 参数
            additional_context=additional_context,
        )
        # ... 现有代码 ...
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/orchestrator.py
git commit -m "feat(backend): pass mode parameter in orchestrator"
```

---

### Task 5: 更新前端讨论页显示模式信息

**Files:**
- Modify: `frontend/src/pages/DiscussionPage.tsx`

- [ ] **Step 1: 添加模式显示**

```tsx
// frontend/src/pages/DiscussionPage.tsx
// 在 roomData 接口中添加 mode 字段
interface RoomData {
  name: string;
  goal: string;
  round_limit: number;
  mode: string;  // 添加 mode 字段
}

// 在组件中添加模式标签映射
const modeLabels: Record<string, { label: string; color: string }> = {
  code_document: { label: '代码文档', color: 'bg-blue-100 text-blue-700' },
  document: { label: '纯文档', color: 'bg-green-100 text-green-700' },
  code: { label: '代码', color: 'bg-purple-100 text-purple-700' },
};

// 在 header 区域添加模式显示
<div className="flex items-center gap-3">
  {roomData?.mode && (
    <span className={`text-xs px-2 py-1 rounded-full ${modeLabels[roomData.mode]?.color || 'bg-gray-100 text-gray-700'}`}>
      {modeLabels[roomData.mode]?.label || roomData.mode}
    </span>
  )}
  {/* ... 现有代码 ... */}
</div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DiscussionPage.tsx
git commit -m "feat(frontend): display discussion mode in discussion page"
```

---

### Task 6: 更新 ArtifactRouter 传递模式参数

**Files:**
- Modify: `backend/app/routers/artifacts.py`

- [ ] **Step 1: 修改 synthesize 端点**

```python
# backend/app/routers/artifacts.py
# 在 synthesize 端点中获取 room.mode 并传递给 artifact_writer

@router.post("/api/rooms/{room_id}/synthesize", response_model=ArtifactResponse)
async def synthesize(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> ArtifactResponse:
    """Generate artifact from discussion."""
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = await message_service.get_by_room(session, room_id)
    if not messages:
        raise HTTPException(status_code=400, detail="No messages found for this room")

    messages_data = [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "sender_id": m.sender_id,
            "content": m.content,
            "round": m.round,
        }
        for m in messages
    ]

    participants = [p.role_card.name for p in room.participants if p.role_card]

    writer = create_artifact_writer(session)
    artifact = await writer.generate_artifact(
        room_id=room_id,
        room_name=room.name,
        goal=room.goal,
        messages=messages_data,
        output_directory=room.output_directory,
        mode=room.mode,  # 传递 mode 参数
        participants=participants,
        source_count=len(room.shared_sources) if room.shared_sources else 0,
    )

    return ArtifactResponse.model_validate(artifact)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/artifacts.py
git commit -m "feat(backend): pass mode parameter in artifact generation"
```

---

## 四、验证方式

### 验证路由修复
```bash
# 启动前端
cd frontend && npm run dev

# 访问 http://localhost:5173/rooms/{id}
# 应该自动重定向到讨论页，而不是显示"此页面正在开发中..."
```

### 验证三种模式
```bash
# 创建不同模式的讨论室
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name":"代码文档测试","goal":"设计登录模块","mode":"code_document",...}'

curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name":"纯文档测试","goal":"生成调研报告","mode":"document",...}'

curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name":"代码测试","goal":"实现排序算法","mode":"code",...}'

# 启动讨论并验证 prompt 中包含正确的模式信息
# 验证产出文件格式正确
```

### 验证产出格式
```bash
# 代码文档模式 → final-plan.md (Markdown)
# 纯文档模式 → final-report.txt (文本)
# 代码模式 → code-draft.md (Markdown 代码草案)
```

---

## 五、Git 操作

完成所有任务后：
```bash
git add .
git commit -m "feat: implement three-mode discussion feature

- Fix room detail page routing to discussion page
- Add code_document, document, code mode support
- ContextBuilder: mode-specific prompt templates
- ArtifactWriter: mode-specific output formats
- Orchestrator: pass mode parameter
- DiscussionPage: display current mode

Closes #XXX"

git push origin feature/three-mode-discussion
```
