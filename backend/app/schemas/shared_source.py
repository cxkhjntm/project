"""SharedSource schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SharedSourceCreate(BaseModel):
    """Schema for creating a shared source."""
    source_type: str = Field(..., description="Source type: file, folder, text")
    path: Optional[str] = Field(None, description="Path for folder source")
    content: Optional[str] = Field(None, description="Content for text source")


class SharedSourceResponse(BaseModel):
    """Schema for shared source response."""
    id: str
    room_id: str
    source_type: str
    path: Optional[str] = None
    content: Optional[str] = None
    file_count: int
    created_at: datetime

    class Config:
        from_attributes = True
