"""Message schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    """Citation reference to source material."""
    source_id: str = Field(..., description="Source ID")
    file: Optional[str] = Field(None, description="File name")
    snippet: Optional[str] = Field(None, description="Relevant snippet")


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    room_id: str = Field(..., description="Room ID")
    sender_type: str = Field(..., description="Sender type: user|expert|orchestrator|system")
    sender_id: Optional[str] = Field(None, description="Role card ID for experts")
    content: str = Field(..., min_length=1, description="Message content")
    citations: Optional[List[Citation]] = Field(None, description="Citations")
    round: int = Field(..., ge=0, description="Discussion round number")


class MessageResponse(BaseModel):
    """Schema for message response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    room_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content: str
    citations: Optional[List[Citation]] = None
    round: int
    created_at: datetime


class MessageListItem(BaseModel):
    """Schema for message list item."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    room_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content: str
    round: int
    created_at: datetime
