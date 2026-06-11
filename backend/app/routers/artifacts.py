"""Artifact API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.artifact import Artifact
from app.models.room import Room
from app.schemas.artifact import (
    ArtifactContent,
    ArtifactResponse,
    SynthesizeRequest,
    SynthesizeResponse,
)
from app.services.artifact_writer import ArtifactWriter, ArtifactWriterError
from app.services.message_service import message_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["artifacts"])


@router.post(
    "/api/rooms/{room_id}/synthesize",
    response_model=SynthesizeResponse,
)
async def synthesize_artifact(
    room_id: str,
    request: SynthesizeRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> SynthesizeResponse:
    """Generate artifact from room discussion messages."""
    request = request or SynthesizeRequest()

    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = await message_service.get_by_room(session, room_id)
    if not messages:
        raise HTTPException(status_code=400, detail="No messages found in room for synthesis")

    message_dicts = [
        {
            "sender_type": m.sender_type,
            "sender_id": m.sender_id,
            "content": m.content,
            "round": m.round,
            "citations": m.citations,
        }
        for m in messages
    ]

    writer = ArtifactWriter(session)
    try:
        result = await writer.generate_artifact(
            room_id=room_id,
            room_name=request.title or room.name,
            goal=room.goal,
            messages=message_dicts,
            output_directory=room.output_directory,
            mode=room.mode,
            max_length=request.max_length,
        )
    except ArtifactWriterError as e:
        logger.error("Artifact generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    content_preview = None
    try:
        with open(result.final_artifact.file_path, encoding="utf-8") as f:
            content = f.read()
            content_preview = content[:500]
    except OSError:
        pass

    return SynthesizeResponse(
        artifact=ArtifactResponse.model_validate(result.final_artifact),
        artifacts=[ArtifactResponse.model_validate(a) for a in result.artifacts],
        discussion_log=ArtifactResponse.model_validate(result.discussion_log),
        fallback_used=result.fallback_used,
        content_preview=content_preview or result.content_preview,
        message="Artifact generated successfully",
    )


@router.get(
    "/api/rooms/{room_id}/artifacts",
    response_model=list[ArtifactResponse],
)
async def list_artifacts(
    room_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[ArtifactResponse]:
    """List all artifacts for a room."""
    result = await session.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await session.execute(
        select(Artifact).where(Artifact.room_id == room_id).order_by(Artifact.created_at.desc())
    )
    artifacts = result.scalars().all()

    return [ArtifactResponse.model_validate(a) for a in artifacts]


@router.get(
    "/api/artifacts/{artifact_id}/content",
    response_model=ArtifactContent,
)
async def get_artifact_content(
    artifact_id: str,
    session: AsyncSession = Depends(get_session),
) -> ArtifactContent:
    """Get the content of an artifact file."""
    result = await session.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        with open(artifact.file_path, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        logger.error(
            "Failed to read artifact file",
            artifact_id=artifact_id,
            file_path=artifact.file_path,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to read artifact file: {e}")

    return ArtifactContent(content=content, encoding="utf-8")
