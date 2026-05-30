"""Tests for model client."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.model_client import ModelClient, ModelResponse


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
