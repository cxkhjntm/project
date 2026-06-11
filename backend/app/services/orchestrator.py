"""Discussion orchestrator for managing multi-expert conversations."""

import asyncio
import inspect
import re
from collections.abc import Callable, Coroutine
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger
from app.utils.token_counter import estimate_tokens

logger = get_logger(__name__)

CONVERGENCE_KEYWORDS = [
    "可行",
    "同意",
    "没有异议",
    "建议直接",
    "没问题",
    "LGTM",
    "一致",
    "共识",
    "确认",
    "通过",
    "赞成",
    "支持",
]


def parse_host_action(content: str) -> dict[str, Any] | None:
    """Parse ACTION instruction from host message."""
    match = re.search(
        r"ACTION:\s*(next:([^\s`，,。；;]+)|converge|synthesize)",
        content,
        re.IGNORECASE,
    )
    if not match:
        return None
    action_str = match.group(1).lower()
    if action_str == "converge":
        return {"type": "converge"}
    elif action_str == "synthesize":
        return {"type": "synthesize"}
    elif action_str.startswith("next:"):
        expert_id = match.group(2)
        return {"type": "next", "expert_id": expert_id}
    return None


def parse_length_warning(content: str) -> bool:
    """Parse LENGTH_WARNING from host message."""
    return bool(re.search(r"LENGTH_WARNING:\s*true", content, re.IGNORECASE))


def check_convergence(messages: list[dict[str, Any]], min_consensus: int = 2) -> bool:
    """Check if discussion has reached convergence."""
    if not messages:
        return False
    last_round = max(m.get("round", 0) for m in messages)
    last_round_messages = [
        m for m in messages if m.get("round") == last_round and m.get("sender_type") == "expert"
    ]
    if len(last_round_messages) < 2:
        return False
    consensus_count = sum(
        1
        for msg in last_round_messages
        if any(kw in msg.get("content", "") for kw in CONVERGENCE_KEYWORDS)
    )
    return consensus_count >= min_consensus


