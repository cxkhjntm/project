# Stage 0: Project Initialization & Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the complete project scaffold with Python FastAPI backend, React frontend, database migrations, and basic configuration - making both frontend and backend runnable.

**Architecture:** Local-first desktop app with Python FastAPI backend (runs as Tauri sidecar) and React frontend. SQLite database with SQLAlchemy ORM and Alembic migrations. Structured logging with structlog, environment config with pydantic-settings.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, SQLite, structlog, pydantic-settings, React 18, TypeScript, Vite, Tailwind CSS, Zustand, React Router

---

## File Structure

### Backend Files (to create)
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # pydantic-settings configuration
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   ├── role_card.py
│   │   ├── room.py
│   │   ├── message.py
│   │   ├── shared_source.py
│   │   └── artifact.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── routers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── seed/
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # structlog configuration
│       └── file_filter.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── tests/
    └── __init__.py
```

### Frontend Files (to create)
```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes.tsx
│   ├── pages/
│   │   └── HomePage.tsx
│   ├── components/
│   │   └── shared/
│   │       └── Layout.tsx
│   ├── hooks/
│   ├── stores/
│   ├── api/
│   │   └── client.ts
│   ├── types/
│   │   └── index.ts
│   └── styles/
│       └── globals.css
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── index.html
```

---

## Task 1: Python Backend Project Initialization

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/routers backend/app/services backend/app/seed backend/app/utils backend/tests
```

- [ ] **Step 2: Create pyproject.toml with project metadata**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "expert-room-backend"
version = "0.1.0"
description = "AI Expert Team Collaboration Workbench - Backend"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "Expert Room Team" },
]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "alembic>=1.13.1",
    "aiosqlite>=0.19.0",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "structlog>=24.1.0",
    "httpx>=0.26.0",
    "sse-starlette>=1.8.2",
    "cryptography>=42.0.2",
    "python-multipart>=0.0.6",
    "chardet>=5.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.4",
    "pytest-asyncio>=0.23.3",
    "httpx>=0.26.0",
    "ruff>=0.1.14",
    "mypy>=1.8.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create requirements.txt for pip users**

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.25
alembic>=1.13.1
aiosqlite>=0.19.0
pydantic>=2.5.3
pydantic-settings>=2.1.0
structlog>=24.1.0
httpx>=0.26.0
sse-starlette>=1.8.2
cryptography>=42.0.2
python-multipart>=0.0.6
chardet>=5.2.0

# Dev dependencies
pytest>=7.4.4
pytest-asyncio>=0.23.3
ruff>=0.1.14
mypy>=1.8.0
```

- [ ] **Step 4: Create backend/app/__init__.py**

```python
"""Expert Room Backend - AI Expert Team Collaboration Workbench."""
```

- [ ] **Step 5: Create backend/app/main.py with FastAPI app**

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Expert Room API",
        description="AI Expert Team Collaboration Workbench",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
```

- [ ] **Step 6: Verify FastAPI app starts**

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Expected: Server starts on http://localhost:8000, visit http://localhost:8000/docs shows Swagger UI

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): initialize FastAPI project structure

- Create pyproject.toml with all dependencies
- Create requirements.txt for pip users
- Create FastAPI app with health check endpoint
- Configure CORS for frontend development"
```

---

## Task 2: Database Configuration (SQLAlchemy + Alembic + SQLite)

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Create backend/app/config.py with pydantic-settings**

```python
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
```

- [ ] **Step 2: Create .env.example file**

```bash
# Application
APP_NAME=Expert Room
DEBUG=false

# Database
DATABASE_URL=sqlite+aiosqlite:///./expert_room.db

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Security - Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=

# LLM Defaults
DEFAULT_MAX_TOKENS=4096
DEFAULT_TEMPERATURE=0.7
MAX_DISCUSSION_ROUNDS=5

# File Processing
MAX_FILE_SIZE_MB=10
```

- [ ] **Step 3: Create backend/app/database.py with SQLAlchemy async setup**

```python
"""Database configuration with SQLAlchemy async engine."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_session() -> AsyncSession:
    """Get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 4: Create alembic.ini**

