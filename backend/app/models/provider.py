"""Provider model for LLM service configuration."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Provider(Base):
    """LLM service provider configuration."""

    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="openai-compatible")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    default_temperature: Mapped[float] = mapped_column(Float, default=0.7)
    default_max_input_tokens: Mapped[int] = mapped_column(Integer, default=128000)
    default_max_output_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    role_cards: Mapped[list["RoleCard"]] = relationship(back_populates="default_provider")

    def __repr__(self) -> str:
        return f"<Provider {self.name} ({self.type})>"
