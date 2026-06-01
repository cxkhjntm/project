"""Discussion API endpoints."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session, async_session_factory
from app.models.room import Room, RoomParticipant
from app.models.role_card import RoleCard
from app.models.provider import Provider
from app.schemas.discussion import DiscussionControlRequest, DiscussionStatusResponse
from app.schemas.message import MessageResponse
from app.services.message_service import message_service
from app.services.orchestrator import Orchestrator, SSEEventType, create_orchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rooms", tags=["discussion"])


@router.post("/{room_id}/start")
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
    from sse_starlette.sse import EventSourceResponse
    
    result = await session.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.participants).selectinload(RoomParticipant.role_card),
            selectinload(Room.participants).selectinload(RoomParticipant.provider),
        )
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status not in ("draft", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Room is in '{room.status}' state, cannot start discussion"
        )
    
    if not room.participants:
        raise HTTPException(
            status_code=400,
            detail="Room has no participants"
        )
    
    room.status = "running"
    await session.flush()
    
    event_queue = asyncio.Queue()
    
    async def on_event(event_type: SSEEventType, data: dict):
        await event_queue.put((event_type.value, data))
    
    async def run_discussion():
        async with async_session_factory() as bg_session:
            merged_room = None
            try:
                merged_room = await bg_session.merge(room)

                orchestrator = create_orchestrator(
                    session=bg_session,
                    room=merged_room,
                    on_event=on_event,
                )

                result = await orchestrator.run_discussion()

                merged_room.status = "completed" if result["success"] else "failed"
                await bg_session.commit()

            except Exception as e:
                logger.error("Discussion failed", error=str(e))
                if merged_room:
                    merged_room.status = "failed"
                    await bg_session.commit()
            finally:
                await event_queue.put(None)
    
    asyncio.create_task(run_discussion())
    
    async def event_generator():
        while True:
            event = await event_queue.get()
            
            if event is None:
                break
            
            event_type, data = event
            yield {
                "event": event_type,
                "data": json.dumps(data, ensure_ascii=False),
            }
    
    return EventSourceResponse(event_generator())


@router.get("/{room_id}/messages")
async def get_messages(
    room_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
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
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    messages = await message_service.get_by_room(
        session, room_id, limit=limit, offset=offset
    )
    
    return [
        MessageResponse.model_validate(m)
        for m in messages
    ]


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
    
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    last_message_count = 0
    
    async def event_generator():
        nonlocal last_message_count
        
        while True:
            result = await session.execute(
                select(Room).where(Room.id == room_id)
            )
            current_room = result.scalar_one_or_none()
            
            if not current_room:
                break
            
            if current_room.status in ("completed", "failed"):
                messages = await message_service.get_by_room(session, room_id)
                
                if len(messages) > last_message_count:
                    new_messages = messages[last_message_count:]
                    for msg in new_messages:
                        yield {
                            "event": "message",
                            "data": json.dumps(
                                MessageResponse.model_validate(msg).model_dump(),
                                ensure_ascii=False,
                            ),
                        }
                
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "room_id": room_id,
                        "status": current_room.status,
                        "total_messages": len(messages),
                    }),
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
                            MessageResponse.model_validate(msg).model_dump(),
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

    if request.action == "start":
        if room.status != "draft":
            raise HTTPException(status_code=400, detail="Room is not in draft state")
        room.status = "running"
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
        room.status = "completed"

    await session.commit()

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
        current_round=0,
        total_rounds=room.round_limit,
        is_paused=room.status == "paused",
        can_pause=room.status == "running",
        can_resume=room.status == "paused",
        can_stop=room.status in ("running", "paused"),
    )
