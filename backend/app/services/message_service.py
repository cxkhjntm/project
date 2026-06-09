"""Message service for CRUD operations."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.schemas.message import MessageCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MessageService:
    """Service for message CRUD operations."""

    async def create(self, session: AsyncSession, data: MessageCreate) -> Message:
        """Create a new message."""
        import uuid

        citations_dict = None
        if data.citations:
            citations_dict = [c.model_dump() for c in data.citations]

        message = Message(
            id=str(uuid.uuid4()),
            room_id=data.room_id,
            sender_type=data.sender_type,
            sender_id=data.sender_id,
            content=data.content,
            citations=citations_dict,
            round=data.round,
        )

        session.add(message)
        await session.flush()

        logger.info(
            "Created message",
            message_id=message.id,
            room_id=message.room_id,
            sender_type=message.sender_type,
            round=message.round,
        )
        return message

    async def get_by_room(
        self,
        session: AsyncSession,
        room_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Message]:
        """Get messages by room ID."""
        query = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.round.asc(), Message.created_at.asc())
        )

        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, message_id: str) -> Message | None:
        """Get message by ID."""
        result = await session.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()

    async def get_latest_round(self, session: AsyncSession, room_id: str) -> int:
        """Get the latest round number for a room."""
        result = await session.execute(
            select(func.max(Message.round)).where(Message.room_id == room_id)
        )
        max_round = result.scalar_one_or_none()
        return max_round or 0

    async def get_by_room_round(
        self,
        session: AsyncSession,
        room_id: str,
        round_number: int,
    ) -> list[Message]:
        """Get messages for a room in a specific round."""
        result = await session.execute(
            select(Message)
            .where(Message.room_id == room_id, Message.round == round_number)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_by_room(self, session: AsyncSession, room_id: str) -> int:
        """Count messages in a room."""
        result = await session.execute(
            select(func.count()).select_from(Message).where(Message.room_id == room_id)
        )
        return result.scalar_one()


message_service = MessageService()