```ini
# Alembic Configuration File

[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite+aiosqlite:///./expert_room.db

[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ${ruff_executable:ruff}
ruff.options = format --target-version py312 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 5: Create alembic/env.py with async support**

```python
"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base

# Import all models here so Alembic can detect them
from app.models import provider, role_card, room, message, shared_source, artifact  # noqa: F401

# Alembic Config object
config = context.config

# Set sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogeneration
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: Create alembic/script.py.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 7: Initialize Alembic**

```bash
cd backend
alembic init alembic
# Replace the generated env.py and script.py.mako with our custom versions
```

- [ ] **Step 8: Verify Alembic configuration**

```bash
cd backend
alembic current
```

Expected: Shows current migration version (empty for new database)

- [ ] **Step 9: Commit**

```bash
git add backend/app/config.py backend/app/database.py backend/alembic.ini backend/alembic/ backend/.env.example
git commit -m "feat(backend): configure SQLAlchemy + Alembic + SQLite

- Add pydantic-settings configuration with .env support
- Configure async SQLAlchemy engine with aiosqlite
- Set up Alembic for database migrations
- Create database session management
- Add .env.example with all configuration options"
```

---

## Task 3: Database Models (7 Tables)

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/provider.py`
- Create: `backend/app/models/role_card.py`
- Create: `backend/app/models/room.py`
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/shared_source.py`
- Create: `backend/app/models/artifact.py`

- [ ] **Step 1: Create backend/app/models/__init__.py**

```python
"""Database models for Expert Room."""

from app.models.provider import Provider
from app.models.role_card import RoleCard
from app.models.room import Room, RoomParticipant
from app.models.message import Message
from app.models.shared_source import SharedSource
from app.models.artifact import Artifact

__all__ = [
    "Provider",
    "RoleCard",
    "Room",
    "RoomParticipant",
    "Message",
    "SharedSource",
    "Artifact",
]
```

- [ ] **Step 2: Create backend/app/models/provider.py**

```python
"""Provider model for LLM service configuration."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Provider(Base):
    """LLM service provider configuration."""

    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="openai-compatible")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    default_temperature: Mapped[float] = mapped_column(Float, default=0.7)
    default_max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    role_cards: Mapped[list["RoleCard"]] = relationship(back_populates="default_provider")

    def __repr__(self) -> str:
        return f"<Provider {self.name} ({self.type})>"
```

- [ ] **Step 3: Create backend/app/models/role_card.py**

```python
"""RoleCard model for expert personas."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class RoleCard(Base):
    """Expert role card configuration."""

    __tablename__ = "role_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expertise: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    responsibilities: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    constraints: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_provider_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("providers.id"), nullable=True
    )
    default_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    default_provider: Mapped[Optional["Provider"]] = relationship(back_populates="role_cards")
    room_participations: Mapped[list["RoomParticipant"]] = relationship(back_populates="role_card")

    def __repr__(self) -> str:
        return f"<RoleCard {self.name} (builtin={self.is_builtin})>"
```

- [ ] **Step 4: Create backend/app/models/room.py**

```python
"""Room model for expert group chats."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Room(Base):
    """Expert discussion room."""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="code_document")
    strategy: Mapped[str] = mapped_column(String(50), default="standard")
    output_directory: Mapped[str] = mapped_column(String(500), nullable=False)
    round_limit: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    participants: Mapped[list["RoomParticipant"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    sources: Mapped[list["SharedSource"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Room {self.name} (status={self.status})>"


class RoomParticipant(Base):
    """Association between Room and RoleCard."""

    __tablename__ = "room_participants"

    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
    )
    role_card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("role_cards.id"), primary_key=True
    )
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("providers.id"), nullable=False
    )
    model_override: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    room: Mapped["Room"] = relationship(back_populates="participants")
    role_card: Mapped["RoleCard"] = relationship(back_populates="room_participations")
    provider: Mapped["Provider"] = relationship()

    def __repr__(self) -> str:
        return f"<RoomParticipant room={self.room_id} role={self.role_card_id}>"
```

