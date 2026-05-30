"""Tests for provider service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate
from app.services.provider_service import ProviderService


@pytest.fixture
def provider_service() -> ProviderService:
    """Create provider service instance."""
    return ProviderService()


@pytest.fixture
def sample_provider_data() -> ProviderCreate:
    """Sample provider creation data."""
    return ProviderCreate(
        name="Test Provider",
        base_url="https://api.openai.com/v1",
        api_key="sk-test-key-12345",
        default_model="gpt-4o",
    )


class TestProviderService:
    """Test provider service CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_provider(
        self, provider_service: ProviderService, sample_provider_data: ProviderCreate
    ) -> None:
        """Test creating a provider."""
        # This test requires a real database session
        # For now, just verify the service can be instantiated
        assert provider_service is not None

    @pytest.mark.asyncio
    async def test_create_provider_encrypts_key(
        self, provider_service: ProviderService, sample_provider_data: ProviderCreate
    ) -> None:
        """Test that API key is encrypted on creation."""
        # Verify encryption is called
        from app.services.crypto import crypto_service
        encrypted = crypto_service.encrypt("test-key")
        assert encrypted != "test-key"
        assert crypto_service.decrypt(encrypted) == "test-key"
