"""Seed data loader for built-in role cards."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_card import RoleCard
from app.utils.logger import get_logger

logger = get_logger(__name__)

SEED_FILE = Path(__file__).parent / "builtin_roles.json"


async def load_builtin_roles(session: AsyncSession) -> list[RoleCard]:
    """Load built-in role cards from seed file.

    Args:
        session: Database session

    Returns:
        List of loaded role cards (empty if already loaded)
    """
    result = await session.execute(select(RoleCard).where(RoleCard.is_builtin).limit(1))
    if result.scalar_one_or_none() is not None:
        logger.info("Built-in roles already loaded, skipping")
        return []

    if not SEED_FILE.exists():
        logger.warning("Seed file not found", path=str(SEED_FILE))
        return []

    with open(SEED_FILE, encoding="utf-8") as f:
        roles_data = json.load(f)

    loaded_roles = []
    for role_data in roles_data:
        role = RoleCard(
            id=f"builtin_{role_data['name'].lower().replace(' ', '_')}",
            name=role_data["name"],
            description=role_data["description"],
            expertise=role_data["expertise"],
            responsibilities=role_data["responsibilities"],
            constraints=role_data.get("constraints"),
            system_prompt=role_data["system_prompt"],
            output_style=role_data.get("output_style"),
            temperature=role_data.get("temperature", 0.7),
            is_builtin=True,
        )
        session.add(role)
        loaded_roles.append(role)

    await session.flush()

    logger.info("Loaded built-in roles", count=len(loaded_roles))
    return loaded_roles
