"""Role card service for CRUD operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_card import RoleCard
from app.schemas.role_card import RoleCardCreate, RoleCardUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RoleCardService:
    """Service for role card CRUD operations."""

    async def create(self, session: AsyncSession, data: RoleCardCreate) -> RoleCard:
        """Create a new role card.
        
        Args:
            session: Database session
            data: Role card creation data
            
        Returns:
            Created role card
        """
        import uuid
        
        role_card = RoleCard(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            expertise=data.expertise,
            responsibilities=data.responsibilities,
            constraints=data.constraints,
            system_prompt=data.system_prompt,
            output_style=data.output_style,
            default_provider_id=data.default_provider_id,
            default_model=data.default_model,
            temperature=data.temperature,
            is_builtin=False,
        )
        
        session.add(role_card)
        await session.flush()
        
        logger.info("Created role card", role_card_id=role_card.id, name=role_card.name)
        return role_card

    async def get_all(
        self, session: AsyncSession, builtin_only: bool = False
    ) -> List[RoleCard]:
        """Get all role cards.
        
        Args:
            session: Database session
            builtin_only: If True, return only built-in role cards
            
        Returns:
            List of role cards
        """
        query = select(RoleCard).order_by(RoleCard.name)
        
        if builtin_only:
            query = query.where(RoleCard.is_builtin == True)
        
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, role_card_id: str) -> Optional[RoleCard]:
        """Get role card by ID.
        
        Args:
            session: Database session
            role_card_id: Role card ID
            
        Returns:
            Role card or None
        """
        result = await session.execute(
            select(RoleCard).where(RoleCard.id == role_card_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, role_card_id: str, data: RoleCardUpdate
    ) -> Optional[RoleCard]:
        """Update a role card.
        
        Args:
            session: Database session
            role_card_id: Role card ID
            data: Update data
            
        Returns:
            Updated role card or None
            
        Raises:
            ValueError: If trying to update a built-in role card
        """
        role_card = await self.get_by_id(session, role_card_id)
        if not role_card:
            return None
        
        if role_card.is_builtin:
            raise ValueError("Cannot modify built-in role cards")
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(role_card, field, value)
        
        await session.flush()
        
        logger.info("Updated role card", role_card_id=role_card.id)
        return role_card

    async def delete(self, session: AsyncSession, role_card_id: str) -> bool:
        """Delete a role card.
        
        Args:
            session: Database session
            role_card_id: Role card ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If trying to delete a built-in role card
        """
        role_card = await self.get_by_id(session, role_card_id)
        if not role_card:
            return False
        
        if role_card.is_builtin:
            raise ValueError("Cannot delete built-in role cards")
        
        await session.delete(role_card)
        await session.flush()
        
        logger.info("Deleted role card", role_card_id=role_card_id)
        return True

    async def copy(
        self, session: AsyncSession, role_card_id: str, new_name: str
    ) -> Optional[RoleCard]:
        """Copy a role card.
        
        Args:
            session: Database session
            role_card_id: Source role card ID
            new_name: Name for the copy
            
        Returns:
            Copied role card or None
        """
        import uuid
        
        source = await self.get_by_id(session, role_card_id)
        if not source:
            return None
        
        copy = RoleCard(
            id=str(uuid.uuid4()),
            name=new_name,
            description=source.description,
            expertise=source.expertise,
            responsibilities=source.responsibilities,
            constraints=source.constraints,
            system_prompt=source.system_prompt,
            output_style=source.output_style,
            default_provider_id=source.default_provider_id,
            default_model=source.default_model,
            temperature=source.temperature,
            is_builtin=False,
        )
        
        session.add(copy)
        await session.flush()
        
        logger.info("Copied role card", source_id=role_card_id, copy_id=copy.id)
        return copy


# Singleton instance
role_card_service = RoleCardService()
