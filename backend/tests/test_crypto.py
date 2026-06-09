"""Tests for crypto service."""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.services.crypto import CryptoService


@pytest.fixture
def crypto_service() -> CryptoService:
    """Create crypto service with encryption enabled for testing."""
    with patch("app.services.crypto.settings") as mock_settings:
        mock_settings.encrypt_api_keys = True
        mock_settings.encryption_key = Fernet.generate_key().decode()
        yield CryptoService()


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

    def test_decrypt_invalid_token_returns_original(self, crypto_service: CryptoService) -> None:
        """Test that decrypting invalid data returns original (backward compat)."""
        invalid_data = "invalid-encrypted-data"
        result = crypto_service.decrypt(invalid_data)
        assert result == invalid_data

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


class TestOptionalEncryption:
    """Test optional encryption feature."""

    def test_default_mode_returns_plaintext(self) -> None:
        """Test that with encrypt_api_keys=False, encrypt returns plaintext."""
        with patch("app.services.crypto.settings") as mock_settings:
            mock_settings.encrypt_api_keys = False
            mock_settings.encryption_key = ""
            svc = CryptoService()
            plaintext = "sk-test-api-key-12345"
            result = svc.encrypt(plaintext)
            assert result == plaintext

    def test_default_mode_decrypt_returns_original(self) -> None:
        """Test that with encrypt_api_keys=False, decrypt returns original."""
        with patch("app.services.crypto.settings") as mock_settings:
            mock_settings.encrypt_api_keys = False
            mock_settings.encryption_key = ""
            svc = CryptoService()
            plaintext = "sk-test-api-key-12345"
            result = svc.decrypt(plaintext)
            assert result == plaintext

    def test_enabled_encryption_encrypt_decrypt_roundtrip(self) -> None:
        """Test that with encrypt_api_keys=True, encrypt/decrypt works."""
        with patch("app.services.crypto.settings") as mock_settings:
            mock_settings.encrypt_api_keys = True
            mock_settings.encryption_key = Fernet.generate_key().decode()
            svc = CryptoService()
            plaintext = "sk-test-api-key-12345"
            encrypted = svc.encrypt(plaintext)
            assert encrypted != plaintext
            decrypted = svc.decrypt(encrypted)
            assert decrypted == plaintext

    def test_backward_compat_plaintext_when_encryption_enabled(self) -> None:
        """Test that decrypting plaintext works when encryption is enabled."""
        with patch("app.services.crypto.settings") as mock_settings:
            mock_settings.encrypt_api_keys = True
            mock_settings.encryption_key = Fernet.generate_key().decode()
            svc = CryptoService()
            plaintext = "sk-test-api-key-12345"
            result = svc.decrypt(plaintext)
            assert result == plaintext