class DiscussionState(StrEnum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    CONVERGING = "converging"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class SSEEventType(StrEnum):
    THINKING = "thinking"
    MESSAGE = "message"
    TOKEN = "token"
    ARTIFACT = "artifact"
    ERROR = "error"
    DONE = "done"
    STATUS = "status"
    COST_UPDATE = "cost_update"


class Orchestrator:
    def __init__(
        self,
        session: AsyncSession,
        room: Any,
        on_event: Callable[..., Coroutine[Any, Any, None]] | None = None,
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
            self.participants.append(
                {
                    "role_card_id": p.role_card_id,
                    "name": p.role_card.name if p.role_card else "Unknown",
                    "provider_id": p.provider_id,
                    "model": p.model_override or p.provider.default_model,
                    "base_url": p.provider.base_url,
                }
            )

        self.rolling_summary = ""
        self.shared_sources = []
        self.total_messages = 0
        self.total_tokens = 0
        self.all_messages: list[dict[str, Any]] = []
        self.decisions: list[str] = []
        self.mode = room.mode if hasattr(room, "mode") else "code_document"

    def should_continue(self) -> bool:
        return self.current_round < self.max_rounds

    async def _get_room_status(self) -> str:
        """Read latest room status, falling back to the in-memory room object."""
        try:
            from app.models.room import Room

            result = await self.session.execute(select(Room.status).where(Room.id == self.room_id))
            status = result.scalar_one_or_none()
            if inspect.isawaitable(status):
                status = await status
            if isinstance(status, str):
                return status
        except Exception as e:
            logger.debug("Failed to refresh room status", room_id=self.room_id, error=str(e))

        status = getattr(self.room, "status", None)
        return status if isinstance(status, str) else "running"

    async def _wait_if_paused(self) -> bool:
        """Wait while room is paused. Return False if discussion should stop."""
        while True:
            status = await self._get_room_status()
            if status == "paused":
                self.state = DiscussionState.PAUSED
                await self.emit_event(
                    SSEEventType.STATUS,
                    {
                        "room_id": self.room_id,
                        "status": "paused",
                        "phase": "paused",
                        "round": self.current_round,
                        "total_rounds": self.max_rounds,
                    },
                )
                await asyncio.sleep(1)
                continue
            if status in ("stopped", "failed"):
                return False
            self.state = DiscussionState.RUNNING
            return True

    async def _should_stop(self) -> bool:
        return (await self._get_room_status()) in ("stopped", "failed")

    def _participants_for_action(
        self,
        action: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if not action or action.get("type") != "next":
            return self.participants

        target = str(action.get("expert_id", "")).strip().lower()
        if not target:
            return self.participants

        for participant in self.participants:
            if target in {
                str(participant.get("role_card_id", "")).lower(),
                str(participant.get("name", "")).lower(),
            }:
                return [participant]

        logger.warning(
            "Host selected unknown expert, falling back to all participants",
            target=target,
            room_id=self.room_id,
        )
        return self.participants

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

    async def emit_event(self, event_type: SSEEventType, data: dict[str, Any]) -> None:
        if self.on_event:
            await self.on_event(event_type, data)

        logger.debug("SSE event emitted", type=event_type, data=data)

    async def run_discussion(self) -> dict[str, Any]:
        try:
            self.state = DiscussionState.RUNNING

            await self.emit_event(
                SSEEventType.STATUS,
                {
                    "room_id": self.room_id,
                    "status": "running",
                    "phase": "discussing",
                    "round": 0,
                    "total_rounds": self.max_rounds,
                },
            )

            await self.load_shared_sources()

            while self.should_continue():
                if not await self._wait_if_paused():
                    break

                self.current_round += 1

                await self.emit_event(
                    SSEEventType.STATUS,
                    {
                        "room_id": self.room_id,
                        "status": "running",
                        "phase": "discussing",
                        "round": self.current_round,
                        "total_rounds": self.max_rounds,
                    },
                )

                host_content = await self._run_orchestrator_turn()

                if await self._should_stop():
                    break

                action = parse_host_action(host_content) if host_content else None
                length_warning = parse_length_warning(host_content) if host_content else False

                for participant in self._participants_for_action(action):
                    if not await self._wait_if_paused():
                        break
                    await self._run_expert_turn(participant, length_warning)
                    if await self._should_stop():
                        break

                if await self._should_stop():
                    break

                await self._update_rolling_summary()

                if action and action.get("type") == "converge":
                    break

                if action and action.get("type") == "synthesize":
                    break

                if self._check_convergence():
                    break

            stopped = await self._should_stop()
            if stopped:
                self.state = DiscussionState.STOPPED
                artifact_info = None
            else:
                self.state = DiscussionState.COMPLETED

                # 自动生成产出物
                artifact_info = await self._auto_generate_artifact()

            await self.emit_event(
                SSEEventType.DONE,
                {
                    "room_id": self.room_id,
                    "status": "stopped" if stopped else "completed",
                    "total_rounds": self.current_round,
                    "total_messages": self.total_messages,
                    "artifact_count": 1 if artifact_info else 0,
                },
            )

            return {
                "success": not stopped,
                "status": "stopped" if stopped else "completed",
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

            await self.emit_event(
                SSEEventType.ERROR,
                {
                    "room_id": self.room_id,
                    "error": str(e),
                    "recoverable": False,
                },
            )

            return {
                "success": False,
                "error": str(e),
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
            }

    async def _run_orchestrator_turn(self) -> str | None:
        await self.emit_event(
            SSEEventType.THINKING,
            {
                "room_id": self.room_id,
                "role": "主持人",
                "status": "思考中",
            },
        )

        from app.services.context_builder import context_builder

        user_guidance = await self._get_user_guidance_context()
        prompt = context_builder.build_orchestrator_prompt(
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self._with_user_guidance(self.rolling_summary, user_guidance),
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            experts=[{"name": p["name"]} for p in self.participants],
            mode=self.mode,
        )

        if not self.participants:
            return None

        provider = self.participants[0]
        api_key = await self._get_api_key(provider["provider_id"])

        from app.services.model_client import ModelClientError, create_model_client

        client = create_model_client(
            base_url=provider["base_url"],
            api_key=api_key,
            model=provider["model"],
        )

        try:
            full_content = ""
            chunk_count = 0
            async for chunk in client.chat_completion_stream(
                messages=[{"role": "user", "content": prompt}]
            ):
                full_content += chunk
                chunk_count += 1
                await self.emit_event(
                    SSEEventType.TOKEN,
                    {
                        "room_id": self.room_id,
                        "role": "主持人",
                        "content": chunk,
                    },
                )
                if chunk_count % 10 == 0:
                    if not await self._wait_if_paused():
                        return None

            if await self._should_stop():
                return None

            from app.schemas.message import MessageCreate
            from app.services.message_service import message_service

            message_data = MessageCreate(
                room_id=self.room_id,
                sender_type="orchestrator",
                sender_id=None,
                content=full_content,
                citations=None,
                round=self.current_round,
            )

            message = await message_service.create(self.session, message_data)
            await self.session.commit()
            self.total_messages += 1
            self.total_tokens += estimate_tokens(prompt) + estimate_tokens(full_content)

            self.all_messages.append(
                {
                    "sender_type": "orchestrator",
                    "sender_id": None,
                    "content": full_content,
                    "round": self.current_round,
                }
            )

            await self.emit_event(
                SSEEventType.MESSAGE,
                {
                    "id": message.id,
                    "room_id": self.room_id,
                    "sender_type": "orchestrator",
                    "sender_id": None,
                    "content": full_content,
                    "citations": [],
                    "round": self.current_round,
                },
            )
            await self._emit_cost_update()

            return full_content

        except ModelClientError as e:
            logger.error("Orchestrator turn failed", error=str(e), round=self.current_round)
            await self.emit_event(
                SSEEventType.ERROR,
                {
                    "room_id": self.room_id,
                    "error": "orchestrator_turn_failed",
                    "message": str(e),
                    "round": self.current_round,
                },
            )
            return None

    async def _run_expert_turn(
        self, participant: dict[str, Any], length_warning: bool = False
    ) -> None:
        role_card_id = participant["role_card_id"]
        role_name = participant["name"]

        await self.emit_event(
            SSEEventType.THINKING,
            {
                "room_id": self.room_id,
                "role": role_name,
                "status": "思考中",
            },
        )

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

        additional_context = None
        extra_contexts = []
        if length_warning:
            extra_contexts.append(
                "⚠️ 上一轮回复过长。本轮请严格控制在 300 字以内，使用要点式输出。"
            )

        user_guidance = await self._get_user_guidance_context()
        if user_guidance:
            extra_contexts.append(user_guidance)

        if extra_contexts:
            additional_context = "\n\n".join(extra_contexts)

        prompt = context_builder.build_expert_prompt(
            role=role_data,
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            mode=self.mode,
            additional_context=additional_context,
        )

        api_key = await self._get_api_key(participant["provider_id"])

        from app.services.model_client import ModelClientError, create_model_client

        client = create_model_client(
            base_url=participant["base_url"],
            api_key=api_key,
            model=participant["model"],
        )

        try:
            full_content = ""
            chunk_count = 0
            async for chunk in client.chat_completion_stream(
                messages=[{"role": "user", "content": prompt}]
            ):
                full_content += chunk
                chunk_count += 1
                await self.emit_event(
                    SSEEventType.TOKEN,
                    {
                        "room_id": self.room_id,
                        "role": role_name,
                        "content": chunk,
                    },
                )
                if chunk_count % 10 == 0:
                    if not await self._wait_if_paused():
                        return

            if await self._should_stop():
                return

            from app.schemas.message import MessageCreate
            from app.services.message_service import message_service

            message_data = MessageCreate(
                room_id=self.room_id,
                sender_type="expert",
                sender_id=role_card_id,
                content=full_content,
                citations=None,
                round=self.current_round,
            )

            message = await message_service.create(self.session, message_data)
            await self.session.commit()
            self.total_messages += 1
            self.total_tokens += estimate_tokens(prompt) + estimate_tokens(full_content)

            key_point = self._extract_key_point(full_content)

            self.all_messages.append(
                {
                    "sender_type": "expert",
                    "sender_id": role_name,
                    "content": full_content,
                    "round": self.current_round,
                }
            )

            await self.emit_event(
                SSEEventType.MESSAGE,
                {
                    "id": message.id,
                    "room_id": self.room_id,
                    "sender_type": "expert",
                    "sender_id": role_card_id,
                    "content": full_content,
                    "citations": [],
                    "round": self.current_round,
                    "key_point": key_point,
                },
            )
            await self._emit_cost_update()

        except ModelClientError as e:
            logger.error(
                "Expert turn failed",
                role=role_name,
                error=str(e),
                round=self.current_round,
            )

            await self.emit_event(
                SSEEventType.ERROR,
                {
                    "room_id": self.room_id,
                    "error": f"{role_name}发言失败: {str(e)}",
                    "recoverable": True,
                },
            )

    async def _get_api_key(self, provider_id: str) -> str:
        from app.services.crypto import crypto_service
        from app.services.provider_service import provider_service

        provider = await provider_service.get_by_id(self.session, provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        try:
            return crypto_service.decrypt(provider.api_key_encrypted)
        except Exception as e:
            logger.error("Failed to decrypt API key", provider_id=provider_id, error=str(e))
            raise ValueError(f"Failed to decrypt API key for provider {provider_id}") from e

    async def _update_rolling_summary(self) -> None:
        from app.services.context_builder import context_builder
        from app.services.message_service import message_service

        messages = await message_service.get_by_room_round(
            self.session,
            self.room_id,
            self.current_round,
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

    async def _get_user_guidance_context(self) -> str:
        from app.models.message import Message

        result = await self.session.execute(
            select(Message)
            .where(Message.room_id == self.room_id, Message.sender_type == "user")
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())[-8:]
        if not messages:
            return ""

        lines = []
        for message in messages:
            content = message.content.strip()
            if len(content) > 300:
                content = content[:300] + "..."
            if message.round > 0:
                lines.append(f"- 第 {message.round} 轮用户指引：{content}")
            else:
                lines.append(f"- 用户预置指引：{content}")

        return "## 用户最新指引\n这些指引由用户在讨论中补充，请从下一次发言开始遵循：\n" + "\n".join(
            lines
        )

    def _with_user_guidance(self, rolling_summary: str, user_guidance: str) -> str:
        if not user_guidance:
            return rolling_summary
        if not rolling_summary:
            return user_guidance
        return f"{rolling_summary}\n\n{user_guidance}"

    def _check_convergence(self) -> bool:
        if self.current_round >= self.max_rounds:
            return True
        if self.current_round < 2:
            return False
        return check_convergence(self.all_messages)

    def _extract_key_point(self, content: str) -> str | None:
        skip_patterns = [
            r"^(关于|针对|对于|关于这个|说到|谈到|提及|涉及|回到)",
            r"^#{1,6}\s",
            r"^[-*]\s",
            r"^```",
            r"^\s*$",
            r"^>\s",
        ]
        lines = content.split("\n")
        for line in lines:
            trimmed = line.strip()
            if len(trimmed) < 15:
                continue
            if any(re.match(p, trimmed) for p in skip_patterns):
                continue
            cleaned = trimmed.replace("**", "").replace("*", "").replace("`", "")
            return cleaned[:100]
        meaningful = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
        return max(meaningful, key=len)[:100] if meaningful else None

    async def _auto_generate_artifact(self) -> dict[str, Any] | None:
        """讨论完成后自动生成产出物。"""
        try:
            from app.services.message_service import message_service

            db_messages = await message_service.get_by_room(self.session, self.room_id)
            artifact_messages = [
                {
                    "sender_type": message.sender_type,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "round": message.round,
                    "citations": message.citations,
                }
                for message in db_messages
            ] or self.all_messages

            if not artifact_messages:
                logger.warning("No messages to generate artifact from", room_id=self.room_id)
                return None

            output_directory = getattr(self.room, "output_directory", None)
            if not output_directory:
                logger.warning("No output directory configured", room_id=self.room_id)
                return None

            from app.services.artifact_writer import ArtifactWriter

            writer = ArtifactWriter(self.session)

            participant_names = [p["name"] for p in self.participants]
            model_name = self.participants[0]["model"] if self.participants else "unknown"

            artifact = await writer.generate_artifact(
                room_id=self.room_id,
                room_name=self.room.name if hasattr(self.room, "name") else "专家讨论",
                goal=self.goal,
                messages=artifact_messages,
                output_directory=output_directory,
                mode=self.mode,
                participants=participant_names,
                source_count=len(self.shared_sources),
                model_name=model_name,
            )

            await self.session.commit()

            artifact_info = {
                "id": artifact.id,
                "title": artifact.title,
                "file_path": artifact.file_path,
                "artifact_type": artifact.artifact_type,
                "summary": artifact.summary,
            }

            await self.emit_event(
                SSEEventType.ARTIFACT,
                {
                    "room_id": self.room_id,
                    "artifact": artifact_info,
                },
            )

            logger.info(
                "Auto-generated artifact",
                room_id=self.room_id,
                artifact_id=artifact.id,
            )
            return artifact_info

        except Exception as e:
            logger.error(
                "Auto artifact generation failed",
                room_id=self.room_id,
                error=str(e),
            )
            await self.emit_event(
                SSEEventType.ERROR,
                {
                    "room_id": self.room_id,
                    "error": f"产出物自动生成失败: {str(e)}",
                    "recoverable": True,
                },
            )
            return None

    async def _emit_cost_update(self) -> None:
        await self.emit_event(
            SSEEventType.COST_UPDATE,
            {
                "room_id": self.room_id,
                "total_tokens": self.total_tokens,
                "round": self.current_round,
                "estimated": True,
            },
        )


def create_orchestrator(
    session: AsyncSession,
    room: Any,
    on_event: Callable[..., Coroutine[Any, Any, None]] | None = None,
) -> Orchestrator:
    return Orchestrator(session=session, room=room, on_event=on_event)
