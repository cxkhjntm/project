"""Provider schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProviderCreate(BaseModel):
    """Schema for creating a provider."""

    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    base_url: str = Field(..., min_length=1, max_length=500, description="API base URL")
    api_key: str = Field(..., min_length=1, description="API key (will be encrypted)")
    default_model: str = Field(..., min_length=1, max_length=100, description="Default model name")
    default_temperature: float = Field(0.7, ge=0.0, le=2.0, description="Default temperature")
    default_max_input_tokens: int = Field(
        128000, ge=1, le=1000000, description="Default max input tokens (context window)"
    )
    default_max_output_tokens: int = Field(
        4096, ge=1, le=1000000, description="Default max output tokens (generation)"
    )


class ProviderUpdate(BaseModel):
    """Schema for updating a provider."""

    name: str | None = Field(None, min_length=1, max_length=100)
    base_url: str | None = Field(None, min_length=1, max_length=500)
    api_key: str | None = Field(None, min_length=1)
    default_model: str | None = Field(None, min_length=1, max_length=100)
    default_temperature: float | None = Field(None, ge=0.0, le=2.0)
    default_max_input_tokens: int | None = Field(None, ge=1, le=1000000)
    default_max_output_tokens: int | None = Field(None, ge=1, le=1000000)
    enabled: bool | None = None


class ProviderResponse(BaseModel):
    """Schema for provider response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    base_url: str
    api_key_masked: str = Field(..., description="Masked API key for display")
    default_model: str
    default_temperature: float
    default_max_input_tokens: int
    default_max_output_tokens: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ProviderTestResponse(BaseModel):
    """Schema for provider test response."""

    success: bool
    message: str
    latency_ms: float | None = None
