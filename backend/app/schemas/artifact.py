"""Artifact schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ArtifactBase(BaseModel):
    """Base schema with common artifact fields."""
    artifact_type: str = Field(
        ...,
        description="Artifact type: markdown, text, code, csv",
        pattern=r"^(markdown|text|code|csv)$",
    )
    title: str = Field(..., min_length=1, max_length=200, description="Artifact title")
    file_path: str = Field(..., min_length=1, max_length=500, description="Output file path")
    summary: Optional[str] = Field(None, description="Brief summary of artifact content")


class ArtifactCreate(ArtifactBase):
    """Schema for creating an artifact."""
    room_id: str = Field(..., description="Room ID this artifact belongs to")


class ArtifactResponse(BaseModel):
    """Schema for artifact API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    room_id: str
    artifact_type: str
    title: str
    file_path: str
    summary: Optional[str] = None
    created_at: datetime


class ArtifactContent(BaseModel):
    """Schema for artifact content (file body)."""
    content: str = Field(..., description="Full text content of the artifact file")
    encoding: str = Field("utf-8", description="Content encoding")


class SynthesizeRequest(BaseModel):
    """Schema for synthesize endpoint request."""
    room_id: str = Field(..., description="Room ID to synthesize discussion from")
    artifact_type: str = Field(
        "markdown",
        description="Desired output type: markdown, text, code, csv",
        pattern=r"^(markdown|text|code|csv)$",
    )
    title: Optional[str] = Field(None, description="Override artifact title")
    include_citations: bool = Field(True, description="Include source citations in output")
    max_length: Optional[int] = Field(None, ge=100, description="Max output length in characters")


class SynthesizeResponse(BaseModel):
    """Schema for synthesize endpoint response."""
    artifact: ArtifactResponse
    content_preview: Optional[str] = Field(
        None, description="First 500 chars of generated content"
    )
    message: str = Field("Artifact generated successfully", description="Status message")
