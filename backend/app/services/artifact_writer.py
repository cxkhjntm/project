"""Artifact writer service for generating structured outputs in multiple formats."""

import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artifact import Artifact
from app.models.room import RoomParticipant
from app.utils.formatters import build_discussion_markdown, build_summary, get_sender_label
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactFormat(StrEnum):
    """产出格式枚举"""

    MARKDOWN = "markdown"
    TEXT = "text"
    CODE = "code"


MODE_FORMAT_MAP = {
    "code_document": ArtifactFormat.MARKDOWN,
    "document": ArtifactFormat.TEXT,
    "code": ArtifactFormat.CODE,
}

MODE_DISPLAY_NAMES = {
    ArtifactFormat.MARKDOWN: "代码文档模式",
    ArtifactFormat.TEXT: "纯文档模式",
    ArtifactFormat.CODE: "代码模式",
}

CONCLUSION_KEYWORDS = (
    "建议",
    "推荐",
    "结论",
    "认为",
    "应该",
    "优先",
    "采用",
    "选择",
    "方案",
    "recommend",
    "suggest",
    "should",
    "priority",
    "prioritize",
    "use",
    "adopt",
)

RISK_KEYWORDS = (
    "风险",
    "问题",
    "限制",
    "瓶颈",
    "成本",
    "依赖",
    "冲突",
    "安全",
    "失败",
    "不确定",
    "注意",
    "risk",
    "issue",
    "limitation",
    "concern",
    "cost",
    "dependency",
    "security",
    "failure",
    "trade-off",
    "tradeoff",
)

ACTION_KEYWORDS = (
    "下一步",
    "实施",
    "落地",
    "执行",
    "验证",
    "测试",
    "接入",
    "配置",
    "创建",
    "补充",
    "完善",
    "需要",
    "先",
    "todo",
    "action",
    "next",
    "implement",
    "validate",
    "test",
    "build",
    "create",
    "configure",
)


class ArtifactWriterError(Exception):
    pass


@dataclass
class ArtifactGenerationResult:
    final_artifact: Artifact
    discussion_log: Artifact
    fallback_used: bool
    content_preview: str | None = None

    @property
    def artifacts(self) -> list[Artifact]:
        return [self.final_artifact, self.discussion_log]

    def __getattr__(self, name: str) -> Any:
        return getattr(self.final_artifact, name)


