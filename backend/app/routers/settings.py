"""Global settings API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DEFAULT_APP_SETTINGS, get_session
from app.models.settings import AppSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _settings_with_defaults(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(AppSettings))
    values = {setting.key: setting.value for setting in result.scalars().all()}

    missing = False
    for key, default_value in DEFAULT_APP_SETTINGS.items():
        if key not in values:
            values[key] = default_value
            session.add(AppSettings(key=key, value=default_value))
            missing = True

    if missing:
        await session.flush()

    return values


@router.get("")
async def get_settings(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Get all global application settings."""
    return await _settings_with_defaults(session)


@router.put("")
async def update_settings(
    data: dict[str, str],
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Update supported global application settings."""
    unknown_keys = set(data) - set(DEFAULT_APP_SETTINGS)
    if unknown_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported setting keys: {', '.join(sorted(unknown_keys))}",
        )

    current = await _settings_with_defaults(session)
    for key, value in data.items():
        normalized = "" if value is None else str(value)
        setting = await session.get(AppSettings, key)
        if setting is None:
            session.add(AppSettings(key=key, value=normalized))
        else:
            setting.value = normalized
        current[key] = normalized

    await session.flush()
    return current
