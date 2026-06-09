"""Room model for expert group chats."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.message import Message
    from app.models.provider import Provider
    from app.models.role_card import RoleCard
    from app.models.shared_source import SharedSource


class Room(Base):
    """Expert discussion room."""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="code_document")
    strategy: Mapped[str] = mapped_column(String(50), default="standard")
    output_directory: Mapped[str] = mapped_column(String(500), nullable=False)
    round_limit: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    participants: Mapped[list[RoomParticipant]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    sources: Mapped[list[SharedSource]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Room {self.name} (status={self.status})>"


class RoomParticipant(Base):
    """Association between Room and RoleCard."""

    __tablename__ = "room_participants"

    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
    )
    role_card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("role_cards.id"), primary_key=True
    )
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id"), nullable=False)
    model_override: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Transient fields populated by service layer for response serialization
    role_card_name: str = ""
    role_card_expertise: list[str] = []

    # Relationships
    room: Mapped[Room] = relationship(back_populates="participants")
    role_card: Mapped[RoleCard] = relationship(back_populates="room_participations")
    provider: Mapped[Provider] = relationship()

    def __repr__(self) -> str:
        return f"<RoomParticipant room={self.room_id} role={self.role_card_id}>"
