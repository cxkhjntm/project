"""Room schemas for request/response validation."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ParticipantInput(BaseModel):
    """Schema for room participant input."""
    role_card_id: str = Field(..., description="Role card ID")
    provider_id: str = Field(..., description="Provider ID to use for this role")
    model_override: Optional[str] = Field(None, description="Override model for this role")


class RoomCreate(BaseModel):
    """Schema for creating a room."""
    name: str = Field(..., min_length=1, max_length=200, description="Room name")
    goal: str = Field(..., min_length=1, description="Discussion goal")
    mode: Literal["code_document", "document", "code"] = Field("code_document", description="Work mode")
    strategy: Literal["standard"] = Field("standard", description="Discussion strategy (MVP: standard only)")
    output_directory: str = Field(..., min_length=1, max_length=500, description="Output directory path")
    round_limit: int = Field(5, ge=1, le=20, description="Maximum discussion rounds")
    participants: List[ParticipantInput] = Field(..., min_length=1, description="Room participants")


class RoomUpdate(BaseModel):
    """Schema for updating a room."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    goal: Optional[str] = Field(None, min_length=1)
    mode: Optional[Literal["code_document", "document", "code"]] = None
    output_directory: Optional[str] = Field(None, min_length=1, max_length=500)
    round_limit: Optional[int] = Field(None, ge=1, le=20)


class ParticipantResponse(BaseModel):
    """Schema for participant response."""
    room_id: str
    role_card_id: str
    provider_id: str
    model_override: Optional[str] = None

    class Config:
        from_attributes = True


class RoomResponse(BaseModel):
    """Schema for room response."""
    id: str
    name: str
    goal: str
    mode: str
    strategy: str
    output_directory: str
    round_limit: int
    status: str
    created_at: datetime
    updated_at: datetime
    participants: List[ParticipantResponse] = []

    class Config:
        from_attributes = True


class RoomListItem(BaseModel):
    """Schema for room list item (without participants)."""
    id: str
    name: str
    goal: str
    mode: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
