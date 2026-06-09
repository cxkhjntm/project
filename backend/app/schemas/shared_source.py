"""SharedSource schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SharedSourceCreate(BaseModel):
    """Schema for creating a shared source."""

    source_type: str = Field(..., description="Source type: file, folder, text")
    path: str | None = Field(None, description="Path for folder source")
    content: str | None = Field(None, description="Content for text source")


class SharedSourceResponse(BaseModel):
    """Schema for shared source response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    room_id: str
    source_type: str
    path: str | None = None
    content: str | None = None
    file_count: int
    created_at: datetime
