"""Room service for CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.provider import Provider
from app.models.role_card import RoleCard
from app.models.room import Room, RoomParticipant
from app.schemas.room import RoomCreate, RoomUpdate
from app.utils.logger import get_logger
from app.utils.path_validator import validate_output_directory

logger = get_logger(__name__)


class RoomService:
    """Service for room CRUD operations."""

    async def create(self, session: AsyncSession, data: RoomCreate) -> Room:
        """Create a new room with participants.

        Args:
            session: Database session
            data: Room creation data

        Returns:
            Created room with participants loaded

        Raises:
            PathValidationError: If output_directory is invalid
            ValueError: If referenced role_card_id or provider_id doesn't exist
        """
        import uuid

        validated_output_dir = validate_output_directory(data.output_directory)

        for p in data.participants:
            role_card = await session.get(RoleCard, p.role_card_id)
            if not role_card:
                raise ValueError(f"Role card not found: {p.role_card_id}")
            provider = await session.get(Provider, p.provider_id)
            if not provider:
                raise ValueError(f"Provider not found: {p.provider_id}")

        room = Room(
            id=str(uuid.uuid4()),
            name=data.name,
            goal=data.goal,
            mode=data.mode,
            strategy=data.strategy,
            output_directory=validated_output_dir,
            round_limit=data.round_limit,
            convergence_agreement_threshold=data.convergence_agreement_threshold,
            convergence_conflict_threshold=data.convergence_conflict_threshold,
            convergence_provider_id=data.convergence_provider_id,
            convergence_model_override=data.convergence_model_override,
            status="draft",
        )
        session.add(room)
        await session.flush()

        # Add participants
        for p in data.participants:
            participant = RoomParticipant(
                room_id=room.id,
                role_card_id=p.role_card_id,
                provider_id=p.provider_id,
                model_override=p.model_override,
            )
            session.add(participant)

        await session.flush()

        # Reload with participants
        result = await session.execute(
            select(Room).where(Room.id == room.id).options(selectinload(Room.participants))
        )
        room = result.scalar_one()

        logger.info("Created room", room_id=room.id, name=room.name)
        return room

    async def get_all(self, session: AsyncSession) -> list[Room]:
        """Get all rooms.

        Args:
            session: Database session

        Returns:
            List of rooms
        """
        result = await session.execute(select(Room).order_by(Room.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, room_id: str) -> Room | None:
        """Get room by ID with participants and role card details.

        Args:
            session: Database session
            room_id: Room ID

        Returns:
            Room with participants enriched with role card data, or None
        """
        result = await session.execute(
            select(Room)
            .where(Room.id == room_id)
            .options(selectinload(Room.participants).selectinload(RoomParticipant.role_card))
        )
        room = result.scalar_one_or_none()

        # Enrich participants with role card details for response serialization
        if room:
            for participant in room.participants:
                if participant.role_card:
                    participant.role_card_name = participant.role_card.name
                    participant.role_card_expertise = participant.role_card.expertise or []
                else:
                    participant.role_card_name = ""
                    participant.role_card_expertise = []

        return room

    async def update(self, session: AsyncSession, room_id: str, data: RoomUpdate) -> Room | None:
        """Update a room.

        Args:
            session: Database session
            room_id: Room ID
            data: Update data

        Returns:
            Updated room or None
        """
        room = await self.get_by_id(session, room_id)
        if not room:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(room, field, value)

        await session.flush()

        logger.info("Updated room", room_id=room.id)
        return room

    async def delete(self, session: AsyncSession, room_id: str) -> bool:
        """Delete a room (cascade deletes participants, sources, messages, artifacts).

        Args:
            session: Database session
            room_id: Room ID

        Returns:
            True if deleted, False if not found
        """
        room = await self.get_by_id(session, room_id)
        if not room:
            return False

        await session.delete(room)
        await session.flush()

        logger.info("Deleted room", room_id=room_id)
        return True

    async def update_status(self, session: AsyncSession, room_id: str, status: str) -> Room | None:
        """Update room status.

        Args:
            session: Database session
            room_id: Room ID
            status: New status (draft, active, completed, error)

        Returns:
            Updated room or None
        """
        room = await self.get_by_id(session, room_id)
        if not room:
            return None

        room.status = status
        await session.flush()

        logger.info("Updated room status", room_id=room.id, status=status)
        return room


# Singleton instance
room_service = RoomService()