- [ ] **Step 5: Create backend/app/models/message.py**

```python
"""Message model for discussion messages."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class Message(Base):
    """Discussion message."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # 'user' | 'expert' | 'orchestrator' | 'system'
    )
    sender_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True  # role_card_id for experts
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} round={self.round} sender={self.sender_type}>"
```

- [ ] **Step 6: Create backend/app/models/shared_source.py**

```python
"""SharedSource model for uploaded files and folders."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SharedSource(Base):
    """Shared data source (file, folder, or text)."""

    __tablename__ = "shared_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # 'file' | 'folder' | 'text'
    )
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship(back_populates="sources")

    def __repr__(self) -> str:
        return f"<SharedSource {self.source_type} room={self.room_id}>"
```

- [ ] **Step 7: Create backend/app/models/artifact.py**

```python
"""Artifact model for generated outputs."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Artifact(Base):
    """Generated output artifact."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # 'markdown' | 'text' | 'code' | 'csv'
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship(back_populates="artifacts")

    def __repr__(self) -> str:
        return f"<Artifact {self.title} type={self.artifact_type}>"
```

- [ ] **Step 8: Verify models can be imported**

```bash
cd backend
python -c "from app.models import Provider, RoleCard, Room, Message, SharedSource, Artifact; print('All models imported successfully')"
```

Expected: "All models imported successfully"

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/
git commit -m "feat(backend): add all 7 database models

- Provider: LLM service configuration
- RoleCard: Expert persona definitions
- Room: Discussion room with participants
- Message: Discussion messages with citations
- SharedSource: Uploaded files/folders/text
- Artifact: Generated output files
- RoomParticipant: Many-to-many room-role association"
```

---

## Task 4: Alembic Migration for 7 Tables

**Files:**
- Create: `backend/alembic/versions/001_initial_tables.py` (auto-generated)

- [ ] **Step 1: Generate initial migration**

```bash
cd backend
alembic revision --autogenerate -m "create initial 7 tables"
```

Expected: Creates migration file in alembic/versions/

- [ ] **Step 2: Review generated migration**

Check the generated file to ensure all 7 tables are created:
- providers
- role_cards
- rooms
- room_participants
- shared_sources
- messages
- artifacts

- [ ] **Step 3: Apply migration**

```bash
cd backend
alembic upgrade head
```

Expected: "Running upgrade -> <revision_id>, create initial 7 tables"

- [ ] **Step 4: Verify tables exist**

```bash
cd backend
sqlite3 expert_room.db ".tables"
```

Expected output:
```
alembic_version  artifacts        messages         providers
room_participants  rooms            role_cards       shared_sources
```

- [ ] **Step 5: Verify table structure**

```bash
cd backend
sqlite3 expert_room.db ".schema providers"
sqlite3 expert_room.db ".schema role_cards"
sqlite3 expert_room.db ".schema rooms"
```

Expected: Shows correct column definitions for each table

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(backend): create initial database migration

- Generate Alembic migration for all 7 tables
- Apply migration to create SQLite database
- Verify all tables created with correct schema"
```

---

## Task 5: Structured Logging with structlog

**Files:**
- Create: `backend/app/utils/__init__.py`
- Create: `backend/app/utils/logger.py`

- [ ] **Step 1: Create backend/app/utils/__init__.py**

```python
"""Utility modules for Expert Room backend."""
```

- [ ] **Step 2: Create backend/app/utils/logger.py with structlog configuration**

