"""Artifact writer service for generating structured Markdown outputs."""

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
        if not messages:
            raise ValueError("No messages provided for artifact generation")

        discussion_text = self._build_discussion_text(messages)
        part1_content = self._generate_part1(goal, discussion_text)
        part1_summary = self._extract_part1_summary(part1_content)
        part2_content = self._generate_part2(goal, discussion_text, part1_summary)

        round_count = max(m.get("round", 0) for m in messages)
        header = self._build_source_annotation(
            room_name, participants or [], source_count, model_name, round_count
        )

        markdown_content = header + part1_content + "\n\n" + part2_content

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        artifact_dir = os.path.join(output_directory, f"artifact_{timestamp}")

        try:
            os.makedirs(artifact_dir, exist_ok=True)
            file_path = os.path.join(artifact_dir, "final-plan.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

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
            artifact_type="markdown",
            title=room_name,
            file_path=file_path,
            summary=summary,
        )

        self.session.add(artifact)
        await self.session.flush()

        logger.info("Generated artifact", artifact_id=artifact.id, room_id=room_id, file_path=file_path)
        return artifact

    def _generate_part1(self, goal: str, discussion: str) -> str:
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

    def _generate_part2(self, goal: str, discussion: str, part1_summary: str) -> str:
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
        lines = part1_content.split('\n')
        summary_parts = []
        for line in lines:
            if line.startswith('#'):
                summary_parts.append(line)
            elif line.strip() and summary_parts and not summary_parts[-1].startswith('#'):
                continue
            elif line.strip() and summary_parts:
                summary_parts.append(line[:100])
        return '\n'.join(summary_parts[:20])

    def _build_source_annotation(
        self, room_name: str, participants: List[str], source_count: int, model_name: str, round_count: int
    ) -> str:
        participant_str = "、".join(participants) if participants else "未知"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        return f"""> 📋 本方案由专家团通过 {round_count} 轮多专家讨论自动生成。
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
