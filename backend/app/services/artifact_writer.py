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
    ) -> Artifact:
        if not messages:
            raise ValueError("No messages provided for artifact generation")

        markdown_content = self._build_markdown_content(
            room_name=room_name,
            goal=goal,
            messages=messages,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        artifact_dir = os.path.join(output_directory, f"artifact_{timestamp}")

        try:
            os.makedirs(artifact_dir, exist_ok=True)
            file_path = os.path.join(artifact_dir, "final-plan.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
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

    def _build_markdown_content(
        self,
        room_name: str,
        goal: str,
        messages: List[Dict[str, Any]],
    ) -> str:
        return build_discussion_markdown(
            room_name=room_name,
            goal=goal,
            messages=messages,
            include_summary=False,
        )

    def _get_sender_label(self, sender_type: str, sender_id: Optional[str]) -> str:
        return get_sender_label(sender_type, sender_id)

    def _build_summary(self, messages: List[Dict[str, Any]]) -> str:
        return build_summary(messages)
