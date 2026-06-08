"""Tests for model client."""

import pytest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.model_client import (
    ModelClient,
    ModelResponse,
    get_global_client,
    close_global_client,
)


@pytest.mark.asyncio
async def test_model_client_chat_completion():
    """Test chat completion call."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "Test response"
                }
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
    }
    
    # Act
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
        )
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
    
    # Assert
    assert isinstance(result, ModelResponse)
    assert result.content == "Test response"
    assert result.usage["total_tokens"] == 15


@pytest.mark.asyncio
async def test_model_client_retry_on_failure():
    """Test retry logic on API failure."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        max_retries=2,
    )
    
    # Act
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [
            Exception("Connection error"),
            AsyncMock(
                status_code=200,
                json=lambda: {
                    "choices": [{"message": {"content": "Retry success"}}],
                    "usage": {"total_tokens": 10},
                },
            ),
        ]
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )
    
    # Assert
    assert result.content == "Retry success"
    assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_get_global_client_creates_instance():
    """Test that get_global_client creates a singleton instance."""
    # Arrange - ensure clean state
    import app.services.model_client as module
    module._global_client = None

    # Act
    client = await get_global_client()

    # Assert
    assert client is not None
    assert isinstance(client, httpx.AsyncClient)

    # Cleanup
    await close_global_client()


@pytest.mark.asyncio
async def test_get_global_client_returns_same_instance():
    """Test that get_global_client returns the same instance on multiple calls."""
    # Arrange - ensure clean state
    import app.services.model_client as module
    module._global_client = None

    # Act
    client1 = await get_global_client()
    client2 = await get_global_client()

    # Assert
    assert client1 is client2

    # Cleanup
    await close_global_client()


@pytest.mark.asyncio
async def test_global_client_has_connection_pool_config():
    """Test that global client has proper connection pool configuration."""
    # Arrange - ensure clean state
    import app.services.model_client as module
    module._global_client = None

    # Act
    client = await get_global_client()

    # Assert - verify connection pool limits
    # httpx.AsyncClient stores pool config in _transport
    transport = client._transport
    assert transport._pool._max_keepalive_connections == 20

    # Cleanup
    await close_global_client()


@pytest.mark.asyncio
async def test_close_global_client():
    """Test that close_global_client properly closes and resets the client."""
    # Arrange - ensure clean state
    import app.services.model_client as module
    module._global_client = None
    client = await get_global_client()
    assert module._global_client is not None

    # Act
    await close_global_client()

    # Assert
    assert module._global_client is None
