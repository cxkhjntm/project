"""Discussion API endpoints."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.room import Room, RoomParticipant
from app.schemas.discussion import DiscussionControlRequest, DiscussionStatusResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.services.discussion_runtime import discussion_runtime
from app.services.message_service import message_service

TERMINAL_STATUSES = {"completed", "failed", "stopped"}
STARTABLE_STATUSES = {"idle", "draft", "completed", "failed", "stopped"}

router = APIRouter(prefix="/api/rooms", tags=["discussion"])


async def _get_room_with_participants(session: AsyncSession, room_id: str) -> Room | None:
    result = await session.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.participants).selectinload(RoomParticipant.role_card),
            selectinload(Room.participants).selectinload(RoomParticipant.provider),
        )
    )
    return result.scalar_one_or_none()


def _message_event_payload(message) -> dict:
    return MessageResponse.model_validate(message).model_dump(mode="json")


async def _mark_running_and_start_task(room: Room, session: AsyncSession) -> None:
    if not room.participants:
        raise HTTPException(status_code=400, detail="Room has no participants")

    if room.status in STARTABLE_STATUSES - {"draft", "idle"}:
        from app.models.message import Message

        await session.execute(delete(Message).where(Message.room_id == room.id))

    room.status = "running"
    await session.commit()
    discussion_runtime.ensure_started(room.id)


async def _discussion_event_response(room_id: str, session: AsyncSession):
    from sse_starlette.sse import EventSourceResponse

    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    latest_round = await message_service.get_latest_round(session, room_id)
    initial_status = room.status
    total_rounds = room.round_limit
    if initial_status == "running":
        discussion_runtime.ensure_started(room_id)

    terminal_message_count = None
    if initial_status in TERMINAL_STATUSES:
        terminal_message_count = await message_service.count_by_room(session, room_id)

    queue = None
    if initial_status not in TERMINAL_STATUSES:
        queue = discussion_runtime.subscribe(room_id)

    async def event_generator():
        try:
            yield {
                "event": "status",
                "data": json.dumps(
                    {
                        "room_id": room_id,
                        "status": initial_status,
                        "phase": "subscribed",
                        "round": latest_round,
                        "total_rounds": total_rounds,
                    },
                    ensure_ascii=False,
                ),
            }

            if initial_status in TERMINAL_STATUSES:
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "room_id": room_id,
                            "status": initial_status,
                            "total_messages": terminal_message_count or 0,
                        },
                        ensure_ascii=False,
                    ),
                }
                return

            if queue is None:
                return

            while True:
                event_type, data = await queue.get()
                yield {
                    "event": event_type,
                    "data": json.dumps(data, ensure_ascii=False),
                }
                if event_type == "done":
                    break
        finally:
            if queue is not None:
                discussion_runtime.unsubscribe(room_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/{room_id}/start")
async def start_discussion(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Start a discussion in a room.

    This endpoint initiates the discussion and returns an SSE stream.

    Args:
        room_id: Room ID
        session: Database session

    Returns:
        SSE stream of discussion events
    """
    room = await _get_room_with_participants(session, room_id)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status in STARTABLE_STATUSES:
        await _mark_running_and_start_task(room, session)
    elif room.status == "running":
        discussion_runtime.ensure_started(room.id)
    elif room.status != "paused":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Room is in '{room.status}' state, cannot start discussion. "
                "Allowed states: draft, idle, completed, failed, stopped"
            ),
        )

    return await _discussion_event_response(room_id, session)


