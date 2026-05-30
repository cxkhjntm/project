"""Discussion log generator service for producing formatted discussion logs."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.utils.formatters import build_discussion_markdown, build_summary, get_sender_label
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
        return build_discussion_markdown(
            room_name=room_name,
            goal=goal,
            messages=messages,
            include_summary=True,
        )

    def _get_sender_label(self, sender_type: str, sender_id: Optional[str]) -> str:
        return get_sender_label(sender_type, sender_id)

    def _build_summary(self, messages: List[Dict[str, Any]]) -> str:
        return build_summary(messages)
