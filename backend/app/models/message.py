"""Message model for discussion messages."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

if TYPE_CHECKING:
    from app.models.room import Room


class Message(Base):
    """Discussion message."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # 'user' | 'expert' | 'orchestrator' | 'system'
    )
    sender_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,  # role_card_id for experts
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped[Room] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} round={self.round} sender={self.sender_type}>"