```python
"""Structured logging configuration with sensitive data masking."""

import logging
import re
import sys
from typing import Any

import structlog

# Patterns for sensitive data
SENSITIVE_PATTERNS = [
    (re.compile(r'(api[_-]?key["\s:=]+)\s*\S+', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(sk-[a-zA-Z0-9]{8})[a-zA-Z0-9]+', re.IGNORECASE), r'\1***'),
    (re.compile(r'(password["\s:=]+)\s*\S+', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(token["\s:=]+)\s*\S+', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(secret["\s:=]+)\s*\S+', re.IGNORECASE), r'\1***MASKED***'),
]


def mask_sensitive_data(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Mask sensitive data in log events."""
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern, replacement in SENSITIVE_PATTERNS:
                event_dict[key] = pattern.sub(replacement, value)
    return event_dict


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging with structlog."""
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            mask_sensitive_data,
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)
```

- [ ] **Step 3: Update backend/app/main.py to use logging**

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logger import setup_logging, get_logger

# Setup logging
setup_logging(debug=settings.debug)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Expert Room API",
        description="AI Expert Team Collaboration Workbench",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Starting Expert Room API", version="0.1.0", debug=settings.debug)

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down Expert Room API")

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
```

- [ ] **Step 4: Test logging output**

```bash
cd backend
python -c "
from app.utils.logger import setup_logging, get_logger
setup_logging(debug=True)
logger = get_logger('test')
logger.info('Test message', user='testuser', api_key='sk-abc12345xyz')
logger.info('Password test', password='secret123', token='bearer_xyz')
"
```

Expected: Shows log output with masked sensitive data

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/
git commit -m "feat(backend): add structured logging with sensitive data masking

- Configure structlog with JSON output for production
- Add sensitive data masking for API keys, passwords, tokens
- Support debug mode with console output
- Integrate logging into FastAPI application"
```

---

## Task 6: Pydantic-Settings Configuration

**Files:**
- Modify: `backend/app/config.py` (already created)
- Create: `backend/.env` (gitignored)

- [ ] **Step 1: Create backend/.env file**

```bash
# Application
APP_NAME=Expert Room
DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./expert_room.db

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Security - Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-encryption-key-here

# LLM Defaults
DEFAULT_MAX_TOKENS=4096
DEFAULT_TEMPERATURE=0.7
MAX_DISCUSSION_ROUNDS=5

# File Processing
MAX_FILE_SIZE_MB=10
```

- [ ] **Step 2: Verify .env is in .gitignore**

Check that .gitignore contains:
```
.env
.env.local
.env.*.local
```

- [ ] **Step 3: Test configuration loading**

```bash
cd backend
python -c "
from app.config import settings
print(f'App Name: {settings.app_name}')
print(f'Debug: {settings.debug}')
print(f'Database URL: {settings.database_url}')
print(f'CORS Origins: {settings.cors_origins}')
print(f'Max Rounds: {settings.max_discussion_rounds}')
"
```

Expected: Shows configuration values loaded from .env

- [ ] **Step 4: Test environment variable override**

```bash
cd backend
DEBUG=false python -c "
from app.config import settings
print(f'Debug: {settings.debug}')
"
```

Expected: Shows "Debug: False" (overridden by environment variable)

- [ ] **Step 5: Commit**

```bash
git add backend/.env.example
git commit -m "feat(backend): configure pydantic-settings with .env support

- Load configuration from .env file
- Support environment variable overrides
- Add .env.example with all options documented
- Ensure .env is gitignored for security"
```

---

## Task 7: React Frontend Project Initialization

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles/globals.css`

- [ ] **Step 1: Initialize Vite React TypeScript project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
```

Expected: Creates Vite project with React TypeScript template

- [ ] **Step 2: Update package.json with dependencies**

```json
{
  "name": "expert-room-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.26.0",
    "zustand": "^5.0.0",
    "react-hook-form": "^7.53.0",
    "@hookform/resolvers": "^3.3.4",
    "zod": "^3.23.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.55.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.6.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 3: Install dependencies**

```bash
cd frontend
npm install
```

Expected: Installs all dependencies successfully

- [ ] **Step 4: Configure Tailwind CSS**

Create `frontend/tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
      },
    },
  },
  plugins: [],
}
```

Create `frontend/postcss.config.js`:
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: Create global CSS with Tailwind directives**

Create `frontend/src/styles/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 6: Configure Vite with proxy for backend**

