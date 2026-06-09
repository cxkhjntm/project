"""Provider service for CRUD operations."""

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
            default_max_input_tokens=data.default_max_input_tokens,
            default_max_output_tokens=data.default_max_output_tokens,
            enabled=True,
        )

        session.add(provider)
        await session.flush()

        logger.info("Created provider", provider_id=provider.id, name=provider.name)
        return provider

    async def get_all(self, session: AsyncSession) -> list[Provider]:
        """Get all providers.

        Args:
            session: Database session

        Returns:
            List of providers
        """
        result = await session.execute(select(Provider).order_by(Provider.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, provider_id: str) -> Provider | None:
        """Get provider by ID.

        Args:
            session: Database session
            provider_id: Provider ID

        Returns:
            Provider or None
        """
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, provider_id: str, data: ProviderUpdate
    ) -> Provider | None:
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

        valid_fields = {col.name for col in Provider.__table__.columns}
        for field, value in update_data.items():
            if field not in valid_fields:
                logger.warning("Ignoring invalid field in provider update", field=field)
                continue
            setattr(provider, field, value)

        await session.flush()
        await session.refresh(provider)

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
                    message = f"API returned status {response.status_code}: {response.text[:200]}"
                    return {
                        "success": False,
                        "message": message,
                        "latency_ms": round(latency_ms, 2),
                    }

        except httpx.TimeoutException:
            return {"success": False, "message": "Connection timeout (30s)", "latency_ms": None}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}", "latency_ms": None}


# Singleton instance
provider_service = ProviderService()