@router.get("/{room_id}/events")
async def stream_discussion_events(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Subscribe to discussion SSE events without starting a new discussion."""
    return await _discussion_event_response(room_id, session)


@router.get("/{room_id}/messages")
async def get_messages(
    room_id: str,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Get messages for a room.

    Args:
        room_id: Room ID
        limit: Optional limit
        offset: Optional offset
        session: Database session

    Returns:
        List of messages
    """
    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = await message_service.get_by_room(session, room_id, limit=limit, offset=offset)

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{room_id}/messages", response_model=MessageResponse, status_code=201)
async def create_user_message(
    room_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session),
):
    """Create a user message in a room."""
    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    content = str(data.get("content", "")).strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    latest_round = await message_service.get_latest_round(session, room_id)
    effective_round = latest_round
    if room.status in ("running", "paused"):
        effective_round = max(1, latest_round)

    message = await message_service.create(
        session,
        MessageCreate(
            room_id=room_id,
            sender_type="user",
            sender_id=None,
            content=content,
            citations=None,
            round=effective_round,
        ),
    )
    await session.commit()
    await discussion_runtime.broadcast(
        room_id,
        "message",
        _message_event_payload(message),
    )

    return MessageResponse.model_validate(message)


@router.get("/{room_id}/messages/stream")
async def stream_messages(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Stream messages via SSE.

    This endpoint streams new messages as they are created.

    Args:
        room_id: Room ID
        session: Database session

    Returns:
        SSE stream of messages
    """
    from sse_starlette.sse import EventSourceResponse

    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    last_message_count = 0

    async def event_generator():
        nonlocal last_message_count

        while True:
            result = await session.execute(select(Room).where(Room.id == room_id))
            current_room = result.scalar_one_or_none()

            if not current_room:
                break

            if current_room.status in ("completed", "failed", "stopped"):
                messages = await message_service.get_by_room(session, room_id)

                if len(messages) > last_message_count:
                    new_messages = messages[last_message_count:]
                    for msg in new_messages:
                        yield {
                            "event": "message",
                            "data": json.dumps(
                                MessageResponse.model_validate(msg).model_dump(mode="json"),
                                ensure_ascii=False,
                            ),
                        }

                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "room_id": room_id,
                            "status": current_room.status,
                            "total_messages": len(messages),
                        }
                    ),
                }
                break

            messages = await message_service.get_by_room(session, room_id)

            if len(messages) > last_message_count:
                new_messages = messages[last_message_count:]
                last_message_count = len(messages)

                for msg in new_messages:
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            MessageResponse.model_validate(msg).model_dump(mode="json"),
                            ensure_ascii=False,
                        ),
                    }

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.post("/{room_id}/control")
async def control_discussion(
    room_id: str,
    request: DiscussionControlRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    should_commit = True
    if request.action == "start":
        if room.status in STARTABLE_STATUSES:
            room = await _get_room_with_participants(session, room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            await _mark_running_and_start_task(room, session)
            should_commit = False
        elif room.status == "running":
            discussion_runtime.ensure_started(room_id)
            should_commit = False
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Room is in '{room.status}' state, cannot start. "
                    "Allowed states: draft, idle, completed, failed, stopped"
                ),
            )
    elif request.action == "pause":
        if room.status != "running":
            raise HTTPException(status_code=400, detail="Room is not running")
        room.status = "paused"
    elif request.action == "resume":
        if room.status != "paused":
            raise HTTPException(status_code=400, detail="Room is not paused")
        room.status = "running"
    elif request.action == "stop":
        if room.status not in ("running", "paused"):
            raise HTTPException(status_code=400, detail="Room cannot be stopped")
        room.status = "stopped"

    if should_commit:
        await session.commit()
    await discussion_runtime.broadcast(
        room_id,
        "status",
        {
            "room_id": room_id,
            "status": room.status,
            "phase": request.action,
            "round": await message_service.get_latest_round(session, room_id),
            "total_rounds": room.round_limit,
        },
    )

    return {"status": room.status, "action": request.action}


@router.get("/{room_id}/status", response_model=DiscussionStatusResponse)
async def get_discussion_status(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return DiscussionStatusResponse(
        room_id=room.id,
        status=room.status,
        current_round=await message_service.get_latest_round(session, room_id),
        total_rounds=room.round_limit,
        is_paused=room.status == "paused",
        can_pause=room.status == "running",
        can_resume=room.status == "paused",
        can_stop=room.status in ("running", "paused"),
    )
