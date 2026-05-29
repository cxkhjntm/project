"""SharedSource model for uploaded files and folders."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SharedSource(Base):
    """Shared data source (file, folder, or text)."""

    __tablename__ = "shared_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # 'file' | 'folder' | 'text'
    )
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship(back_populates="sources")

    def __repr__(self) -> str:
        return f"<SharedSource {self.source_type} room={self.room_id}>"
