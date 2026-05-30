"""Discussion log generator service for producing formatted discussion logs."""

import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscussionLogError(Exception):
    """Exception raised for discussion log errors."""
    pass


class DiscussionLogGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_log(
        self,
        room_id: str,
        room_name: str,
        goal: str,
        messages: List[Dict[str, Any]],
        output_directory: str,
    ) -> Artifact:
        if not messages:
            raise ValueError("No messages provided for discussion log generation")

        log_content = self._build_log_content(
            room_name=room_name,
            goal=goal,
            messages=messages,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(output_directory, f"discussion_log_{timestamp}")

        try:
            os.makedirs(log_dir, exist_ok=True)
            file_path = os.path.join(log_dir, "discussion-log.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(log_content)
        except OSError as e:
            logger.error(
                "Failed to write discussion log file",
                log_dir=log_dir,
                error=str(e),
            )
            raise DiscussionLogError(
                f"Failed to write discussion log to {log_dir}: {e}"
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
            "Generated discussion log",
            artifact_id=artifact.id,
            room_id=room_id,
            file_path=file_path,
            message_count=len(messages),
        )

        return artifact

    def _build_log_content(
        self,
        room_name: str,
        goal: str,
        messages: List[Dict[str, Any]],
    ) -> str:
        lines: List[str] = []
        lines.append(f"# {room_name}")
        lines.append("")
        lines.append(f"**目标**: {goal}")
        lines.append("")

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"*生成时间: {now}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        rounds: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for msg in messages:
            rounds[msg["round"]].append(msg)

        for round_num in sorted(rounds.keys()):
            lines.append(f"## Round {round_num}")
            lines.append("")
            for msg in rounds[round_num]:
                sender_label = self._get_sender_label(
                    msg["sender_type"], msg.get("sender_id")
                )
                lines.append(f"**{sender_label}**: {msg['content']}")
                lines.append("")
            lines.append("---")
            lines.append("")

        summary = self._build_summary(messages)
        lines.append("## 统计摘要")
        lines.append("")
        lines.append(summary)

        return "\n".join(lines)

    def _get_sender_label(self, sender_type: str, sender_id: Optional[str]) -> str:
        if sender_type == "orchestrator":
            return "主持人"
        elif sender_type == "expert":
            return f"专家 ({sender_id})"
        elif sender_type == "system":
            return "系统"
        else:
            return sender_type

    def _build_summary(self, messages: List[Dict[str, Any]]) -> str:
        round_count = len({m["round"] for m in messages})
        expert_count = len({m.get("sender_id") for m in messages if m["sender_type"] == "expert"})
        return f"共 {len(messages)} 条消息，{round_count} 轮讨论，{expert_count} 位专家参与"
