"""Tests for model client."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.model_client import (
    ModelClient,
    ModelClientError,
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


# ===== Streaming Tests =====

def _make_sse_chunks(*content_parts: str) -> list[bytes]:
    """Helper to create SSE-formatted byte chunks.
    
    Args:
        content_parts: Content strings for each delta
        
    Returns:
        List of bytes chunks in SSE format
    """
    chunks = []
    for content in content_parts:
        data = {
            "choices": [
                {
                    "delta": {"content": content},
                    "finish_reason": None,
                }
            ]
        }
        chunks.append(f"data: {json.dumps(data)}\n\n".encode())
    # Add [DONE] terminator
    chunks.append(b"data: [DONE]\n\n")
    return chunks


@pytest.mark.asyncio
async def test_chat_completion_stream_yields_content():
    """Test that chat_completion_stream yields content chunks."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    chunks = _make_sse_chunks("Hello", " world", "!")
    
    # Create mock response that supports streaming
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    async def mock_aiter_bytes():
        for chunk in chunks:
            yield chunk
    
    mock_response.aiter_bytes = mock_aiter_bytes
    
    # Create mock stream context manager
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act
    with patch("httpx.AsyncClient.stream", return_value=mock_stream) as mock_stream_call:
        results = []
        async for chunk in client.chat_completion_stream(
            messages=[{"role": "user", "content": "Hello"}]
        ):
            results.append(chunk)
    
    # Assert
    assert results == ["Hello", " world", "!"]
    mock_stream_call.assert_called_once()


@pytest.mark.asyncio
async def test_chat_completion_stream_sends_correct_payload():
    """Test that stream method sends correct API payload."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        temperature=0.5,
        max_tokens=100,
    )
    
    chunks = _make_sse_chunks("ok")
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    async def mock_aiter_bytes():
        for chunk in chunks:
            yield chunk
    
    mock_response.aiter_bytes = mock_aiter_bytes
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act
    with patch("httpx.AsyncClient.stream", return_value=mock_stream) as mock_stream_call:
        async for _ in client.chat_completion_stream(
            messages=[{"role": "user", "content": "test"}],
            temperature=0.3,
            max_tokens=50,
            stop=["END"],
        ):
            pass
    
    # Assert - check the payload passed to stream()
    call_kwargs = mock_stream_call.call_args
    assert call_kwargs.kwargs.get("json", call_kwargs[1].get("json") if len(call_kwargs) > 1 else None) is not None
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["model"] == "gpt-4o"
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 50
    assert payload["stop"] == ["END"]
    assert payload["stream"] is True


@pytest.mark.asyncio
async def test_chat_completion_stream_handles_done_terminator():
    """Test that stream correctly handles [DONE] terminator."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    # Create chunks with [DONE] in the middle (simulating premature DONE)
    data1 = {"choices": [{"delta": {"content": "first"}}]}
    data2 = {"choices": [{"delta": {"content": "second"}}]}
    chunks = [
        f"data: {json.dumps(data1)}\n\n".encode(),
        b"data: [DONE]\n\n",
        f"data: {json.dumps(data2)}\n\n".encode(),  # Should be ignored
    ]
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    async def mock_aiter_bytes():
        for chunk in chunks:
            yield chunk
    
    mock_response.aiter_bytes = mock_aiter_bytes
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act
    with patch("httpx.AsyncClient.stream", return_value=mock_stream):
        results = []
        async for chunk in client.chat_completion_stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            results.append(chunk)
    
    # Assert - only content before [DONE] should be yielded
    assert results == ["first"]


@pytest.mark.asyncio
async def test_chat_completion_stream_handles_empty_delta():
    """Test that stream handles empty or missing delta content."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    # Some chunks have empty delta (role announcement, etc.)
    data_role = {"choices": [{"delta": {"role": "assistant"}}]}
    data_empty = {"choices": [{"delta": {}}]}
    data_content = {"choices": [{"delta": {"content": "hello"}}]}
    
    chunks = [
        f"data: {json.dumps(data_role)}\n\n".encode(),
        f"data: {json.dumps(data_empty)}\n\n".encode(),
        f"data: {json.dumps(data_content)}\n\n".encode(),
        b"data: [DONE]\n\n",
    ]
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    async def mock_aiter_bytes():
        for chunk in chunks:
            yield chunk
    
    mock_response.aiter_bytes = mock_aiter_bytes
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act
    with patch("httpx.AsyncClient.stream", return_value=mock_stream):
        results = []
        async for chunk in client.chat_completion_stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            results.append(chunk)
    
    # Assert - only content with actual text should be yielded
    assert results == ["hello"]


@pytest.mark.asyncio
async def test_chat_completion_stream_handles_api_error():
    """Test that stream raises ModelClientError on HTTP error status."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401, text="Invalid API key"),
        )
    )
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act & Assert
    with patch("httpx.AsyncClient.stream", return_value=mock_stream):
        with pytest.raises(ModelClientError) as exc_info:
            async for _ in client.chat_completion_stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass
    
    assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_completion_stream_handles_network_error():
    """Test that stream raises ModelClientError on network failure."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act & Assert
    with patch("httpx.AsyncClient.stream", return_value=mock_stream):
        with pytest.raises(ModelClientError):
            async for _ in client.chat_completion_stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass


@pytest.mark.asyncio
async def test_chat_completion_stream_handles_malformed_json():
    """Test that stream skips malformed JSON lines gracefully."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    chunks = [
        b"data: {invalid json}\n\n",
        f"data: {json.dumps({'choices': [{'delta': {'content': 'ok'}}]})}\n\n".encode(),
        b"data: [DONE]\n\n",
    ]
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    async def mock_aiter_bytes():
        for chunk in chunks:
            yield chunk
    
    mock_response.aiter_bytes = mock_aiter_bytes
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act
    with patch("httpx.AsyncClient.stream", return_value=mock_stream):
        results = []
        async for chunk in client.chat_completion_stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            results.append(chunk)
    
    # Assert - malformed line skipped, valid content yielded
    assert results == ["ok"]


@pytest.mark.asyncio
async def test_chat_completion_stream_empty_stream():
    """Test that stream handles an empty stream (no content chunks)."""
    # Arrange
    client = ModelClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
    )
    
    chunks = [b"data: [DONE]\n\n"]
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    async def mock_aiter_bytes():
        for chunk in chunks:
            yield chunk
    
    mock_response.aiter_bytes = mock_aiter_bytes
    
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    
    # Act
    with patch("httpx.AsyncClient.stream", return_value=mock_stream):
        results = []
        async for chunk in client.chat_completion_stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            results.append(chunk)
    
    # Assert - no content chunks
    assert results == []
