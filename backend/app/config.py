"""Application configuration using pydantic-settings."""

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
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Security
    encryption_key: str = ""  # AES key for API key encryption
    encrypt_api_keys: bool = False  # Whether to encrypt API keys at rest

    # LLM defaults
    default_max_tokens: int = 4096
    default_temperature: float = 0.7
    max_discussion_rounds: int = 5

    # Token limits
    max_tokens_per_turn: int = 4096  # Maximum output tokens per LLM call
    max_total_tokens: int = 50000  # Maximum total tokens per discussion

    # File processing
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = [
        ".txt", ".md", ".json", ".csv", ".py", ".ts", ".js", ".tsx", ".jsx",
        ".html", ".css", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ]
    excluded_directories: list[str] = [
        "node_modules", ".git", "dist", "build", ".next", ".venv",
        "__pycache__", "target", "coverage", ".idea", ".vscode",
    ]


settings = Settings()

__all__ = ["Settings", "settings"]