class ArtifactWriter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_artifact(
        self,
        room_id: str,
        room_name: str,
        goal: str,
        messages: list[dict[str, Any]],
        output_directory: str,
        mode: str = "code_document",
        participants: list[str] | None = None,
        source_count: int = 0,
        model_name: str = "unknown",
        max_length: int | None = None,
    ) -> ArtifactGenerationResult:
        if not messages:
            raise ValueError("No messages provided for artifact generation")
        if not output_directory:
            raise ValueError("Output directory is required for artifact generation")

        artifact_format = MODE_FORMAT_MAP.get(mode, ArtifactFormat.MARKDOWN)
        discussion_text = self._build_discussion_text(messages)
        discussion_log_content = self._build_discussion_log_content(room_name, goal, messages)
        synthesis = self._synthesize_discussion(messages)

        round_count = max(m.get("round", 0) for m in messages)
        header = self._build_source_annotation(
            room_name, participants or [], source_count, model_name, round_count, artifact_format
        )

        fallback_used = False
        if artifact_format == ArtifactFormat.MARKDOWN:
            generated, fallback_used = await self._generate_markdown_final(
                room_id=room_id,
                goal=goal,
                discussion_text=discussion_text,
                synthesis=synthesis,
                mode=mode,
                max_length=max_length,
            )
            content = header + generated
            file_name = "final-plan.md"
            artifact_type = "markdown"
        elif artifact_format == ArtifactFormat.TEXT:
            generated, fallback_used = await self._generate_text_final(
                room_id=room_id,
                goal=goal,
                discussion_text=discussion_text,
                synthesis=synthesis,
                mode=mode,
                max_length=max_length,
            )
            content = header + generated
            file_name = "final-report.txt"
            artifact_type = "text"
        else:
            generated, fallback_used = await self._generate_code_final(
                room_id=room_id,
                goal=goal,
                discussion_text=discussion_text,
                synthesis=synthesis,
                mode=mode,
                max_length=max_length,
            )
            content = header + generated
            file_name = "code-draft.md"
            artifact_type = "markdown"

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        artifact_dir = os.path.join(
            output_directory, f"artifact_{timestamp}_{uuid.uuid4().hex[:8]}"
        )

        try:
            os.makedirs(artifact_dir, exist_ok=True)
            file_path = os.path.join(artifact_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            log_path = os.path.join(artifact_dir, "discussion-log.md")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(discussion_log_content)
        except OSError as e:
            logger.error("Failed to write artifact file", artifact_dir=artifact_dir, error=str(e))
            raise ArtifactWriterError(f"Failed to write artifact to {artifact_dir}: {e}") from e

        summary = self._build_summary(messages)
        if fallback_used:
            summary = f"{summary} | fallback=true"

        final_artifact = Artifact(
            id=str(uuid.uuid4()),
            room_id=room_id,
            artifact_type=artifact_type,
            artifact_kind="final",
            title=room_name,
            file_path=file_path,
            summary=summary,
        )
        discussion_log_artifact = Artifact(
            id=str(uuid.uuid4()),
            room_id=room_id,
            artifact_type="markdown",
            artifact_kind="discussion_log",
            title=f"{room_name} 讨论记录",
            file_path=log_path,
            summary=self._build_summary(messages),
        )

        self.session.add(final_artifact)
        self.session.add(discussion_log_artifact)
        await self.session.flush()

        logger.info(
            "Generated artifact",
            artifact_id=final_artifact.id,
            room_id=room_id,
            file_path=file_path,
            mode=mode,
            fallback_used=fallback_used,
        )
        return ArtifactGenerationResult(
            final_artifact=final_artifact,
            discussion_log=discussion_log_artifact,
            fallback_used=fallback_used,
            content_preview=content[:500],
        )

    async def _generate_markdown_final(
        self,
        room_id: str,
        goal: str,
        discussion_text: str,
        synthesis: dict[str, list[str]],
        mode: str,
        max_length: int | None,
    ) -> tuple[str, bool]:
        llm_content = await self._generate_llm_synthesis(
            room_id=room_id,
            goal=goal,
            discussion_text=discussion_text,
            mode=mode,
            max_length=max_length,
        )
        if llm_content:
            return llm_content, False

        part1_content = self._generate_part1(goal, discussion_text, synthesis)
        part1_summary = self._extract_part1_summary(part1_content)
        part2_content = self._generate_part2(goal, discussion_text, part1_summary, synthesis)
        return part1_content + "\n\n" + part2_content, True

    async def _generate_text_final(
        self,
        room_id: str,
        goal: str,
        discussion_text: str,
        synthesis: dict[str, list[str]],
        mode: str,
        max_length: int | None,
    ) -> tuple[str, bool]:
        llm_content = await self._generate_llm_synthesis(
            room_id=room_id,
            goal=goal,
            discussion_text=discussion_text,
            mode=mode,
            max_length=max_length,
        )
        if llm_content:
            return llm_content, False
        return self._generate_text(goal, discussion_text, synthesis), True

    async def _generate_code_final(
        self,
        room_id: str,
        goal: str,
        discussion_text: str,
        synthesis: dict[str, list[str]],
        mode: str,
        max_length: int | None,
    ) -> tuple[str, bool]:
        llm_content = await self._generate_llm_synthesis(
            room_id=room_id,
            goal=goal,
            discussion_text=discussion_text,
            mode=mode,
            max_length=max_length,
        )
        if llm_content:
            return llm_content, False
        return self._generate_code(goal, discussion_text, synthesis), True

    async def _generate_llm_synthesis(
        self,
        room_id: str,
        goal: str,
        discussion_text: str,
        mode: str,
        max_length: int | None,
    ) -> str | None:
        client = await self._build_synthesis_client(room_id)
        if client is None:
            return None

        from app.services.context_builder import context_builder
        from app.services.model_client import ModelClientError

        prompt = context_builder.build_synthesizer_prompt(
            goal=goal,
            full_discussion=discussion_text,
            mode=mode,
        )
        prompt += """

额外要求：
- 生成的是最终产物，不是讨论记录
- 不要逐轮照抄对话原文
- 只保留关键结论、实施步骤、风险、验收标准和必要引用
- 完整逐轮记录会单独保存到 discussion-log.md，不要在本文重复附录
"""

        try:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
        except ModelClientError as e:
            logger.warning("LLM synthesis failed, falling back to deterministic writer", error=str(e))
            return None
        except Exception as e:
            logger.warning("Unexpected synthesis failure, falling back", error=str(e))
            return None

        content = response.content.strip()
        if not content:
            logger.warning("LLM synthesis returned empty content, falling back")
            return None
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip() + "\n\n...(内容已按最大长度截断)"
        return content

    async def _build_synthesis_client(self, room_id: str):
        result = await self.session.execute(
            select(RoomParticipant)
            .where(RoomParticipant.room_id == room_id)
            .options(selectinload(RoomParticipant.provider))
        )
        participant = result.scalars().first()
        if not participant or not participant.provider:
            logger.warning("No provider available for LLM synthesis", room_id=room_id)
            return None

        from app.services.crypto import crypto_service
        from app.services.model_client import create_model_client

        provider = participant.provider
        try:
            api_key = crypto_service.decrypt(provider.api_key_encrypted)
        except Exception as e:
            logger.warning("Could not decrypt synthesis provider key", room_id=room_id, error=str(e))
            return None

        return create_model_client(
            base_url=provider.base_url,
            api_key=api_key,
            model=participant.model_override or provider.default_model,
            temperature=provider.default_temperature,
            max_tokens=provider.default_max_output_tokens,
        )

    def _generate_part1(
        self,
        goal: str,
        discussion: str,
        synthesis: dict[str, list[str]],
    ) -> str:
        observations = self._format_bullets(
            synthesis["observations"], "讨论记录中暂无可抽取的资料理解。"
        )
        requirements = self._format_bullets(
            synthesis["requirements"],
            "讨论记录中暂无明确需求拆解，建议在下一轮补充边界、输入输出和验收条件。",
        )
        conclusions = self._format_bullets(synthesis["conclusions"], "讨论记录中暂无明确总体方案。")
        implementation = self._format_bullets(
            synthesis["implementation"],
            "讨论记录中暂无明确模块设计，建议按核心流程、数据模型、接口和持久化拆分。",
        )

        return f"""# {goal}

## 1. 背景与目标
本产出基于专家讨论记录自动整理，目标是形成可执行、可复核的方案文档。

目标：{goal}

## 2. 当前资料理解
{observations}

## 3. 需求拆解
{requirements}

## 4. 总体方案
{conclusions}

## 5. 模块设计
{implementation}"""

    def _generate_part2(
        self,
        goal: str,
        discussion: str,
        part1_summary: str,
        synthesis: dict[str, list[str]],
    ) -> str:
        interfaces = self._format_bullets(
            synthesis["interfaces"], "讨论记录中暂无明确接口或数据结构设计。"
        )
        actions = self._format_numbered(
            synthesis["actions"], "1. 将核心结论转化为任务清单，并补齐负责人、顺序和验收标准。"
        )
        tests = self._format_bullets(
            synthesis["tests"],
            "讨论记录中暂无明确测试项，建议至少覆盖核心流程、异常输入、权限/路径安全和产出文件验证。",
        )
        risks = self._format_bullets(synthesis["risks"], "讨论记录中暂无明确风险项。")
        next_steps = self._format_bullets(
            synthesis["next_steps"], "讨论记录中暂无明确后续迭代建议。"
        )

        return f"""## 6. 数据结构 / 接口设计
{interfaces}

## 7. 实施步骤
{actions}

## 8. 测试与验收标准
{tests}

## 9. 风险与取舍
{risks}

## 10. 后续迭代建议
{next_steps}"""

    def _generate_text(
        self,
        goal: str,
        discussion: str,
        synthesis: dict[str, list[str]],
    ) -> str:
        return f"""{goal}
{"=" * 60}

执行摘要
--------
{self._format_plain_lines(synthesis["conclusions"], "讨论记录中暂无明确结论。")}

背景与目标
----------
{goal}

现状分析
--------
{self._format_plain_lines(synthesis["observations"], "讨论记录中暂无明确现状分析。")}

核心发现
--------
{self._format_plain_lines(synthesis["requirements"], "讨论记录中暂无明确核心发现。")}

结论与建议
----------
{self._format_plain_lines(synthesis["actions"], "讨论记录中暂无明确行动建议。")}

数据来源说明
----------
本报告根据讨论消息自动整理，完整逐轮内容见同目录 discussion-log.md。

附录
----
风险与注意事项：
{self._format_plain_lines(synthesis["risks"], "讨论记录中暂无明确风险项。")}"""

    def _generate_code(
        self,
        goal: str,
        discussion: str,
        synthesis: dict[str, list[str]],
    ) -> str:
        todo_lines = synthesis["actions"] or synthesis["implementation"] or synthesis["conclusions"]
        todo_block = (
            "\n".join(f"- {item}" for item in todo_lines[:8]) or "- 根据讨论结论补充核心实现任务。"
        )
        return f"""# {goal}

## 实现概述
{self._format_bullets(synthesis["conclusions"], "讨论记录中暂无明确实现结论。")}

## 核心任务草案
{self._format_bullets(todo_lines, "根据讨论结论补充核心实现任务。")}

## 伪代码骨架

```python
# Generated implementation notes from expert discussion.
TODO_ITEMS = \"\"\"
{todo_block}
\"\"\"

def main():
    \"\"\"Wire the agreed implementation tasks into concrete modules.\"\"\"
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
{self._format_bullets(synthesis["interfaces"], "讨论记录中暂无明确依赖或接口说明。")}

## 集成方式
{self._format_bullets(synthesis["implementation"], "讨论记录中暂无明确集成方式。")}

## 注意事项
{self._format_bullets(synthesis["risks"], "讨论记录中暂无明确注意事项。")}

## 测试建议
{self._format_bullets(synthesis["tests"], "讨论记录中暂无明确测试建议。")}"""

    def _synthesize_discussion(self, messages: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Extract deterministic synthesis points from discussion messages."""
        all_items: list[str] = []
        expert_items: list[str] = []

        for msg in messages:
            sender_type = msg.get("sender_type", "unknown")
            sender_id = msg.get("sender_id")
            sender_label = get_sender_label(sender_type, sender_id)
            for item in self._extract_message_items(str(msg.get("content", ""))):
                labeled_item = f"{sender_label}: {item}"
                all_items.append(labeled_item)
                if sender_type == "expert":
                    expert_items.append(labeled_item)

        primary_items = expert_items or all_items
        conclusions = self._select_items(primary_items, CONCLUSION_KEYWORDS, limit=6)
        if not conclusions:
            conclusions = self._fallback_items(primary_items, limit=4)

        requirements = self._select_items(
            primary_items,
            ("需求", "目标", "范围", "边界", "功能", "MVP", "requirement", "scope", "goal"),
            limit=5,
        )
        implementation = self._select_items(
            primary_items,
            (
                "实现",
                "架构",
                "模块",
                "流程",
                "数据库",
                "接口",
                "集成",
                "服务",
                "状态",
                "implementation",
                "architecture",
                "module",
                "database",
                "service",
                "workflow",
            ),
            limit=6,
        )
        interfaces = self._select_items(
            primary_items,
            (
                "接口",
                "API",
                "数据",
                "表",
                "模型",
                "schema",
                "REST",
                "FastAPI",
                "SQLAlchemy",
                "database",
                "endpoint",
                "contract",
            ),
            limit=5,
        )
        risks = self._select_items(primary_items, RISK_KEYWORDS, limit=5)
        actions = self._select_items(primary_items, ACTION_KEYWORDS, limit=6)
        tests = self._select_items(
            primary_items,
            ("测试", "验收", "验证", "覆盖", "用例", "test", "validate", "acceptance", "coverage"),
            limit=5,
        )
        next_steps = self._select_items(
            primary_items,
            ("后续", "迭代", "下一步", "补充", "完善", "phase", "next", "follow-up", "future"),
            limit=5,
        )

        return {
            "observations": self._fallback_items(primary_items, limit=4),
            "requirements": requirements,
            "conclusions": conclusions,
            "implementation": implementation,
            "interfaces": interfaces,
            "risks": risks,
            "actions": actions,
            "tests": tests,
            "next_steps": next_steps,
        }

    def _extract_message_items(self, content: str) -> list[str]:
        items: list[str] = []
        in_code_block = False
        for raw_line in content.replace("\r\n", "\n").split("\n"):
            line = raw_line.strip()
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            line = self._clean_item(line)
            if not line:
                continue

            for part in re.split(r"(?<=[。！？!?；;])\s*|(?<=[.!?])\s+", line):
                item = self._clean_item(part)
                if 8 <= len(item) <= 240:
                    items.append(item[:180])

        return self._dedupe(items)

    def _clean_item(self, text: str) -> str:
        text = re.sub(r"ACTION:\s*\S+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"LENGTH_WARNING:\s*\w+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^#{1,6}\s*", "", text)
        text = re.sub(r"^[-*+]\s+", "", text)
        text = re.sub(r"^\d+[.)、]\s*", "", text)
        text = text.replace("**", "").replace("__", "").replace("`", "")
        return re.sub(r"\s+", " ", text).strip(" -:：\t")

    def _select_items(
        self,
        items: list[str],
        keywords: tuple[str, ...],
        limit: int,
    ) -> list[str]:
        selected = []
        lowered_keywords = tuple(k.lower() for k in keywords)
        for item in items:
            searchable = item.lower()
            if any(keyword in searchable for keyword in lowered_keywords):
                selected.append(item)
        return self._dedupe(selected)[:limit]

    def _fallback_items(self, items: list[str], limit: int) -> list[str]:
        return self._dedupe(items)[:limit]

    def _dedupe(self, items: list[str]) -> list[str]:
        seen = set()
        unique_items = []
        for item in items:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)
        return unique_items

    def _format_bullets(self, items: list[str], empty_text: str) -> str:
        if not items:
            return f"- {empty_text}"
        return "\n".join(f"- {item}" for item in items)

    def _format_numbered(self, items: list[str], empty_text: str) -> str:
        if not items:
            return empty_text
        return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))

    def _format_plain_lines(self, items: list[str], empty_text: str) -> str:
        if not items:
            return empty_text
        return "\n".join(f"- {item}" for item in items)

    def _extract_part1_summary(self, part1_content: str) -> str:
        lines = part1_content.split("\n")
        summary_parts = []
        for line in lines:
            if line.startswith("#"):
                summary_parts.append(line)
            elif line.strip() and summary_parts and not summary_parts[-1].startswith("#"):
                continue
            elif line.strip() and summary_parts:
                summary_parts.append(line[:100])
        return "\n".join(summary_parts[:20])

    def _build_source_annotation(
        self,
        room_name: str,
        participants: list[str],
        source_count: int,
        model_name: str,
        round_count: int,
        artifact_format: ArtifactFormat = ArtifactFormat.MARKDOWN,
    ) -> str:
        participant_str = "、".join(participants) if participants else "未知"
        mode_name = MODE_DISPLAY_NAMES.get(artifact_format, "未知模式")
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        return f"""> 📋 本方案由专家团通过 {round_count} 轮多专家讨论自动生成。
> 讨论室：{room_name}
> 讨论模式：{mode_name}
> 参与专家：{participant_str}
> 共享资料：{source_count} 个文件
> 所用模型：{model_name}
> 生成时间：{now}

---

"""

    def _build_discussion_text(self, messages: list[dict[str, Any]]) -> str:
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

    def _build_markdown_content(
        self, room_name: str, goal: str, messages: list[dict[str, Any]]
    ) -> str:
        return build_discussion_markdown(
            room_name=room_name, goal=goal, messages=messages, include_summary=False
        )

    def _build_discussion_log_content(
        self, room_name: str, goal: str, messages: list[dict[str, Any]]
    ) -> str:
        return build_discussion_markdown(
            room_name=room_name, goal=goal, messages=messages, include_summary=True
        )

    def _get_sender_label(self, sender_type: str, sender_id: str | None) -> str:
        return get_sender_label(sender_type, sender_id)

    def _build_summary(self, messages: list[dict[str, Any]]) -> str:
        return build_summary(messages)


def create_artifact_writer(session: AsyncSession) -> ArtifactWriter:
    return ArtifactWriter(session=session)
