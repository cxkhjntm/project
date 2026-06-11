"""In-memory runtime for active discussion tasks and SSE subscribers."""

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models.room import Room, RoomParticipant
from app.services.orchestrator import SSEEventType, create_orchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)

DiscussionEvent = tuple[str, dict[str, Any]]
SubscriberQueue = asyncio.Queue[DiscussionEvent]


class DiscussionRuntime:
    """Coordinates one active discussion task and many SSE subscribers per room."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._subscribers: dict[str, set[SubscriberQueue]] = {}

    def has_active_task(self, room_id: str) -> bool:
        task = self._tasks.get(room_id)
        return bool(task and not task.done())

    def ensure_started(self, room_id: str) -> bool:
        """Start the room task if absent. Return True when a new task was created."""
        if self.has_active_task(room_id):
            return False

        task = asyncio.create_task(self._run_room(room_id))
        self._tasks[room_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(room_id, None))
        return True

    def subscribe(self, room_id: str) -> SubscriberQueue:
        queue: SubscriberQueue = asyncio.Queue(maxsize=200)
        self._subscribers.setdefault(room_id, set()).add(queue)
        return queue

    def unsubscribe(self, room_id: str, queue: SubscriberQueue) -> None:
        subscribers = self._subscribers.get(room_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(room_id, None)

    async def broadcast(self, room_id: str, event_type: str, data: dict[str, Any]) -> None:
        subscribers = list(self._subscribers.get(room_id, set()))
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await queue.put((event_type, data))

    async def _run_room(self, room_id: str) -> None:
        async with async_session_factory() as bg_session:
            room: Room | None = None
            try:
                result = await bg_session.execute(
                    select(Room)
                    .where(Room.id == room_id)
                    .options(
                        selectinload(Room.participants).selectinload(
                            RoomParticipant.role_card
                        ),
                        selectinload(Room.participants).selectinload(
                            RoomParticipant.provider
                        ),
                    )
                )
                room = result.scalar_one_or_none()
                if not room:
                    return

                orchestrator = create_orchestrator(
                    session=bg_session,
                    room=room,
                    on_event=lambda event_type, data: self.broadcast(
                        room_id, event_type.value, data
                    ),
                )

                result_data = await orchestrator.run_discussion()
                room.status = result_data.get(
                    "status",
                    "completed" if result_data.get("success") else "failed",
                )
                await bg_session.commit()

            except Exception as e:
                logger.error("Discussion task failed", room_id=room_id, error=str(e))
                if room:
                    room.status = "failed"
                    await bg_session.commit()
                await self.broadcast(
                    room_id,
                    SSEEventType.ERROR.value,
                    {
                        "room_id": room_id,
                        "error": str(e),
                        "recoverable": False,
                    },
                )
                await self.broadcast(
                    room_id,
                    SSEEventType.DONE.value,
                    {
                        "room_id": room_id,
                        "status": "failed",
                        "total_messages": 0,
                    },
                )


discussion_runtime = DiscussionRuntime()
