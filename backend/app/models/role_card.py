"""RoleCard model for expert personas."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class RoleCard(Base):
    """Expert role card configuration."""

    __tablename__ = "role_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expertise: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    responsibilities: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    constraints: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_provider_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("providers.id"), nullable=True
    )
    default_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    default_provider: Mapped[Optional["Provider"]] = relationship(back_populates="role_cards")
    room_participations: Mapped[list["RoomParticipant"]] = relationship(back_populates="role_card")

    def __repr__(self) -> str:
        return f"<RoleCard {self.name} (builtin={self.is_builtin})>"
