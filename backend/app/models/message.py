"""Message model for discussion messages."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class Message(Base):
    """Discussion message."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # 'user' | 'expert' | 'orchestrator' | 'system'
    )
    sender_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True  # role_card_id for experts
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} round={self.round} sender={self.sender_type}>"
