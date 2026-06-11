"""Context builder for discussion prompts with token budget management."""

from enum import StrEnum
from typing import Any

from app.utils.logger import get_logger
from app.utils.token_counter import (
    TOKEN_ESTIMATES,
    TokenBudget,
    check_budget,
    estimate_tokens,
    get_degradation_action,
)

logger = get_logger(__name__)

# Role definition compression threshold
FULL_ROLE_ROUNDS = 2


class DiscussionMode(StrEnum):
    """讨论模式枚举"""

    CODE_DOCUMENT = "code_document"
    DOCUMENT = "document"
    CODE = "code"


MODE_TEMPLATES: dict[DiscussionMode, dict[str, str]] = {
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


def _parse_mode(mode: str) -> DiscussionMode:
    """Parse mode string to DiscussionMode enum, fallback to CODE_DOCUMENT."""
    try:
        return DiscussionMode(mode)
    except ValueError:
        logger.warning("Invalid discussion mode '%s', falling back to code_document", mode)
        return DiscussionMode.CODE_DOCUMENT


class ContextBuilder:
    """Builds context for LLM prompts with token budget management."""

    def __init__(
        self,
        max_file_tokens: int = 4000,
        max_summary_tokens: int = 1000,
        budget: TokenBudget | None = None,
    ):
        self.max_file_tokens = max_file_tokens
        self.max_summary_tokens = max_summary_tokens
        self.chars_per_token = TOKEN_ESTIMATES["english_chars_per_token"]
        self.budget = budget or TokenBudget()

    def build_expert_prompt(
        self,
        role: dict[str, Any],
        goal: str,
        shared_sources: list[dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        mode: str = "code_document",
        additional_context: str | None = None,
    ) -> str:
        mode_enum = _parse_mode(mode)
        mode_config = MODE_TEMPLATES[mode_enum]

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
工作模式：{mode_config["name"]}
{round_context}

## 共享资料
{file_contents if file_contents else "无共享资料"}

## 已有讨论
{rolling_summary if rolling_summary else "这是讨论的开始，还没有已有讨论。"}

## 本轮要求
{mode_config["expert_instruction"].strip()}"""

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
        shared_sources: list[dict[str, Any]],
        rolling_summary: str,
        current_round: int,
        total_rounds: int,
        experts: list[dict[str, Any]],
        mode: str = "code_document",
    ) -> str:
        mode_enum = _parse_mode(mode)
        mode_config = MODE_TEMPLATES[mode_enum]

        expert_names = ", ".join(e["name"] for e in experts)
        file_contents = self._build_file_contents(shared_sources)

        is_near_end = current_round >= total_rounds - 1

        convergence_section = """
## 收敛判断标准
当以下条件满足时，判断讨论已收敛：
- 专家们的观点已经达成一致，没有重大分歧
- 没有新的信息或观点出现
- 讨论已经充分，可以得出结论
- 关键决策已经确认"""

        if is_near_end:
            convergence_section += """
注意：当前已是最后几轮，请优先评估是否满足收敛条件。"""

        prompt = f"""你是专家群聊主持人。你的任务是控制讨论流程，而不是替专家完成全部内容。

本次任务目标：{goal}
当前工作模式：{mode_config["name"]}（{mode_config["description"]}）
当前轮次：第 {current_round}/{total_rounds} 轮
参与专家：{expert_names}

共享资料摘要：
{file_contents if file_contents else "无共享资料"}

已有讨论摘要：
{rolling_summary if rolling_summary else "这是讨论的开始。"}
{convergence_section}

## 输出格式要求
你的回复必须以 ACTION 指令结尾，格式如下：
- `ACTION: focus:<专家名称1,专家名称2>` — 指定本轮必须重点回应的专家；所有专家仍会参与发言
- `ACTION: converge` — 讨论已收敛，可以结束
- `ACTION: synthesize` — 开始生成产出物

调度约束：
- 不允许只让单个专家独占本轮讨论
- 如果某些问题必须由特定专家重点回应，使用 `focus`
- 如果希望所有专家按正常顺序发言，仍然使用 `ACTION: focus:` 或省略专家名称

请用简洁的主持词引导讨论（不超过 200 字），并在末尾输出 ACTION 指令。"""

        return prompt

    def build_synthesizer_prompt(
        self,
        goal: str,
        full_discussion: str,
        mode: str = "code_document",
    ) -> str:
        mode_enum = _parse_mode(mode)
        mode_config = MODE_TEMPLATES[mode_enum]

        prompt = f"""你是文档专家。请根据以下讨论记录，生成一份{mode_config["output_format"]}。

## 讨论记录
{full_discussion}

## 产出要求
请按以下结构生成文档：

# {goal}
{mode_config["synthesizer_chapters"]}

要求：
- 内容必须来自讨论记录，不要编造
- 引用关键决策时标注是哪位专家提出的
- 结论要清晰、可执行
- 使用 Markdown 格式"""

        return prompt

    def _build_role_definition(self, role: dict[str, Any], current_round: int) -> str:
        if current_round <= FULL_ROLE_ROUNDS:
            expertise = ", ".join(role.get("expertise", []))
            responsibilities = "\n".join(f"- {r}" for r in role.get("responsibilities", []))
            constraints = "\n".join(f"- {c}" for c in role.get("constraints", []))
            return f"""你是{role["name"]}，一位{role.get("description", "专家")}。

## 专业能力
{expertise}

## 职责
{responsibilities}

## 约束
{constraints if constraints else "无特殊约束"}"""
        else:
            constraints = role.get("constraints", [])
            constraint_text = constraints[0] if constraints else ""
            return f"""你是{role["name"]}。{role.get("description", "专家")}
{f"核心约束：{constraint_text}" if constraint_text else ""}"""

    def _build_round_context(self, current_round: int, total_rounds: int) -> str:
        context = f"当前是第 {current_round}/{total_rounds} 轮讨论。"
        if current_round >= total_rounds - 1:
            context += "\n注意：这是最后几轮讨论，请开始收敛观点，准备总结。"
        elif current_round == 1:
            context += "\n这是第一轮讨论，请从你的专业角度给出初步观点。"
        return context

    def _build_messages_context(self, messages: list[dict[str, Any]] | None) -> str:
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

    def _build_decisions_context(self, decisions: list[str] | None) -> str:
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

    def _build_role_definition(self, role: dict[str, Any], current_round: int) -> str:
        if current_round <= FULL_ROLE_ROUNDS:
            expertise = ", ".join(role.get("expertise", []))
            responsibilities = "\n".join(f"- {r}" for r in role.get("responsibilities", []))
            constraints = "\n".join(f"- {c}" for c in role.get("constraints", []))

            return f"""你是{role["name"]}，一位{role.get("description", "专家")}。

## 专业能力
{expertise}

## 职责
{responsibilities}

## 约束
{constraints if constraints else "无特殊约束"}"""
        else:
            constraints = role.get("constraints", [])
            constraint_text = constraints[0] if constraints else ""

            return f"""你是{role["name"]}。{role.get("description", "专家")}
{f"核心约束：{constraint_text}" if constraint_text else ""}"""

    def _build_file_contents_with_budget(
        self, shared_sources: list[dict[str, Any]], max_chars: int
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

    def _build_file_contents(self, shared_sources: list[dict[str, Any]]) -> str:
        if not shared_sources:
            return ""

        sections = []
        total_chars = 0
        max_chars = int(self.max_file_tokens * self.chars_per_token)

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

    def _build_file_contents_with_budget(
        self, shared_sources: list[dict[str, Any]], max_chars: int
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

    def truncate_content(self, content: str, max_tokens: int | None = None) -> str:
        max_chars = int((max_tokens or self.max_file_tokens) * self.chars_per_token)

        if len(content) <= max_chars:
            return content

        return content[:max_chars] + "...(内容已截断)"

    def build_rolling_summary(
        self,
        existing_summary: str,
        new_messages: list[dict[str, Any]],
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
