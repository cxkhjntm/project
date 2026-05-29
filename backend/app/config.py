"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Expert Room"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./expert_room.db"

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Security
    encryption_key: str = ""  # AES key for API key encryption

    # LLM defaults
    default_max_tokens: int = 4096
    default_temperature: float = 0.7
    max_discussion_rounds: int = 5

    # File processing
    max_file_size_mb: int = 10
    allowed_extensions: List[str] = [
        ".txt", ".md", ".json", ".csv", ".py", ".ts", ".js", ".tsx", ".jsx",
        ".html", ".css", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ]
    excluded_directories: List[str] = [
        "node_modules", ".git", "dist", "build", ".next", ".venv",
        "__pycache__", "target", "coverage", ".idea", ".vscode",
    ]


settings = Settings()

__all__ = ["Settings", "settings"]
