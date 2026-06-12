"""Global application settings model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    """Application-level key-value settings."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
