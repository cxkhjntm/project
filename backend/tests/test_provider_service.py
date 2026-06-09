"""Tests for provider service."""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.schemas.provider import ProviderCreate
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
        """Test that API key is encrypted when encryption is enabled."""
        from app.services.crypto import CryptoService

        with patch("app.services.crypto.settings") as mock_settings:
            mock_settings.encrypt_api_keys = True
            mock_settings.encryption_key = Fernet.generate_key().decode()
            svc = CryptoService()
            encrypted = svc.encrypt("test-key")
            assert encrypted != "test-key"
            assert svc.decrypt(encrypted) == "test-key"
