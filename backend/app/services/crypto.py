"""AES-256-GCM encryption service for API keys."""

import base64
import os
from typing import Tuple

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CryptoService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self) -> None:
        """Initialize crypto service with key from settings."""
        if not settings.encryption_key:
            # Generate a new key if not configured
            self._key = Fernet.generate_key()
            logger.warning("No encryption key configured, generated temporary key")
        else:
            self._key = settings.encryption_key.encode()

        self._fernet = Fernet(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        encrypted = self._fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Failed to decrypt data - invalid token")
            raise

    def mask_key(self, api_key: str) -> str:
        """Mask API key for display purposes.

        Args:
            api_key: The API key to mask

        Returns:
            Masked key (e.g., "sk-abc12345***")
        """
        if not api_key or len(api_key) < 12:
            return "***"

        return f"{api_key[:8]}***"


# Singleton instance
crypto_service = CryptoService()
