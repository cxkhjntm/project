"""Role card schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleCardCreate(BaseModel):
    """Schema for creating a role card."""

    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str = Field(..., min_length=1, description="Role description")
    expertise: list[str] = Field(..., min_length=1, description="Areas of expertise")
    responsibilities: list[str] = Field(..., min_length=1, description="Key responsibilities")
    constraints: list[str] | None = Field(None, description="Behavioral constraints")
    system_prompt: str = Field(..., min_length=1, description="System prompt for the role")
    output_style: str | None = Field(None, description="Preferred output style")
    default_provider_id: str | None = Field(None, description="Default provider ID")
    default_model: str | None = Field(None, description="Default model name")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature setting")


class RoleCardUpdate(BaseModel):
    """Schema for updating a role card."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1)
    expertise: list[str] | None = Field(None, min_length=1)
    responsibilities: list[str] | None = Field(None, min_length=1)
    constraints: list[str] | None = None
    system_prompt: str | None = Field(None, min_length=1)
    output_style: str | None = None
    default_provider_id: str | None = None
    default_model: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)


class RoleCardResponse(BaseModel):
    """Schema for role card response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    expertise: list[str]
    responsibilities: list[str]
    constraints: list[str] | None
    system_prompt: str
    output_style: str | None
    default_provider_id: str | None
    default_model: str | None
    temperature: float
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


class RoleCardCopyRequest(BaseModel):
    """Schema for copying a role card."""

    new_name: str = Field(..., min_length=1, max_length=100, description="Name for the copy")


class RoleCardGenerateRequest(BaseModel):
    """Schema for AI-generating a role card from prompt."""

    provider_id: str = Field(..., description="Provider ID to use for generation")
    model_override: str | None = Field(None, description="Override provider's default model")
    prompt_text: str = Field(
        ..., min_length=10, max_length=50000, description="Raw prompt text to analyze"
    )


class RoleCardGenerateResponse(BaseModel):
    """Schema for generated role card data."""

    name: str
    description: str
    expertise: list[str]
    responsibilities: list[str]
    constraints: list[str] | None = None
    system_prompt: str
    output_style: str | None = None
    temperature: float = 0.7
