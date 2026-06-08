"""AES-256-GCM encryption service for API keys."""

import base64
import os
from pathlib import Path
from typing import Tuple

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_KEY_FILE = Path(__file__).resolve().parent.parent.parent / ".encryption_key"


class CryptoService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, key_file: Path | None = None) -> None:
        """Initialize crypto service with key from settings."""
        self._key_file = key_file or _KEY_FILE
        self._enabled = settings.encrypt_api_keys

        if not self._enabled:
            self._fernet = None
            logger.info("API key encryption disabled, storing plaintext")
            return

        if settings.encryption_key:
            key_bytes = settings.encryption_key.encode()
            try:
                Fernet(key_bytes)  # Validate before using
                self._key = key_bytes
                logger.info("Using encryption key from ENCRYPTION_KEY env var")
            except ValueError:
                logger.warning(
                    "Invalid ENCRYPTION_KEY in env var (must be 32 url-safe base64-encoded bytes), "
                    "falling back to key file",
                    env_key_preview=settings.encryption_key[:8] + "***"
                    if len(settings.encryption_key) > 8
                    else "***",
                )
                self._key = self._load_or_generate_key()
        else:
            self._key = self._load_or_generate_key()

        self._fernet = Fernet(self._key)

    def _load_or_generate_key(self) -> bytes:
        """Load key from file or generate and persist a new one.

        Returns:
            Fernet-compatible key bytes
        """
        if self._key_file.exists():
            try:
                key = self._key_file.read_bytes().strip()
                # Validate it's a valid Fernet key
                Fernet(key)
                logger.info("Loaded encryption key from file", path=str(self._key_file))
                return key
            except Exception:
                logger.warning(
                    "Invalid key in file, regenerating",
                    path=str(self._key_file),
                )

        key = Fernet.generate_key()
        try:
            self._key_file.parent.mkdir(parents=True, exist_ok=True)
            self._key_file.write_bytes(key)
            # Restrict file permissions (best-effort, may not work on Windows)
            try:
                os.chmod(self._key_file, 0o600)
            except OSError:
                pass
            logger.warning(
                "No encryption key configured, generated and persisted new key",
                path=str(self._key_file),
            )
        except OSError as e:
            logger.error(
                "Failed to persist encryption key, using in-memory key",
                error=str(e),
            )

        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string."""
        if not plaintext:
            return ""

        if not self._enabled:
            return plaintext

        encrypted = self._fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string."""
        if not ciphertext:
            return ""

        if not self._enabled:
            return ciphertext

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.warning("Decryption failed, returning plaintext (backward compat)")
            return ciphertext

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
