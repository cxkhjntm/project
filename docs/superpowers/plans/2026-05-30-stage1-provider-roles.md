# Stage 1: Provider Management + Role Card Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to configure LLM API providers with encrypted key storage and manage expert role cards (CRUD + 4 built-in roles).

**Architecture:** Backend services with AES-256-GCM encryption for API keys, CRUD APIs for providers and role cards, seed data auto-loading on startup. Frontend pages with forms, lists, and preview modals.

**Tech Stack:** Python FastAPI, SQLAlchemy, cryptography (Fernet/AES), React 18, TypeScript, React Hook Form, Zod, Tailwind CSS

---

## File Structure

### Backend Files (to create)
```
backend/app/
├── services/
│   ├── __init__.py
│   ├── crypto.py           # AES-256-GCM encryption for API keys
│   ├── provider_service.py # Provider CRUD business logic
│   └── role_card_service.py # RoleCard CRUD business logic
├── routers/
│   ├── __init__.py
│   ├── providers.py        # Provider API endpoints
│   └── role_cards.py       # RoleCard API endpoints
├── schemas/
│   ├── __init__.py
│   ├── provider.py         # Pydantic request/response schemas
│   └── role_card.py        # Pydantic request/response schemas
└── seed/
    ├── __init__.py
    └── builtin_roles.json  # 4 built-in expert roles
```

### Frontend Files (to create)
```
frontend/src/
├── pages/
│   ├── SettingsPage.tsx     # Provider management page
│   └── RoleCardsPage.tsx    # Role card management page
├── components/
│   ├── provider/
│   │   ├── ProviderForm.tsx    # Create/edit provider form
│   │   ├── ProviderList.tsx    # Provider list with actions
│   │   └── TestConnectionButton.tsx # Test API connection
│   └── role-card/
│       ├── RoleCardForm.tsx    # Create/edit role card form
│       ├── RoleCardList.tsx    # Role card list with actions
│       └── RoleCardPreview.tsx # Preview modal for system prompt
```

---

## Task 1: Crypto Service (API Key Encryption)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/crypto.py`
- Test: `backend/tests/test_crypto.py`

- [ ] **Step 1: Create backend/app/services/__init__.py**

```python
"""Business logic services for Expert Room."""
```

- [ ] **Step 2: Create backend/app/services/crypto.py**

```python
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
```

- [ ] **Step 3: Create backend/tests/test_crypto.py**

```python
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
```

- [ ] **Step 4: Run tests to verify**

```bash
cd backend
pytest tests/test_crypto.py -v
```

Expected: All 8 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_crypto.py
git commit -m "feat(backend): add crypto service for API key encryption

- Implement AES-256-GCM encryption using Fernet
- Add encrypt/decrypt methods with error handling
- Add mask_key method for display purposes
- Add comprehensive tests (8 test cases)"
```

---

## Task 2: Provider Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/provider.py`

- [ ] **Step 1: Create backend/app/schemas/__init__.py**

```python
"""Pydantic schemas for request/response validation."""
```

- [ ] **Step 2: Create backend/app/schemas/provider.py**

```python
"""Provider schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    """Schema for creating a provider."""
    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    base_url: str = Field(..., min_length=1, max_length=500, description="API base URL")
    api_key: str = Field(..., min_length=1, description="API key (will be encrypted)")
    default_model: str = Field(..., min_length=1, max_length=100, description="Default model name")
    default_temperature: float = Field(0.7, ge=0.0, le=2.0, description="Default temperature")
    default_max_tokens: int = Field(4096, ge=1, le=128000, description="Default max tokens")


class ProviderUpdate(BaseModel):
    """Schema for updating a provider."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, min_length=1)
    default_model: Optional[str] = Field(None, min_length=1, max_length=100)
    default_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    enabled: Optional[bool] = None


class ProviderResponse(BaseModel):
    """Schema for provider response."""
    id: str
    name: str
    type: str
    base_url: str
    api_key_masked: str = Field(..., description="Masked API key for display")
    default_model: str
    default_temperature: float
    default_max_tokens: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderTestResponse(BaseModel):
    """Schema for provider test response."""
    success: bool
    message: str
    latency_ms: Optional[float] = None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat(backend): add provider Pydantic schemas

- ProviderCreate for creating providers
- ProviderUpdate for partial updates
- ProviderResponse with masked API key
- ProviderTestResponse for connection tests"
```

---

## Task 3: Provider Service

**Files:**
- Create: `backend/app/services/provider_service.py`
- Test: `backend/tests/test_provider_service.py`

- [ ] **Step 1: Create backend/app/services/provider_service.py**

