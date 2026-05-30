"""Shared source API endpoints."""

import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.shared_source import SharedSourceResponse
from app.services.file_ingestion import file_ingestion_service
from app.services.room_service import room_service
from app.utils.path_validator import validate_path, PathValidationError

router = APIRouter(tags=["sources"])


@router.post(
    "/api/rooms/{room_id}/sources",
    response_model=SharedSourceResponse,
    status_code=201,
)
async def add_source(
    room_id: str,
    source_type: str = Form(...),
    path: str = Form(None),
    content: str = Form(None),
    file: UploadFile = File(None),
    session: AsyncSession = Depends(get_session),
) -> SharedSourceResponse:
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if source_type == "file":
        if not file:
            raise HTTPException(status_code=400, detail="File is required for source_type='file'")
        file_content = await file.read()
        source = await file_ingestion_service.save_uploaded_file(
            session, room_id, file.filename or "unknown", file_content
        )
        if not source:
            raise HTTPException(status_code=400, detail="File rejected: invalid extension or too large")

    elif source_type == "folder":
        if not path:
            raise HTTPException(status_code=400, detail="Path is required for source_type='folder'")
        try:
            validate_path(path, os.getcwd())
        except PathValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        source = await file_ingestion_service.add_folder_source(session, room_id, path)
        if not source:
            raise HTTPException(status_code=400, detail="Invalid folder path")

    elif source_type == "text":
        if not content:
            raise HTTPException(status_code=400, detail="Content is required for source_type='text'")
        source = await file_ingestion_service.add_text_source(session, room_id, content)

    else:
        raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")

    return SharedSourceResponse.model_validate(source)


@router.get("/api/rooms/{room_id}/sources", response_model=List[SharedSourceResponse])
async def list_sources(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> List[SharedSourceResponse]:
    room = await room_service.get_by_id(session, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    sources = await file_ingestion_service.get_room_sources(session, room_id)
    return [SharedSourceResponse.model_validate(s) for s in sources]


@router.delete("/api/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await file_ingestion_service.delete_source(session, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