Create `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 7: Create basic App component**

Create `frontend/src/App.tsx`:
```tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          专家团
        </h1>
        <p className="text-lg text-gray-600">
          AI Expert Team Collaboration Workbench
        </p>
        <div className="mt-8 p-4 bg-white rounded-lg shadow-sm">
          <p className="text-sm text-gray-500">
            Stage 0 scaffold complete. Frontend is running.
          </p>
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </Router>
  )
}

export default App
```

- [ ] **Step 8: Update main.tsx**

Create `frontend/src/main.tsx`:
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 9: Verify frontend starts**

```bash
cd frontend
npm run dev
```

Expected: Frontend starts on http://localhost:5173 and shows "专家团" heading

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): initialize React TypeScript project with Vite

- Create Vite project with React TypeScript template
- Configure Tailwind CSS with custom theme
- Set up React Router for client-side routing
- Add Vite proxy configuration for backend API
- Create basic App component with home page
- Install all required dependencies"
```

---

## Task 8: React Router + Zustand Configuration

**Files:**
- Create: `frontend/src/routes.tsx`
- Create: `frontend/src/stores/index.ts`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/shared/Layout.tsx`

- [ ] **Step 1: Create frontend/src/routes.tsx**

```tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/shared/Layout'
import HomePage from './pages/HomePage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
```

- [ ] **Step 2: Create frontend/src/pages/HomePage.tsx**

```tsx
export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          专家团
        </h1>
        <p className="text-lg text-gray-600">
          AI Expert Team Collaboration Workbench
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="font-semibold text-gray-900 mb-2">⚙️ 设置</h3>
          <p className="text-sm text-gray-600">
            配置模型服务商和 API Key
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="font-semibold text-gray-900 mb-2">   角色卡</h3>
          <p className="text-sm text-gray-600">
            管理专家角色和提示词
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="font-semibold text-gray-900 mb-2">   群聊</h3>
          <p className="text-sm text-gray-600">
            创建和管理专家讨论
          </p>
        </div>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-700">
          ✅ Stage 0 scaffold complete. Frontend and backend are ready for development.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create frontend/src/components/shared/Layout.tsx**

```tsx
import { Outlet, Link, useLocation } from 'react-router-dom'

const navigation = [
  { name: '首页', href: '/' },
  { name: '设置', href: '/settings' },
  { name: '角色卡', href: '/role-cards' },
  { name: '群聊', href: '/rooms' },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center">
                <span className="text-xl font-bold text-gray-900">专家团</span>
              </Link>
              <nav className="ml-8 flex space-x-8">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      location.pathname === item.href
                        ? 'border-blue-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {item.name}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/src/stores/index.ts**

```typescript
import { create } from 'zustand'

// Generic store factory
export function createStore<T extends Record<string, unknown>>(
  name: string,
  initialState: T
) {
  return create<T>()((set) => ({
    ...initialState,
    reset: () => set(initialState),
  }))
}
```

- [ ] **Step 5: Create frontend/src/types/index.ts**

```typescript
// API Response types
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

// Provider types
export interface Provider {
  id: string
  name: string
  type: string
  baseUrl: string
  defaultModel: string
  defaultTemperature: number
  defaultMaxTokens: number
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface CreateProviderRequest {
  name: string
  baseUrl: string
  apiKey: string
  defaultModel: string
  defaultTemperature?: number
  defaultMaxTokens?: number
}

// RoleCard types
export interface RoleCard {
  id: string
  name: string
  description: string
  expertise: string[]
  responsibilities: string[]
  constraints?: string[]
  systemPrompt: string
  outputStyle?: string
  defaultProviderId?: string
  defaultModel?: string
  temperature: number
  isBuiltin: boolean
  createdAt: string
  updatedAt: string
}

// Room types
export interface Room {
  id: string
  name: string
  goal: string
  mode: 'code_document' | 'document' | 'code'
  strategy: 'standard' | 'quick' | 'strict'
  outputDirectory: string
  roundLimit: number
  status: 'draft' | 'active' | 'completed' | 'failed'
  createdAt: string
  updatedAt: string
}

// Message types
export interface Message {
  id: string
  roomId: string
  senderType: 'user' | 'expert' | 'orchestrator' | 'system'
  senderId?: string
  content: string
  citations?: Citation[]
  round: number
  createdAt: string
}

export interface Citation {
  sourceId: string
  file: string
  snippet: string
}

// SSE Event types
export interface SSEEvent {
  event: 'thinking' | 'message' | 'artifact' | 'error' | 'done'
  data: Record<string, unknown>
}
```

- [ ] **Step 6: Create frontend/src/api/client.ts**

```typescript
const API_BASE_URL = '/api'

interface RequestOptions extends RequestInit {
  params?: Record<string, string>
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value)
      })
    }
    return url.toString()
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { params, ...fetchOptions } = options
    const url = this.buildUrl(path, params)

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>(path, { method: 'GET', params })
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' })
  }
}

