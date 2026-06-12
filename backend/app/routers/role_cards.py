"""Role card API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.role_card import (
    RoleCardCopyRequest,
    RoleCardCreate,
    RoleCardGenerateRequest,
    RoleCardGenerateResponse,
    RoleCardResponse,
    RoleCardUpdate,
)
from app.services.role_card_service import role_card_service

router = APIRouter(prefix="/api/role-cards", tags=["role-cards"])


@router.post("", response_model=RoleCardResponse, status_code=201)
async def create_role_card(
    data: RoleCardCreate,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Create a new role card."""
    role_card = await role_card_service.create(session, data)
    return RoleCardResponse.model_validate(role_card)


@router.post("/generate", response_model=RoleCardGenerateResponse)
async def generate_role_card(
    data: RoleCardGenerateRequest,
    session: AsyncSession = Depends(get_session),
) -> RoleCardGenerateResponse:
    """Generate a role card from prompt text using LLM."""
    try:
        result = await role_card_service.generate_from_prompt(
            session,
            provider_id=data.provider_id,
            prompt_text=data.prompt_text,
            model_override=data.model_override,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[RoleCardResponse])
async def list_role_cards(
    builtin: bool | None = Query(None, description="Filter by built-in status"),
    session: AsyncSession = Depends(get_session),
) -> list[RoleCardResponse]:
    """List all role cards."""
    role_cards = await role_card_service.get_all(session, builtin_only=builtin or False)
    return [RoleCardResponse.model_validate(rc) for rc in role_cards]


@router.get("/{role_card_id}", response_model=RoleCardResponse)
async def get_role_card(
    role_card_id: str,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Get a role card by ID."""
    role_card = await role_card_service.get_by_id(session, role_card_id)
    if not role_card:
        raise HTTPException(status_code=404, detail="Role card not found")

    return RoleCardResponse.model_validate(role_card)


@router.put("/{role_card_id}", response_model=RoleCardResponse)
async def update_role_card(
    role_card_id: str,
    data: RoleCardUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Update a role card."""
    try:
        role_card = await role_card_service.update(session, role_card_id, data)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not role_card:
        raise HTTPException(status_code=404, detail="Role card not found")

    return RoleCardResponse.model_validate(role_card)


@router.delete("/{role_card_id}", status_code=204)
async def delete_role_card(
    role_card_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a role card."""
    try:
        deleted = await role_card_service.delete(session, role_card_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail="Role card not found")


@router.post("/{role_card_id}/copy", response_model=RoleCardResponse)
async def copy_role_card(
    role_card_id: str,
    data: RoleCardCopyRequest,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Copy a role card."""
    role_card = await role_card_service.copy(session, role_card_id, data.new_name)
    if not role_card:
        raise HTTPException(status_code=404, detail="Role card not found")

    return RoleCardResponse.model_validate(role_card)
