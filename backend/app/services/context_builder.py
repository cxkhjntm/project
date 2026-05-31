"""Context builder for discussion prompts with token budget management."""

from typing import Any, Dict, List, Optional

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
        additional_context: Optional[str] = None,
    ) -> str:
        role_def = self._build_role_definition(role, current_round)
        file_contents = self._build_file_contents_with_budget(
            shared_sources, int(self.budget.shared_data * self.chars_per_token)
        )

        round_context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
        if current_round >= total_rounds - 1:
            round_context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"

        prompt = f"""{role_def}

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
    ) -> str:
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

    def _build_role_definition(self, role: Dict[str, Any], current_round: int) -> str:
        if current_round <= FULL_ROLE_ROUNDS:
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
            constraints = role.get("constraints", [])
            constraint_text = constraints[0] if constraints else ""

            return f"""你是{role['name']}。{role.get('description', '专家')}
{f'核心约束：{constraint_text}' if constraint_text else ''}"""

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