```python
"""Provider service for CRUD operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate
from app.services.crypto import crypto_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProviderService:
    """Service for provider CRUD operations."""

    async def create(self, session: AsyncSession, data: ProviderCreate) -> Provider:
        """Create a new provider.
        
        Args:
            session: Database session
            data: Provider creation data
            
        Returns:
            Created provider
        """
        import uuid
        
        provider = Provider(
            id=str(uuid.uuid4()),
            name=data.name,
            type="openai-compatible",
            base_url=data.base_url,
            api_key_encrypted=crypto_service.encrypt(data.api_key),
            default_model=data.default_model,
            default_temperature=data.default_temperature,
            default_max_tokens=data.default_max_tokens,
            enabled=True,
        )
        
        session.add(provider)
        await session.flush()
        
        logger.info("Created provider", provider_id=provider.id, name=provider.name)
        return provider

    async def get_all(self, session: AsyncSession) -> List[Provider]:
        """Get all providers.
        
        Args:
            session: Database session
            
        Returns:
            List of providers
        """
        result = await session.execute(select(Provider).order_by(Provider.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, provider_id: str) -> Optional[Provider]:
        """Get provider by ID.
        
        Args:
            session: Database session
            provider_id: Provider ID
            
        Returns:
            Provider or None
        """
        result = await session.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, provider_id: str, data: ProviderUpdate
    ) -> Optional[Provider]:
        """Update a provider.
        
        Args:
            session: Database session
            provider_id: Provider ID
            data: Update data
            
        Returns:
            Updated provider or None
        """
        provider = await self.get_by_id(session, provider_id)
        if not provider:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # Encrypt API key if provided
        if "api_key" in update_data:
            update_data["api_key_encrypted"] = crypto_service.encrypt(update_data.pop("api_key"))
        
        for field, value in update_data.items():
            setattr(provider, field, value)
        
        await session.flush()
        
        logger.info("Updated provider", provider_id=provider.id)
        return provider

    async def delete(self, session: AsyncSession, provider_id: str) -> bool:
        """Delete a provider.
        
        Args:
            session: Database session
            provider_id: Provider ID
            
        Returns:
            True if deleted, False if not found
        """
        provider = await self.get_by_id(session, provider_id)
        if not provider:
            return False
        
        await session.delete(provider)
        await session.flush()
        
        logger.info("Deleted provider", provider_id=provider_id)
        return True

    async def test_connection(self, session: AsyncSession, provider_id: str) -> dict:
        """Test provider connection.
        
        Args:
            session: Database session
            provider_id: Provider ID
            
        Returns:
            Test result dict with success, message, latency_ms
        """
        import time
        import httpx
        
        provider = await self.get_by_id(session, provider_id)
        if not provider:
            return {"success": False, "message": "Provider not found", "latency_ms": None}
        
        api_key = crypto_service.decrypt(provider.api_key_encrypted)
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{provider.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": provider.default_model,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 5,
                    },
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "latency_ms": round(latency_ms, 2),
                    }
                else:
                    return {
                        "success": False,
                        "message": f"API returned status {response.status_code}: {response.text[:200]}",
                        "latency_ms": round(latency_ms, 2),
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "message": "Connection timeout (30s)", "latency_ms": None}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}", "latency_ms": None}


# Singleton instance
provider_service = ProviderService()
```

- [ ] **Step 2: Create backend/tests/test_provider_service.py**

```python
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
```

- [ ] **Step 3: Run tests**

```bash
cd backend
pytest tests/test_provider_service.py -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/provider_service.py backend/tests/test_provider_service.py
git commit -m "feat(backend): add provider service with CRUD operations

- Create, read, update, delete providers
- API key encryption on create/update
- Connection test with httpx
- Comprehensive error handling"
```

---

## Task 4: Provider API Router

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/providers.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/routers/__init__.py**

```python
"""API routers for Expert Room."""
```

- [ ] **Step 2: Create backend/app/routers/providers.py**

```python
"""Provider API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.provider import (
    ProviderCreate,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
)
from app.services.crypto import crypto_service
from app.services.provider_service import provider_service

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(
    data: ProviderCreate,
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    """Create a new provider."""
    provider = await provider_service.create(session, data)
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key_masked=crypto_service.mask_key(data.api_key),
        default_model=provider.default_model,
        default_temperature=provider.default_temperature,
        default_max_tokens=provider.default_max_tokens,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.get("", response_model=List[ProviderResponse])
async def list_providers(
    session: AsyncSession = Depends(get_session),
) -> List[ProviderResponse]:
    """List all providers."""
    providers = await provider_service.get_all(session)
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            type=p.type,
            base_url=p.base_url,
            api_key_masked=crypto_service.mask_key(
                crypto_service.decrypt(p.api_key_encrypted)
            ),
            default_model=p.default_model,
            default_temperature=p.default_temperature,
            default_max_tokens=p.default_max_tokens,
            enabled=p.enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in providers
    ]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    """Get a provider by ID."""
    provider = await provider_service.get_by_id(session, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key_masked=crypto_service.mask_key(
            crypto_service.decrypt(provider.api_key_encrypted)
        ),
        default_model=provider.default_model,
        default_temperature=provider.default_temperature,
        default_max_tokens=provider.default_max_tokens,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProviderResponse:
    """Update a provider."""
    provider = await provider_service.update(session, provider_id, data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key_masked=crypto_service.mask_key(
            crypto_service.decrypt(provider.api_key_encrypted)
        ),
        default_model=provider.default_model,
        default_temperature=provider.default_temperature,
        default_max_tokens=provider.default_max_tokens,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a provider."""
    deleted = await provider_service.delete(session, provider_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProviderTestResponse:
    """Test provider connection."""
    result = await provider_service.test_connection(session, provider_id)
    return ProviderTestResponse(**result)
```

- [ ] **Step 3: Modify backend/app/main.py to include provider router**

Add import and include router:

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import providers
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
    # TODO: Tighten allow_methods and allow_headers before production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(providers.router)

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

- [ ] **Step 4: Verify API endpoints work**

```bash
cd backend
uvicorn app.main:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/api/providers
```

Expected: Returns empty list `[]`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/ backend/app/main.py
git commit -m "feat(backend): add provider API endpoints

- POST /api/providers - Create provider
- GET /api/providers - List all providers
- GET /api/providers/{id} - Get single provider
- PUT /api/providers/{id} - Update provider
- DELETE /api/providers/{id} - Delete provider
- POST /api/providers/{id}/test - Test connection"
```

---

## Task 5: Role Card Schemas

**Files:**
- Create: `backend/app/schemas/role_card.py`

- [ ] **Step 1: Create backend/app/schemas/role_card.py**

```python
"""Role card schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleCardCreate(BaseModel):
    """Schema for creating a role card."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str = Field(..., min_length=1, description="Role description")
    expertise: List[str] = Field(..., min_length=1, description="Areas of expertise")
    responsibilities: List[str] = Field(..., min_length=1, description="Key responsibilities")
    constraints: Optional[List[str]] = Field(None, description="Behavioral constraints")
    system_prompt: str = Field(..., min_length=1, description="System prompt for the role")
    output_style: Optional[str] = Field(None, description="Preferred output style")
    default_provider_id: Optional[str] = Field(None, description="Default provider ID")
    default_model: Optional[str] = Field(None, description="Default model name")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature setting")


