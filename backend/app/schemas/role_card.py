"""Role card schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleCardCreate(BaseModel):
    """Schema for creating a role card."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str = Field(..., min_length=1, description="Role description")
    expertise: List[str] = Field(..., min_length=1, description="Areas of expertise")
    responsibilities: List[str] = Field(..., min_length=1, description="Key responsibilities")
    constraints: Optional[List[str]] = Field(None, description="Behavioral constraints")
    system_prompt: str = Field(..., min_length=1, description="System prompt for the role")
    output_style: Optional[str] = Field(None, description="Preferred output style")
    default_provider_id: Optional[str] = Field(None, description="Default provider ID")
    default_model: Optional[str] = Field(None, description="Default model name")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature setting")


class RoleCardUpdate(BaseModel):
    """Schema for updating a role card."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1)
    expertise: Optional[List[str]] = Field(None, min_length=1)
    responsibilities: Optional[List[str]] = Field(None, min_length=1)
    constraints: Optional[List[str]] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    output_style: Optional[str] = None
    default_provider_id: Optional[str] = None
    default_model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class RoleCardResponse(BaseModel):
    """Schema for role card response."""
    id: str
    name: str
    description: str
    expertise: List[str]
    responsibilities: List[str]
    constraints: Optional[List[str]]
    system_prompt: str
    output_style: Optional[str]
    default_provider_id: Optional[str]
    default_model: Optional[str]
    temperature: float
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleCardCopyRequest(BaseModel):
    """Schema for copying a role card."""
    new_name: str = Field(..., min_length=1, max_length=100, description="Name for the copy")
