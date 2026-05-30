"""Discussion orchestrator for managing multi-expert conversations."""

from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscussionState(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    CONVERGING = "converging"
    COMPLETED = "completed"
    FAILED = "failed"


class SSEEventType(str, Enum):
    THINKING = "thinking"
    MESSAGE = "message"
    ARTIFACT = "artifact"
    ERROR = "error"
    DONE = "done"


class Orchestrator:
    def __init__(
        self,
        session: AsyncSession,
        room: Any,
        on_event: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
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
            self.participants.append({
                "role_card_id": p.role_card_id,
                "name": p.role_card.name if p.role_card else "Unknown",
                "provider_id": p.provider_id,
                "model": p.model_override or p.provider.default_model,
                "base_url": p.provider.base_url,
            })

        self.rolling_summary = ""
        self.shared_sources = []
        self.total_messages = 0

    def should_continue(self) -> bool:
        return self.current_round < self.max_rounds

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

    async def emit_event(self, event_type: SSEEventType, data: Dict[str, Any]) -> None:
        if self.on_event:
            await self.on_event(event_type, data)

        logger.debug("SSE event emitted", type=event_type, data=data)

    async def run_discussion(self) -> Dict[str, Any]:
        try:
            self.state = DiscussionState.RUNNING
            await self.load_shared_sources()

            while self.should_continue():
                self.current_round += 1

                logger.info(
                    "Starting discussion round",
                    room_id=self.room_id,
                    round=self.current_round,
                    max_rounds=self.max_rounds,
                )

                await self._run_orchestrator_turn()

                for participant in self.participants:
                    await self._run_expert_turn(participant)

                await self._update_rolling_summary()

                if self._check_convergence():
                    logger.info(
                        "Discussion converged",
                        room_id=self.room_id,
                        round=self.current_round,
                    )
                    break

            self.state = DiscussionState.COMPLETED

            await self.emit_event(SSEEventType.DONE, {
                "room_id": self.room_id,
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
                "artifact_count": 0,
            })

            return {
                "success": True,
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
            }

        except Exception as e:
            self.state = DiscussionState.FAILED
            logger.error(
                "Discussion failed",
                room_id=self.room_id,
                error=str(e),
                round=self.current_round,
            )

            await self.emit_event(SSEEventType.ERROR, {
                "room_id": self.room_id,
                "error": str(e),
                "recoverable": False,
            })

            return {
                "success": False,
                "error": str(e),
                "total_rounds": self.current_round,
                "total_messages": self.total_messages,
            }

    async def _run_orchestrator_turn(self) -> None:
        await self.emit_event(SSEEventType.THINKING, {
            "room_id": self.room_id,
            "role": "主持人",
            "status": "思考中",
        })

        from app.services.context_builder import context_builder

        prompt = context_builder.build_orchestrator_prompt(
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
            experts=[{"name": p["name"]} for p in self.participants],
        )

        if self.participants:
            provider = self.participants[0]
            api_key = await self._get_api_key(provider["provider_id"])

            from app.services.model_client import create_model_client, ModelClientError

            client = create_model_client(
                base_url=provider["base_url"],
                api_key=api_key,
                model=provider["model"],
            )

            try:
                response = await client.chat_completion(
                    messages=[{"role": "user", "content": prompt}]
                )

                from app.schemas.message import MessageCreate
                from app.services.message_service import message_service

                message_data = MessageCreate(
                    room_id=self.room_id,
                    sender_type="orchestrator",
                    sender_id=None,
                    content=response.content,
                    citations=None,
                    round=self.current_round,
                )

                message = await message_service.create(self.session, message_data)
                self.total_messages += 1

                await self.emit_event(SSEEventType.MESSAGE, {
                    "id": message.id,
                    "room_id": self.room_id,
                    "sender_type": "orchestrator",
                    "sender_id": None,
                    "content": response.content,
                    "citations": [],
                    "round": self.current_round,
                })

            except ModelClientError as e:
                logger.error(
                    "Orchestrator turn failed",
                    error=str(e),
                    round=self.current_round,
                )

    async def _run_expert_turn(self, participant: Dict[str, Any]) -> None:
        role_card_id = participant["role_card_id"]
        role_name = participant["name"]

        await self.emit_event(SSEEventType.THINKING, {
            "room_id": self.room_id,
            "role": role_name,
            "status": "思考中",
        })

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

        prompt = context_builder.build_expert_prompt(
            role=role_data,
            goal=self.goal,
            shared_sources=self.shared_sources,
            rolling_summary=self.rolling_summary,
            current_round=self.current_round,
            total_rounds=self.max_rounds,
        )

        api_key = await self._get_api_key(participant["provider_id"])

        from app.services.model_client import create_model_client, ModelClientError

        client = create_model_client(
            base_url=participant["base_url"],
            api_key=api_key,
            model=participant["model"],
        )

        try:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )

            from app.schemas.message import MessageCreate
            from app.services.message_service import message_service

            message_data = MessageCreate(
                room_id=self.room_id,
                sender_type="expert",
                sender_id=role_card_id,
                content=response.content,
                citations=None,
                round=self.current_round,
            )

            message = await message_service.create(self.session, message_data)
            self.total_messages += 1

            await self.emit_event(SSEEventType.MESSAGE, {
                "id": message.id,
                "room_id": self.room_id,
                "sender_type": "expert",
                "sender_id": role_card_id,
                "content": response.content,
                "citations": [],
                "round": self.current_round,
            })

        except ModelClientError as e:
            logger.error(
                "Expert turn failed",
                role=role_name,
                error=str(e),
                round=self.current_round,
            )

            await self.emit_event(SSEEventType.ERROR, {
                "room_id": self.room_id,
                "error": f"{role_name}发言失败: {str(e)}",
                "recoverable": True,
            })

    async def _get_api_key(self, provider_id: str) -> str:
        from app.services.provider_service import provider_service
        from app.services.crypto import crypto_service

        provider = await provider_service.get_by_id(self.session, provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        return crypto_service.decrypt(provider.api_key_encrypted)

    async def _update_rolling_summary(self) -> None:
        from app.services.message_service import message_service
        from app.services.context_builder import context_builder

        messages = await message_service.get_by_room(
            self.session,
            self.room_id,
            limit=len(self.participants) + 1,
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

    def _check_convergence(self) -> bool:
        if self.current_round >= self.max_rounds:
            return True

        return False


def create_orchestrator(
    session: AsyncSession,
    room: Any,
    on_event: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
) -> Orchestrator:
    return Orchestrator(session=session, room=room, on_event=on_event)
