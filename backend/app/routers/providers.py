"""Provider API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.provider import (
    ProviderCreate,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
)
from app.services.crypto import crypto_service
from app.services.provider_service import provider_service

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(
    data: ProviderCreate,
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    """Create a new provider."""
    provider = await provider_service.create(session, data)
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key_masked=crypto_service.mask_key(data.api_key),
        default_model=provider.default_model,
        default_temperature=provider.default_temperature,
        default_max_input_tokens=provider.default_max_input_tokens,
        default_max_output_tokens=provider.default_max_output_tokens,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.get("", response_model=List[ProviderResponse])
async def list_providers(
    session: AsyncSession = Depends(get_session),
) -> List[ProviderResponse]:
    """List all providers."""
    providers = await provider_service.get_all(session)
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            type=p.type,
            base_url=p.base_url,
            api_key_masked=crypto_service.mask_key(
                crypto_service.decrypt(p.api_key_encrypted)
            ),
            default_model=p.default_model,
            default_temperature=p.default_temperature,
            default_max_input_tokens=p.default_max_input_tokens,
            default_max_output_tokens=p.default_max_output_tokens,
            enabled=p.enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in providers
    ]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    """Get a provider by ID."""
    provider = await provider_service.get_by_id(session, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key_masked=crypto_service.mask_key(
            crypto_service.decrypt(provider.api_key_encrypted)
        ),
        default_model=provider.default_model,
        default_temperature=provider.default_temperature,
        default_max_input_tokens=provider.default_max_input_tokens,
        default_max_output_tokens=provider.default_max_output_tokens,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    """Update a provider."""
    provider = await provider_service.update(session, provider_id, data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key_masked=crypto_service.mask_key(
            crypto_service.decrypt(provider.api_key_encrypted)
        ),
        default_model=provider.default_model,
        default_temperature=provider.default_temperature,
        default_max_input_tokens=provider.default_max_input_tokens,
        default_max_output_tokens=provider.default_max_output_tokens,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a provider."""
    deleted = await provider_service.delete(session, provider_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProviderTestResponse:
    """Test provider connection."""
    result = await provider_service.test_connection(session, provider_id)
    return ProviderTestResponse(**result)
