"""Room schemas for request/response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParticipantInput(BaseModel):
    """Schema for room participant input."""

    role_card_id: str = Field(..., description="Role card ID")
    provider_id: str = Field(..., description="Provider ID to use for this role")
    model_override: str | None = Field(None, description="Override model for this role")


class RoomCreate(BaseModel):
    """Schema for creating a room."""

    name: str = Field(..., min_length=1, max_length=200, description="Room name")
    goal: str = Field(..., min_length=1, description="Discussion goal")
    mode: Literal["code_document", "document", "code"] = Field(
        "code_document", description="Work mode"
    )
    strategy: Literal["standard"] = Field(
        "standard", description="Discussion strategy (MVP: standard only)"
    )
    output_directory: str = Field(
        ..., min_length=1, max_length=500, description="Output directory path"
    )
    round_limit: int = Field(5, ge=1, le=20, description="Maximum discussion rounds")
    participants: list[ParticipantInput] = Field(..., min_length=1, description="Room participants")


class RoomUpdate(BaseModel):
    """Schema for updating a room."""

    name: str | None = Field(None, min_length=1, max_length=200)
    goal: str | None = Field(None, min_length=1)
    mode: Literal["code_document", "document", "code"] | None = None
    output_directory: str | None = Field(None, min_length=1, max_length=500)
    round_limit: int | None = Field(None, ge=1, le=20)


class ParticipantResponse(BaseModel):
    """Schema for participant response."""

    model_config = ConfigDict(from_attributes=True)

    room_id: str
    role_card_id: str
    role_card_name: str = ""
    role_card_expertise: list[str] = []
    provider_id: str
    model_override: str | None = None


class RoomResponse(BaseModel):
    """Schema for room response."""

    model_config = ConfigDict(from_attributes=True)

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
    participants: list[ParticipantResponse] = []


class RoomListItem(BaseModel):
    """Schema for room list item (without participants)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    goal: str
    mode: str
    status: str
    created_at: datetime
    updated_at: datetime
