"""Discussion control schemas for request/response validation."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DiscussionAction(str, Enum):
    """Valid actions for discussion control."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


class DiscussionControlRequest(BaseModel):
    """Schema for controlling a discussion."""

    action: DiscussionAction = Field(..., description="Action to perform on the discussion")
    reason: Optional[str] = Field(None, description="Optional reason for the action")


class DiscussionStatusResponse(BaseModel):
    """Schema for discussion status response."""

    room_id: str
    status: str
    current_round: int
    total_rounds: int
    is_paused: bool
    can_pause: bool
    can_resume: bool
    can_stop: bool
