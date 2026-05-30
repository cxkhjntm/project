"""Tests for crypto service."""

import pytest
from cryptography.fernet import Fernet

from app.services.crypto import CryptoService


@pytest.fixture
def crypto_service() -> CryptoService:
    """Create crypto service with test key."""
    return CryptoService()


class TestCryptoService:
    """Test crypto service functionality."""

    def test_encrypt_decrypt_roundtrip(self, crypto_service: CryptoService) -> None:
        """Test that encrypt then decrypt returns original value."""
        plaintext = "sk-test-api-key-12345"
        encrypted = crypto_service.encrypt(plaintext)
        decrypted = crypto_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, crypto_service: CryptoService) -> None:
        """Test encrypting empty string returns empty."""
        assert crypto_service.encrypt("") == ""

    def test_decrypt_empty_string(self, crypto_service: CryptoService) -> None:
        """Test decrypting empty string returns empty."""
        assert crypto_service.decrypt("") == ""

    def test_encrypt_produces_different_output(self, crypto_service: CryptoService) -> None:
        """Test that encryption produces different output each time (due to random IV)."""
        plaintext = "test-key"
        encrypted1 = crypto_service.encrypt(plaintext)
        encrypted2 = crypto_service.encrypt(plaintext)
        # Fernet uses random IV, so ciphertext should be different
        assert encrypted1 != encrypted2

    def test_decrypt_invalid_token_raises(self, crypto_service: CryptoService) -> None:
        """Test that decrypting invalid data raises InvalidToken."""
        from cryptography.fernet import InvalidToken
        with pytest.raises(InvalidToken):
            crypto_service.decrypt("invalid-encrypted-data")

    def test_mask_key_long(self, crypto_service: CryptoService) -> None:
        """Test masking a long API key."""
        key = "sk-abcdefghijklmnopqrstuvwxyz123456"
        masked = crypto_service.mask_key(key)
        assert masked == "sk-abcde***"
        assert len(masked) < len(key)

    def test_mask_key_short(self, crypto_service: CryptoService) -> None:
        """Test masking a short API key."""
        assert crypto_service.mask_key("short") == "***"

    def test_mask_key_empty(self, crypto_service: CryptoService) -> None:
        """Test masking empty key."""
        assert crypto_service.mask_key("") == "***"
