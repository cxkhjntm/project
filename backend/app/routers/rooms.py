"""Room API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.room import (
    RoomCreate,
    RoomListItem,
    RoomResponse,
    RoomUpdate,
)
from app.services.room_service import room_service

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    data: RoomCreate,
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Create a new room with participants."""
    room = await room_service.create(session, data)
    return RoomResponse.model_validate(room)


@router.get("", response_model=List[RoomListItem])
async def list_rooms(
    session: AsyncSession = Depends(get_session),
) -> List[RoomListItem]:
    """List all rooms."""
    rooms = await room_service.get_all(session)
    return [RoomListItem.model_validate(r) for r in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Get a room by ID with participants."""
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse.model_validate(room)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: str,
    data: RoomUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Update a room."""
    room = await room_service.update(session, room_id, data)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse.model_validate(room)


@router.delete("/{room_id}", status_code=204)
async def delete_room(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a room (cascade deletes all related data)."""
    deleted = await room_service.delete(session, room_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Room not found")