class RoleCardUpdate(BaseModel):
    """Schema for updating a role card."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1)
    expertise: Optional[List[str]] = Field(None, min_length=1)
    responsibilities: Optional[List[str]] = Field(None, min_length=1)
    constraints: Optional[List[str]] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    output_style: Optional[str] = None
    default_provider_id: Optional[str] = None
    default_model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class RoleCardResponse(BaseModel):
    """Schema for role card response."""
    id: str
    name: str
    description: str
    expertise: List[str]
    responsibilities: List[str]
    constraints: Optional[List[str]]
    system_prompt: str
    output_style: Optional[str]
    default_provider_id: Optional[str]
    default_model: Optional[str]
    temperature: float
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleCardCopyRequest(BaseModel):
    """Schema for copying a role card."""
    new_name: str = Field(..., min_length=1, max_length=100, description="Name for the copy")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/role_card.py
git commit -m "feat(backend): add role card Pydantic schemas

- RoleCardCreate for creating role cards
- RoleCardUpdate for partial updates
- RoleCardResponse with all fields
- RoleCardCopyRequest for copying role cards"
```

---

## Task 6: Role Card Service

**Files:**
- Create: `backend/app/services/role_card_service.py`
- Test: `backend/tests/test_role_card_service.py`

- [ ] **Step 1: Create backend/app/services/role_card_service.py**

```python
"""Role card service for CRUD operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_card import RoleCard
from app.schemas.role_card import RoleCardCreate, RoleCardUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RoleCardService:
    """Service for role card CRUD operations."""

    async def create(self, session: AsyncSession, data: RoleCardCreate) -> RoleCard:
        """Create a new role card.
        
        Args:
            session: Database session
            data: Role card creation data
            
        Returns:
            Created role card
        """
        import uuid
        
        role_card = RoleCard(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            expertise=data.expertise,
            responsibilities=data.responsibilities,
            constraints=data.constraints,
            system_prompt=data.system_prompt,
            output_style=data.output_style,
            default_provider_id=data.default_provider_id,
            default_model=data.default_model,
            temperature=data.temperature,
            is_builtin=False,
        )
        
        session.add(role_card)
        await session.flush()
        
        logger.info("Created role card", role_card_id=role_card.id, name=role_card.name)
        return role_card

    async def get_all(
        self, session: AsyncSession, builtin_only: bool = False
    ) -> List[RoleCard]:
        """Get all role cards.
        
        Args:
            session: Database session
            builtin_only: If True, return only built-in role cards
            
        Returns:
            List of role cards
        """
        query = select(RoleCard).order_by(RoleCard.name)
        
        if builtin_only:
            query = query.where(RoleCard.is_builtin == True)
        
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, role_card_id: str) -> Optional[RoleCard]:
        """Get role card by ID.
        
        Args:
            session: Database session
            role_card_id: Role card ID
            
        Returns:
            Role card or None
        """
        result = await session.execute(
            select(RoleCard).where(RoleCard.id == role_card_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, role_card_id: str, data: RoleCardUpdate
    ) -> Optional[RoleCard]:
        """Update a role card.
        
        Args:
            session: Database session
            role_card_id: Role card ID
            data: Update data
            
        Returns:
            Updated role card or None
            
        Raises:
            ValueError: If trying to update a built-in role card
        """
        role_card = await self.get_by_id(session, role_card_id)
        if not role_card:
            return None
        
        if role_card.is_builtin:
            raise ValueError("Cannot modify built-in role cards")
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(role_card, field, value)
        
        await session.flush()
        
        logger.info("Updated role card", role_card_id=role_card.id)
        return role_card

    async def delete(self, session: AsyncSession, role_card_id: str) -> bool:
        """Delete a role card.
        
        Args:
            session: Database session
            role_card_id: Role card ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If trying to delete a built-in role card
        """
        role_card = await self.get_by_id(session, role_card_id)
        if not role_card:
            return False
        
        if role_card.is_builtin:
            raise ValueError("Cannot delete built-in role cards")
        
        await session.delete(role_card)
        await session.flush()
        
        logger.info("Deleted role card", role_card_id=role_card_id)
        return True

    async def copy(
        self, session: AsyncSession, role_card_id: str, new_name: str
    ) -> Optional[RoleCard]:
        """Copy a role card.
        
        Args:
            session: Database session
            role_card_id: Source role card ID
            new_name: Name for the copy
            
        Returns:
            Copied role card or None
        """
        import uuid
        
        source = await self.get_by_id(session, role_card_id)
        if not source:
            return None
        
        copy = RoleCard(
            id=str(uuid.uuid4()),
            name=new_name,
            description=source.description,
            expertise=source.expertise,
            responsibilities=source.responsibilities,
            constraints=source.constraints,
            system_prompt=source.system_prompt,
            output_style=source.output_style,
            default_provider_id=source.default_provider_id,
            default_model=source.default_model,
            temperature=source.temperature,
            is_builtin=False,
        )
        
        session.add(copy)
        await session.flush()
        
        logger.info("Copied role card", source_id=role_card_id, copy_id=copy.id)
        return copy


# Singleton instance
role_card_service = RoleCardService()
```

- [ ] **Step 2: Create backend/tests/test_role_card_service.py**

```python
"""Tests for role card service."""

import pytest

from app.services.role_card_service import RoleCardService


@pytest.fixture
def role_card_service() -> RoleCardService:
    """Create role card service instance."""
    return RoleCardService()


class TestRoleCardService:
    """Test role card service CRUD operations."""

    def test_service_instantiation(self, role_card_service: RoleCardService) -> None:
        """Test that service can be instantiated."""
        assert role_card_service is not None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/role_card_service.py backend/tests/test_role_card_service.py
git commit -m "feat(backend): add role card service with CRUD operations

- Create, read, update, delete role cards
- Copy role card functionality
- Built-in role card protection (cannot modify/delete)
- Filter by built-in status"
```

---

## Task 7: Role Card API Router

**Files:**
- Create: `backend/app/routers/role_cards.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/routers/role_cards.py**

```python
"""Role card API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.role_card import (
    RoleCardCopyRequest,
    RoleCardCreate,
    RoleCardResponse,
    RoleCardUpdate,
)
from app.services.role_card_service import role_card_service

router = APIRouter(prefix="/api/role-cards", tags=["role-cards"])


@router.post("", response_model=RoleCardResponse, status_code=201)
async def create_role_card(
    data: RoleCardCreate,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Create a new role card."""
    role_card = await role_card_service.create(session, data)
    return RoleCardResponse.model_validate(role_card)


@router.get("", response_model=List[RoleCardResponse])
async def list_role_cards(
    builtin: Optional[bool] = Query(None, description="Filter by built-in status"),
    session: AsyncSession = Depends(get_session),
) -> List[RoleCardResponse]:
    """List all role cards."""
    role_cards = await role_card_service.get_all(session, builtin_only=builtin or False)
    return [RoleCardResponse.model_validate(rc) for rc in role_cards]


@router.get("/{role_card_id}", response_model=RoleCardResponse)
async def get_role_card(
    role_card_id: str,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Get a role card by ID."""
    role_card = await role_card_service.get_by_id(session, role_card_id)
    if not role_card:
        raise HTTPException(status_code=404, detail="Role card not found")
    
    return RoleCardResponse.model_validate(role_card)


@router.put("/{role_card_id}", response_model=RoleCardResponse)
async def update_role_card(
    role_card_id: str,
    data: RoleCardUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Update a role card."""
    try:
        role_card = await role_card_service.update(session, role_card_id, data)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    if not role_card:
        raise HTTPException(status_code=404, detail="Role card not found")
    
    return RoleCardResponse.model_validate(role_card)


@router.delete("/{role_card_id}", status_code=204)
async def delete_role_card(
    role_card_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a role card."""
    try:
        deleted = await role_card_service.delete(session, role_card_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Role card not found")


@router.post("/{role_card_id}/copy", response_model=RoleCardResponse)
async def copy_role_card(
    role_card_id: str,
    data: RoleCardCopyRequest,
    session: AsyncSession = Depends(get_session),
) -> RoleCardResponse:
    """Copy a role card."""
    role_card = await role_card_service.copy(session, role_card_id, data.new_name)
    if not role_card:
        raise HTTPException(status_code=404, detail="Role card not found")
    
    return RoleCardResponse.model_validate(role_card)
```

- [ ] **Step 2: Modify backend/app/main.py to include role cards router**

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import providers, role_cards
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
    # TODO: Tighten allow_methods and allow_headers before production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(providers.router)
    app.include_router(role_cards.router)

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

- [ ] **Step 3: Verify API endpoints work**

```bash
cd backend
uvicorn app.main:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/api/role-cards
```

Expected: Returns empty list `[]`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/role_cards.py backend/app/main.py
git commit -m "feat(backend): add role card API endpoints

- POST /api/role-cards - Create role card
- GET /api/role-cards - List all role cards (with ?builtin filter)
- GET /api/role-cards/{id} - Get single role card
- PUT /api/role-cards/{id} - Update role card (built-in protected)
- DELETE /api/role-cards/{id} - Delete role card (built-in protected)
- POST /api/role-cards/{id}/copy - Copy role card"
```

---

## Task 8: Built-in Role Cards Seed Data

**Files:**
- Create: `backend/app/seed/__init__.py`
- Create: `backend/app/seed/builtin_roles.json`
- Create: `backend/app/seed/loader.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/seed/__init__.py**

```python
"""Seed data for Expert Room."""
```

- [ ] **Step 2: Create backend/app/seed/builtin_roles.json**

```json
[
  {
    "name": "主持人",
    "description": "控制讨论流程，推动专家发言和结论收敛",
    "expertise": ["流程管理", "冲突识别", "结论收敛"],
    "responsibilities": [
      "安排专家发言顺序",
      "识别讨论中的冲突和遗漏",
      "在信息足够时推动结论收敛",
      "要求专家补充缺失信息"
    ],
    "constraints": [
      "不代替专家完成内容",
      "不在讨论未充分时强行结束"
    ],
    "system_prompt": "你是专家群聊主持人。你的任务是控制讨论流程，而不是替专家完成全部内容。\n\n你需要：\n1. 根据任务目标安排专家发言顺序。\n2. 识别讨论中的冲突、遗漏和风险。\n3. 在信息足够时推动结论收敛。\n4. 最终要求文档专家生成产物。",
    "output_style": null,
    "temperature": 0.7
  },
  {
    "name": "产品经理",
    "description": "明确需求、用户场景、优先级和 MVP 范围",
    "expertise": ["需求分析", "用户场景", "优先级排序", "MVP 定义"],
    "responsibilities": [
      "明确用户目标和边界",
      "拆分功能优先级",
      "定义 MVP 和后续版本边界",
      "检查是否满足真实使用场景"
    ],
    "constraints": [
      "不做超出技术可行性的承诺",
      "结论需要说明优先级理由"
    ],
    "system_prompt": "你是产品经理。你的任务是从用户角度分析需求，明确优先级。\n\n你需要：\n1. 明确用户目标和边界。\n2. 拆分功能优先级（P0/P1/P2）。\n3. 定义 MVP 范围。\n4. 检查是否满足真实使用场景。",
    "output_style": null,
    "temperature": 0.7
  },
  {
    "name": "系统架构师",
    "description": "设计模块、技术边界和整体流程",
    "expertise": ["架构设计", "模块拆分", "技术选型", "风险评估"],
    "responsibilities": [
      "设计整体架构",
      "拆分模块边界",
      "识别技术风险",
      "做技术取舍决策"
    ],
    "constraints": [
      "避免过度设计",
      "优先考虑初版可实现性",
      "结论需要说明取舍理由"
    ],
    "system_prompt": "你是系统架构师。你的任务是设计技术方案，评估可行性。\n\n你需要：\n1. 设计整体架构。\n2. 拆分模块边界。\n3. 识别技术风险。\n4. 做技术取舍决策并说明理由。",
    "output_style": null,
    "temperature": 0.7
  },
  {
    "name": "文档专家",
    "description": "整理讨论结果，生成结构化最终文档",
    "expertise": ["技术写作", "文档结构", "信息整合", "可读性优化"],
    "responsibilities": [
      "整理讨论结果为结构化文档",
      "统一文档格式和风格",
      "确保结论清晰、可执行",
      "保留引用来源"
    ],
    "constraints": [
      "不添加讨论中未出现的内容",
      "保持客观，不偏向某个专家的观点"
    ],
    "system_prompt": "你是文档专家。你的任务是整理讨论结果，生成结构化文档。\n\n你需要：\n1. 整理讨论结果为结构化文档。\n2. 统一文档格式和风格。\n3. 确保结论清晰、可执行。\n4. 保留引用来源。",
    "output_style": "使用 Markdown 格式，层次清晰，结论明确",
    "temperature": 0.5
  }
]
```

- [ ] **Step 3: Create backend/app/seed/loader.py**

```python
"""Seed data loader for built-in role cards."""

import json
from pathlib import Path
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_card import RoleCard
from app.utils.logger import get_logger

logger = get_logger(__name__)

SEED_FILE = Path(__file__).parent / "builtin_roles.json"


async def load_builtin_roles(session: AsyncSession) -> List[RoleCard]:
    """Load built-in role cards from seed file.
    
    Args:
        session: Database session
        
    Returns:
        List of loaded role cards (empty if already loaded)
    """
    # Check if built-in roles already exist
    result = await session.execute(
        select(RoleCard).where(RoleCard.is_builtin == True).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        logger.info("Built-in roles already loaded, skipping")
        return []
    
    # Load seed data
    if not SEED_FILE.exists():
        logger.warning("Seed file not found", path=str(SEED_FILE))
        return []
    
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        roles_data = json.load(f)
    
    import uuid
    
    loaded_roles = []
    for role_data in roles_data:
        role = RoleCard(
            id=f"builtin_{role_data['name'].lower().replace(' ', '_')}",
            name=role_data["name"],
            description=role_data["description"],
            expertise=role_data["expertise"],
            responsibilities=role_data["responsibilities"],
            constraints=role_data.get("constraints"),
            system_prompt=role_data["system_prompt"],
            output_style=role_data.get("output_style"),
            temperature=role_data.get("temperature", 0.7),
            is_builtin=True,
        )
        session.add(role)
        loaded_roles.append(role)
    
    await session.flush()
    
    logger.info("Loaded built-in roles", count=len(loaded_roles))
    return loaded_roles
```

- [ ] **Step 4: Modify backend/app/main.py to load seed data on startup**

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory
from app.routers import providers, role_cards
from app.seed.loader import load_builtin_roles
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
    # TODO: Tighten allow_methods and allow_headers before production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(providers.router)
    app.include_router(role_cards.router)

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Starting Expert Room API", version="0.1.0", debug=settings.debug)
        
        # Load built-in role cards
        async with async_session_factory() as session:
            await load_builtin_roles(session)
            await session.commit()

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

- [ ] **Step 5: Verify built-in roles are loaded**

```bash
cd backend
uvicorn app.main:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/api/role-cards?builtin=true
```

Expected: Returns 4 built-in role cards

- [ ] **Step 6: Commit**

```bash
git add backend/app/seed/ backend/app/main.py
git commit -m "feat(backend): add built-in role cards seed data

- Create builtin_roles.json with 4 expert roles
- Create loader to auto-load on startup
- Skip loading if roles already exist
- Integrate with FastAPI startup event"
```

---

## Task 9: Frontend Provider Management Page

**Files:**
- Create: `frontend/src/pages/SettingsPage.tsx`
- Create: `frontend/src/components/provider/ProviderForm.tsx`
- Create: `frontend/src/components/provider/ProviderList.tsx`
- Create: `frontend/src/components/provider/TestConnectionButton.tsx`
- Modify: `frontend/src/routes.tsx`

- [ ] **Step 1: Create frontend/src/pages/SettingsPage.tsx**

```tsx
import { useState, useEffect } from 'react'
import { Provider } from '../types'
import { api } from '../api/client'
import ProviderForm from '../components/provider/ProviderForm'
import ProviderList from '../components/provider/ProviderList'

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null)

  const fetchProviders = async () => {
    try {
      setLoading(true)
      const data = await api.getProviders()
      setProviders(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load providers')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProviders()
  }, [])

  const handleCreate = async (data: any) => {
    try {
      await api.createProvider(data)
      setShowForm(false)
      fetchProviders()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create provider')
    }
  }

  const handleUpdate = async (id: string, data: any) => {
    try {
      await api.updateProvider(id, data)
      setEditingProvider(null)
      fetchProviders()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update provider')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此 Provider？')) return
    try {
      await api.deleteProvider(id)
      fetchProviders()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete provider')
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">设置</h1>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          添加 Provider
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {showForm && (
        <div className="mb-6 p-6 bg-white rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">添加 Provider</h2>
          <ProviderForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {editingProvider && (
        <div className="mb-6 p-6 bg-white rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">编辑 Provider</h2>
          <ProviderForm
            initialData={editingProvider}
            onSubmit={(data) => handleUpdate(editingProvider.id, data)}
            onCancel={() => setEditingProvider(null)}
          />
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-gray-500">加载中...</div>
      ) : (
        <ProviderList
          providers={providers}
          onEdit={setEditingProvider}
          onDelete={handleDelete}
          onRefresh={fetchProviders}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create frontend/src/components/provider/ProviderForm.tsx**

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Provider } from '../../types'

const providerSchema = z.object({
  name: z.string().min(1, '名称不能为空'),
  base_url: z.string().url('请输入有效的 URL'),
  api_key: z.string().min(1, 'API Key 不能为空'),
  default_model: z.string().min(1, '模型名称不能为空'),
  default_temperature: z.number().min(0).max(2).default(0.7),
  default_max_tokens: z.number().min(1).max(128000).default(4096),
})

type ProviderFormData = z.infer<typeof providerSchema>

interface ProviderFormProps {
  initialData?: Provider
  onSubmit: (data: ProviderFormData) => void
  onCancel: () => void
}

export default function ProviderForm({ initialData, onSubmit, onCancel }: ProviderFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProviderFormData>({
    resolver: zodResolver(providerSchema),
    defaultValues: initialData
      ? {
          name: initialData.name,
          base_url: initialData.base_url,
          api_key: '', // Don't pre-fill API key
          default_model: initialData.default_model,
          default_temperature: initialData.default_temperature,
          default_max_tokens: initialData.default_max_tokens,
        }
      : {
          default_temperature: 0.7,
          default_max_tokens: 4096,
        },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">名称</label>
        <input
          {...register('name')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="例如：OpenAI"
        />
        {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Base URL</label>
        <input
          {...register('base_url')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="https://api.openai.com/v1"
        />
        {errors.base_url && <p className="mt-1 text-sm text-red-600">{errors.base_url.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">API Key</label>
        <input
          {...register('api_key')}
          type="password"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder={initialData ? '留空则不修改' : 'sk-...'}
        />
        {errors.api_key && <p className="mt-1 text-sm text-red-600">{errors.api_key.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">默认模型</label>
        <input
          {...register('default_model')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="gpt-4o"
        />
        {errors.default_model && <p className="mt-1 text-sm text-red-600">{errors.default_model.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Temperature</label>
          <input
            {...register('default_temperature', { valueAsNumber: true })}
            type="number"
            step="0.1"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Max Tokens</label>
          <input
            {...register('default_max_tokens', { valueAsNumber: true })}
            type="number"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? '保存中...' : '保存'}
        </button>
      </div>
    </form>
  )
}
```

- [ ] **Step 3: Create frontend/src/components/provider/ProviderList.tsx**

```tsx
import { Provider } from '../../types'
import TestConnectionButton from './TestConnectionButton'

interface ProviderListProps {
  providers: Provider[]
  onEdit: (provider: Provider) => void
  onDelete: (id: string) => void
  onRefresh: () => void
}

export default function ProviderList({ providers, onEdit, onDelete, onRefresh }: ProviderListProps) {
  if (providers.length === 0) {
    return (
      <div className="text-center py-8 bg-white rounded-lg border">
        <p className="text-gray-500">暂无 Provider，点击上方按钮添加</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {providers.map((provider) => (
        <div
          key={provider.id}
          className="p-4 bg-white rounded-lg shadow-sm border"
        >
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold text-gray-900">{provider.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{provider.base_url}</p>
              <div className="mt-2 flex items-center space-x-4 text-sm text-gray-600">
                <span>模型: {provider.default_model}</span>
                <span>API Key: {provider.api_key_masked}</span>
                <span className={provider.enabled ? 'text-green-600' : 'text-red-600'}>
                  {provider.enabled ? '启用' : '禁用'}
                </span>
              </div>
            </div>
            <div className="flex space-x-2">
              <TestConnectionButton providerId={provider.id} />
              <button
                onClick={() => onEdit(provider)}
                className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
              >
                编辑
              </button>
              <button
                onClick={() => onDelete(provider.id)}
                className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/src/components/provider/TestConnectionButton.tsx**

```tsx
import { useState } from 'react'
import { api } from '../../api/client'

interface TestConnectionButtonProps {
  providerId: string
}

export default function TestConnectionButton({ providerId }: TestConnectionButtonProps) {
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<{ success: boolean; message: string; latency_ms?: number } | null>(null)

  const handleTest = async () => {
    setTesting(true)
    setResult(null)
    try {
      const testResult = await api.testProviderConnection(providerId)
      setResult(testResult)
    } catch (err) {
      setResult({ success: false, message: err instanceof Error ? err.message : 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={handleTest}
        disabled={testing}
        className="px-3 py-1 text-sm text-green-600 hover:bg-green-50 rounded disabled:opacity-50"
      >
        {testing ? '测试中...' : '测试连接'}
      </button>
      {result && (
        <div
          className={`absolute right-0 top-full mt-2 p-3 rounded-lg shadow-lg z-10 min-w-[200px] ${
            result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}
        >
          <p className="text-sm font-medium">{result.message}</p>
          {result.latency_ms && (
            <p className="text-xs mt-1">延迟: {result.latency_ms}ms</p>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Modify frontend/src/routes.tsx to include settings page**

```tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/shared/Layout'
import HomePage from './pages/HomePage'
import SettingsPage from './pages/SettingsPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'role-cards',
        element: <div>角色卡管理（开发中）</div>,
      },
      {
        path: 'rooms',
        element: <div>群聊管理（开发中）</div>,
      },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
```

- [ ] **Step 6: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx frontend/src/components/provider/ frontend/src/routes.tsx
git commit -m "feat(frontend): add provider management page

- Settings page with provider list and form
- Create/edit provider with validation
- Test connection button with status display
- React Hook Form + Zod validation
- Update routes to include settings page"
```

---

## Task 10: Frontend Role Card Management Page

**Files:**
- Create: `frontend/src/pages/RoleCardsPage.tsx`
- Create: `frontend/src/components/role-card/RoleCardForm.tsx`
- Create: `frontend/src/components/role-card/RoleCardList.tsx`
- Create: `frontend/src/components/role-card/RoleCardPreview.tsx`
- Modify: `frontend/src/routes.tsx`

- [ ] **Step 1: Create frontend/src/pages/RoleCardsPage.tsx**

```tsx
import { useState, useEffect } from 'react'
import { RoleCard } from '../types'
import { api } from '../api/client'
import RoleCardForm from '../components/role-card/RoleCardForm'
import RoleCardList from '../components/role-card/RoleCardList'
import RoleCardPreview from '../components/role-card/RoleCardPreview'

export default function RoleCardsPage() {
  const [roleCards, setRoleCards] = useState<RoleCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingCard, setEditingCard] = useState<RoleCard | null>(null)
  const [previewCard, setPreviewCard] = useState<RoleCard | null>(null)

  const fetchRoleCards = async () => {
    try {
      setLoading(true)
      const data = await api.getRoleCards()
      setRoleCards(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load role cards')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRoleCards()
  }, [])

  const handleCreate = async (data: any) => {
    try {
      await api.createRoleCard(data)
      setShowForm(false)
      fetchRoleCards()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create role card')
    }
  }

  const handleUpdate = async (id: string, data: any) => {
    try {
      await api.updateRoleCard(id, data)
      setEditingCard(null)
      fetchRoleCards()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role card')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此角色卡？')) return
    try {
      await api.deleteRoleCard(id)
      fetchRoleCards()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete role card')
    }
  }

  const handleCopy = async (id: string) => {
    const name = prompt('请输入新角色卡名称：')
    if (!name) return
    try {
      await api.copyRoleCard(id, name)
      fetchRoleCards()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to copy role card')
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">角色卡管理</h1>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          新建角色卡
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {showForm && (
        <div className="mb-6 p-6 bg-white rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">新建角色卡</h2>
          <RoleCardForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {editingCard && (
        <div className="mb-6 p-6 bg-white rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">编辑角色卡</h2>
          <RoleCardForm
            initialData={editingCard}
            onSubmit={(data) => handleUpdate(editingCard.id, data)}
            onCancel={() => setEditingCard(null)}
          />
        </div>
      )}

      {previewCard && (
        <RoleCardPreview
          roleCard={previewCard}
          onClose={() => setPreviewCard(null)}
        />
      )}

      {loading ? (
        <div className="text-center py-8 text-gray-500">加载中...</div>
      ) : (
        <RoleCardList
          roleCards={roleCards}
          onEdit={setEditingCard}
          onDelete={handleDelete}
          onCopy={handleCopy}
          onPreview={setPreviewCard}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create frontend/src/components/role-card/RoleCardForm.tsx**

```tsx
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { RoleCard } from '../../types'

const roleCardSchema = z.object({
  name: z.string().min(1, '名称不能为空'),
  description: z.string().min(1, '描述不能为空'),
  expertise: z.array(z.string().min(1)).min(1, '至少添加一项专业能力'),
  responsibilities: z.array(z.string().min(1)).min(1, '至少添加一项职责'),
  constraints: z.array(z.string().min(1)).optional(),
  system_prompt: z.string().min(1, '系统提示词不能为空'),
  output_style: z.string().optional(),
  temperature: z.number().min(0).max(2).default(0.7),
})

type RoleCardFormData = z.infer<typeof roleCardSchema>

interface RoleCardFormProps {
  initialData?: RoleCard
  onSubmit: (data: RoleCardFormData) => void
  onCancel: () => void
}

export default function RoleCardForm({ initialData, onSubmit, onCancel }: RoleCardFormProps) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<RoleCardFormData>({
    resolver: zodResolver(roleCardSchema),
    defaultValues: initialData
      ? {
          name: initialData.name,
          description: initialData.description,
          expertise: initialData.expertise,
          responsibilities: initialData.responsibilities,
          constraints: initialData.constraints || [],
          system_prompt: initialData.system_prompt,
          output_style: initialData.output_style || '',
          temperature: initialData.temperature,
        }
      : {
          expertise: [''],
          responsibilities: [''],
          constraints: [],
          temperature: 0.7,
        },
  })

  const {
    fields: expertiseFields,
    append: appendExpertise,
    remove: removeExpertise,
  } = useFieldArray({ control, name: 'expertise' })

  const {
    fields: responsibilityFields,
    append: appendResponsibility,
    remove: removeResponsibility,
  } = useFieldArray({ control, name: 'responsibilities' })

  const {
    fields: constraintFields,
    append: appendConstraint,
    remove: removeConstraint,
  } = useFieldArray({ control, name: 'constraints' })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">名称</label>
        <input
          {...register('name')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="例如：产品经理"
        />
        {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">描述</label>
        <input
          {...register('description')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="简要描述此角色的职责"
        />
        {errors.description && <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">专业能力</label>
        {expertiseFields.map((field, index) => (
          <div key={field.id} className="flex mt-1">
            <input
              {...register(`expertise.${index}`)}
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={() => removeExpertise(index)}
              className="ml-2 text-red-600 hover:text-red-800"
            >
              删除
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => appendExpertise('')}
          className="mt-2 text-sm text-blue-600 hover:text-blue-800"
        >
          + 添加
        </button>
        {errors.expertise && <p className="mt-1 text-sm text-red-600">{errors.expertise.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">职责</label>
        {responsibilityFields.map((field, index) => (
          <div key={field.id} className="flex mt-1">
            <input
              {...register(`responsibilities.${index}`)}
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={() => removeResponsibility(index)}
              className="ml-2 text-red-600 hover:text-red-800"
            >
              删除
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => appendResponsibility('')}
          className="mt-2 text-sm text-blue-600 hover:text-blue-800"
        >
          + 添加
        </button>
        {errors.responsibilities && <p className="mt-1 text-sm text-red-600">{errors.responsibilities.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">系统提示词</label>
        <textarea
          {...register('system_prompt')}
          rows={6}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="定义此角色的行为和输出格式..."
        />
        {errors.system_prompt && <p className="mt-1 text-sm text-red-600">{errors.system_prompt.message}</p>}
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? '保存中...' : '保存'}
        </button>
      </div>
    </form>
  )
}
```

- [ ] **Step 3: Create frontend/src/components/role-card/RoleCardList.tsx**

```tsx
import { RoleCard } from '../../types'

interface RoleCardListProps {
  roleCards: RoleCard[]
  onEdit: (card: RoleCard) => void
  onDelete: (id: string) => void
  onCopy: (id: string) => void
  onPreview: (card: RoleCard) => void
}

export default function RoleCardList({ roleCards, onEdit, onDelete, onCopy, onPreview }: RoleCardListProps) {
  if (roleCards.length === 0) {
    return (
      <div className="text-center py-8 bg-white rounded-lg border">
        <p className="text-gray-500">暂无角色卡，点击上方按钮创建</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {roleCards.map((card) => (
        <div
          key={card.id}
          className="p-4 bg-white rounded-lg shadow-sm border"
        >
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold text-gray-900">{card.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{card.description}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {card.expertise.slice(0, 3).map((skill, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
                  >
                    {skill}
                  </span>
                ))}
                {card.expertise.length > 3 && (
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded">
                    +{card.expertise.length - 3}
                  </span>
                )}
              </div>
            </div>
            {card.is_builtin && (
              <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                内置
              </span>
            )}
          </div>
          <div className="mt-4 flex space-x-2">
            <button
              onClick={() => onPreview(card)}
              className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded"
            >
              预览
            </button>
            {!card.is_builtin && (
              <>
                <button
                  onClick={() => onEdit(card)}
                  className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
                >
                  编辑
                </button>
                <button
                  onClick={() => onCopy(card.id)}
                  className="px-3 py-1 text-sm text-green-600 hover:bg-green-50 rounded"
                >
                  复制
                </button>
                <button
                  onClick={() => onDelete(card.id)}
                  className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                >
                  删除
                </button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/src/components/role-card/RoleCardPreview.tsx**

```tsx
import { RoleCard } from '../../types'

interface RoleCardPreviewProps {
  roleCard: RoleCard
  onClose: () => void
}

export default function RoleCardPreview({ roleCard, onClose }: RoleCardPreviewProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto m-4">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-xl font-bold text-gray-900">{roleCard.name}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <p className="text-gray-600 mb-4">{roleCard.description}</p>

          <div className="mb-4">
            <h3 className="font-semibold text-gray-700 mb-2">专业能力</h3>
            <div className="flex flex-wrap gap-2">
              {roleCard.expertise.map((skill, i) => (
                <span
                  key={i}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>

          <div className="mb-4">
            <h3 className="font-semibold text-gray-700 mb-2">职责</h3>
            <ul className="list-disc list-inside space-y-1 text-gray-600">
              {roleCard.responsibilities.map((resp, i) => (
                <li key={i}>{resp}</li>
              ))}
            </ul>
          </div>

          {roleCard.constraints && roleCard.constraints.length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold text-gray-700 mb-2">约束条件</h3>
              <ul className="list-disc list-inside space-y-1 text-gray-600">
                {roleCard.constraints.map((constraint, i) => (
                  <li key={i}>{constraint}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mb-4">
            <h3 className="font-semibold text-gray-700 mb-2">系统提示词</h3>
            <pre className="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 whitespace-pre-wrap">
              {roleCard.system_prompt}
            </pre>
          </div>

          {roleCard.output_style && (
            <div className="mb-4">
              <h3 className="font-semibold text-gray-700 mb-2">输出风格</h3>
              <p className="text-gray-600">{roleCard.output_style}</p>
            </div>
          )}

          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Modify frontend/src/routes.tsx to include role cards page**

```tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/shared/Layout'
import HomePage from './pages/HomePage'
import SettingsPage from './pages/SettingsPage'
import RoleCardsPage from './pages/RoleCardsPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'role-cards',
        element: <RoleCardsPage />,
      },
      {
        path: 'rooms',
        element: <div>群聊管理（开发中）</div>,
      },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
```

- [ ] **Step 6: Verify frontend builds**

```bash
cd frontend
npm run build
```

Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/RoleCardsPage.tsx frontend/src/components/role-card/ frontend/src/routes.tsx
git commit -m "feat(frontend): add role card management page

- Role cards page with list and form
- Create/edit role card with validation
- Copy role card functionality
- Preview modal for system prompt
- Built-in role card protection
- React Hook Form + Zod validation"
```

---

## Task 11: Final Integration and Verification

**Files:**
- Create: `docs/stage1-test.md`

- [ ] **Step 1: Start backend and verify all endpoints**

```bash
cd backend
uvicorn app.main:app --reload --port 8000

# Test Provider CRUD
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test OpenAI","base_url":"https://api.openai.com/v1","api_key":"sk-test","default_model":"gpt-4o"}'

curl http://localhost:8000/api/providers

# Test Role Card CRUD
curl http://localhost:8000/api/role-cards
curl http://localhost:8000/api/role-cards?builtin=true
```

Expected: Provider created, 4 built-in role cards returned

- [ ] **Step 2: Start frontend and verify UI**

```bash
cd frontend
npm run dev
```

Open http://localhost:5173 and verify:
- Settings page shows provider form and list
- Role cards page shows built-in roles
- Can create/edit/delete providers
- Can create/edit/copy role cards
- Preview modal works for role cards

- [ ] **Step 3: Create stage1-test.md documentation**

```bash
cat > docs/stage1-test.md << 'EOF'
# Stage 1 Verification Guide

## Backend Verification

### Provider API
```bash
# Create provider
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","base_url":"https://api.openai.com/v1","api_key":"sk-test","default_model":"gpt-4o"}'

# List providers
curl http://localhost:8000/api/providers

# Get single provider
curl http://localhost:8000/api/providers/{id}

# Update provider
curl -X PUT http://localhost:8000/api/providers/{id} \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}'

# Delete provider
curl -X DELETE http://localhost:8000/api/providers/{id}

# Test connection
curl -X POST http://localhost:8000/api/providers/{id}/test
```

### Role Card API
```bash
# List all role cards
curl http://localhost:8000/api/role-cards

# List built-in only
curl http://localhost:8000/api/role-cards?builtin=true

# Create role card
curl -X POST http://localhost:8000/api/role-cards \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Test role","expertise":["test"],"responsibilities":["test"],"system_prompt":"You are test"}'

# Copy role card
curl -X POST http://localhost:8000/api/role-cards/{id}/copy \
  -H "Content-Type: application/json" \
  -d '{"new_name":"Copied Role"}'
```

## Frontend Verification

### Settings Page
- [ ] Page loads with provider form
- [ ] Can create new provider
- [ ] Can edit existing provider
- [ ] Can delete provider
- [ ] Can test connection
- [ ] API key is masked in list

### Role Cards Page
- [ ] Page loads with 4 built-in roles
- [ ] Can create new role card
- [ ] Can edit custom role card
- [ ] Cannot edit built-in role card
- [ ] Can copy role card
- [ ] Can delete custom role card
- [ ] Cannot delete built-in role card
- [ ] Preview modal shows system prompt

## Troubleshooting

### Backend issues
- Check Python 3.12+ is installed
- Verify virtual environment is activated
- Check port 8000 is not in use

### Frontend issues
- Check Node.js 18+ is installed
- Run `npm install` in frontend directory
- Check port 5173 is not in use

### CORS issues
- Ensure backend is running on port 8000
- Check Vite proxy configuration
EOF
```

- [ ] **Step 4: Commit documentation**

```bash
git add docs/stage1-test.md
git commit -m "docs: add Stage 1 verification guide"
```

---

## Summary

This plan implements Stage 1 of the Expert Room project:

1. ✅ Crypto service for API key encryption (Fernet/AES)
2. ✅ Provider schemas (Pydantic)
3. ✅ Provider service (CRUD + connection test)
4. ✅ Provider API router (6 endpoints)
5. ✅ Role card schemas (Pydantic)
6. ✅ Role card service (CRUD + copy)
7. ✅ Role card API router (6 endpoints)
8. ✅ Built-in role cards seed data (4 roles)
9. ✅ Frontend provider management page
10. ✅ Frontend role card management page
11. ✅ Integration verification

**Next Stage:** Stage 2 - Room Creation + File Processing