export const api = new ApiClient(API_BASE_URL)
```

- [ ] **Step 7: Update App.tsx to use router**

```tsx
import { AppRouter } from './routes'

function App() {
  return <AppRouter />
}

export default App
```

- [ ] **Step 8: Verify routing works**

```bash
cd frontend
npm run dev
```

Expected: Navigation links work, pages render correctly

- [ ] **Step 9: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): configure React Router and Zustand

- Set up React Router with nested layouts
- Create main navigation with active state
- Add Zustand store factory
- Define TypeScript types for all API entities
- Create API client with fetch wrapper
- Add responsive layout with header navigation"
```

---

## Task 9: Frontend-Backend Connectivity Verification

**Files:**
- Create: `frontend/src/pages/HomePage.tsx` (update with health check)

- [ ] **Step 1: Update HomePage to test backend connection**

```tsx
import { useState, useEffect } from 'react'

interface HealthStatus {
  status: string
  version: string
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(data => {
        setHealth(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          专家团
        </h1>
        <p className="text-lg text-gray-600">
          AI Expert Team Collaboration Workbench
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="font-semibold text-gray-900 mb-2">⚙️ 设置</h3>
          <p className="text-sm text-gray-600">
            配置模型服务商和 API Key
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="font-semibold text-gray-900 mb-2">   角色卡</h3>
          <p className="text-sm text-gray-600">
            管理专家角色和提示词
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="font-semibold text-gray-900 mb-2">   群聊</h3>
          <p className="text-sm text-gray-600">
            创建和管理专家讨论
          </p>
        </div>
      </div>

      <div className="mt-8 p-6 bg-white rounded-lg shadow-sm border">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">后端连接状态</h2>
        
        {loading && (
          <div className="text-blue-600">正在连接后端...</div>
        )}
        
        {error && (
          <div className="text-red-600">
            ❌ 连接失败: {error}
            <p className="text-sm text-gray-500 mt-2">
              请确保后端服务正在运行: <code>cd backend && uvicorn app.main:app --reload</code>
            </p>
          </div>
        )}
        
        {health && (
          <div className="text-green-600">
            ✅ 后端连接成功
            <div className="mt-2 text-sm text-gray-600">
              <p>状态: {health.status}</p>
              <p>版本: {health.version}</p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-700">
          ✅ Stage 0 scaffold complete. Frontend and backend are ready for development.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Start both frontend and backend**

Terminal 1 (Backend):
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

- [ ] **Step 3: Verify connectivity**

Open http://localhost:5173 in browser:
- Should see "专家团" heading
- Should see "✅ 后端连接成功" with status and version
- No CORS errors in browser console

- [ ] **Step 4: Test API proxy**

```bash
# Direct backend call
curl http://localhost:8000/api/health

# Through frontend proxy
curl http://localhost:5173/api/health
```

Expected: Both return `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 5: Verify no CORS issues**

Check browser console for:
- No CORS errors
- Successful fetch to `/api/health`
- Response shows `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: verify frontend-backend connectivity

- Add health check to home page
- Display connection status with loading states
- Show helpful error message if backend not running
- Verify CORS and proxy configuration work correctly"
```

