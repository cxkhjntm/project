"""Provider schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    """Schema for creating a provider."""
    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    base_url: str = Field(..., min_length=1, max_length=500, description="API base URL")
    api_key: str = Field(..., min_length=1, description="API key (will be encrypted)")
    default_model: str = Field(..., min_length=1, max_length=100, description="Default model name")
    default_temperature: float = Field(0.7, ge=0.0, le=2.0, description="Default temperature")
    default_max_tokens: int = Field(4096, ge=1, le=128000, description="Default max tokens")


class ProviderUpdate(BaseModel):
    """Schema for updating a provider."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, min_length=1)
    default_model: Optional[str] = Field(None, min_length=1, max_length=100)
    default_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    enabled: Optional[bool] = None


class ProviderResponse(BaseModel):
    """Schema for provider response."""
    id: str
    name: str
    type: str
    base_url: str
    api_key_masked: str = Field(..., description="Masked API key for display")
    default_model: str
    default_temperature: float
    default_max_tokens: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderTestResponse(BaseModel):
    """Schema for provider test response."""
    success: bool
    message: str
    latency_ms: Optional[float] = None
