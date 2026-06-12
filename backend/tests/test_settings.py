"""Tests for global settings endpoints."""

import pytest
from fastapi import HTTPException

from app.database import DEFAULT_APP_SETTINGS
from app.routers.settings import get_settings, update_settings


@pytest.mark.asyncio
async def test_get_settings_returns_defaults(db_session):
    settings = await get_settings(db_session)

    assert settings == DEFAULT_APP_SETTINGS


@pytest.mark.asyncio
async def test_update_settings_persists_supported_keys(db_session):
    settings = await update_settings(
        {
            "convergence_provider_id": "provider-1",
            "convergence_model_override": "gpt-4o-mini",
        },
        db_session,
    )

    assert settings["convergence_provider_id"] == "provider-1"
    assert settings["convergence_model_override"] == "gpt-4o-mini"

    reloaded = await get_settings(db_session)
    assert reloaded["convergence_provider_id"] == "provider-1"
    assert reloaded["convergence_model_override"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_update_settings_rejects_unknown_keys(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await update_settings({"unknown": "value"}, db_session)

    assert exc_info.value.status_code == 400