---

## Final Verification

- [ ] **Step 1: Run all backend checks**

```bash
cd backend
# Verify Python version
python --version

# Verify dependencies installed
pip list | grep -E "fastapi|sqlalchemy|alembic|structlog|pydantic"

# Verify database migration
alembic current
sqlite3 expert_room.db ".tables"

# Verify app starts
uvicorn app.main:app --reload &
sleep 3
curl http://localhost:8000/api/health
kill %1
```

- [ ] **Step 2: Run all frontend checks**

```bash
cd frontend
# Verify Node.js version
node --version

# Verify dependencies installed
npm list --depth=0

# Verify build works
npm run build

# Verify dev server starts
npm run dev &
sleep 5
curl -s http://localhost:5173 | grep "专家团"
kill %1
```

- [ ] **Step 3: Verify Git status**

```bash
git status
git log --oneline -5
```

Expected: Clean working directory, all changes committed

- [ ] **Step 4: Create stage0-test.md documentation**

```bash
cat > docs/stage0-test.md << 'EOF'
# Stage 0 Verification Guide

## Backend Verification

### 1. Start Backend Server
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Test Health Endpoint
```bash
curl http://localhost:8000/api/health
```
Expected: `{"status":"ok","version":"0.1.0"}`

### 3. Verify Database
```bash
cd backend
sqlite3 expert_room.db ".tables"
```
Expected: 7 tables (providers, role_cards, rooms, room_participants, messages, shared_sources, artifacts)

### 4. Check Logs
Start server and verify structured log output with no sensitive data exposure.

## Frontend Verification

### 1. Start Frontend Server
```bash
cd frontend
npm run dev
```

### 2. Open Browser
Visit http://localhost:5173

### 3. Verify Features
- [ ] Page loads with "专家团" heading
- [ ] Navigation links work
- [ ] Backend connection status shows "✅ 后端连接成功"
- [ ] No CORS errors in browser console

## Integration Verification

### 1. Start Both Services
Terminal 1: `cd backend && uvicorn app.main:app --reload`
Terminal 2: `cd frontend && npm run dev`

### 2. Test API Proxy
```bash
curl http://localhost:5173/api/health
```
Expected: `{"status":"ok","version":"0.1.0"}`

### 3. Verify CORS
- No CORS errors in browser console
- API calls succeed through frontend proxy

## Git Verification

### 1. Check Commit History
```bash
git log --oneline
```
Expected: Multiple commits for each task

### 2. Verify Clean State
```bash
git status
```
Expected: Clean working directory

## Troubleshooting

### Backend won't start
- Check Python version (3.11+ required)
- Verify virtual environment is activated
- Check port 8000 is not in use

### Frontend won't start
- Check Node.js version (18+ required)
- Run `npm install` to ensure dependencies are installed
- Check port 5173 is not in use

### CORS errors
- Ensure backend is running on port 8000
- Check Vite proxy configuration in vite.config.ts
- Verify CORS_ORIGINS in backend .env file

### Database errors
- Run `alembic upgrade head` to apply migrations
- Check expert_room.db file exists in backend directory
EOF
```

- [ ] **Step 5: Final commit**

```bash
git add docs/
git commit -m "docs: add Stage 0 verification guide

- Add comprehensive verification steps for backend and frontend
- Include integration testing procedures
- Add troubleshooting section for common issues"
```

---

## Summary

This plan implements Stage 0 of the Expert Room project:

1. ✅ Python FastAPI backend with all dependencies
2. ✅ SQLAlchemy + Alembic + SQLite database setup
3. ✅ 7 database tables with proper relationships
4. ✅ Structured logging with sensitive data masking
5. ✅ Environment configuration with pydantic-settings
6. ✅ React + TypeScript + Vite frontend
7. ✅ Tailwind CSS + React Router + Zustand
8. ✅ Frontend-backend connectivity verification

**Next Stage:** Stage 1 - Provider Management + Role Card Management
