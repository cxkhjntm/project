"""Unified LLM API client with retry logic."""

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)

_global_client: httpx.AsyncClient | None = None


async def get_global_client() -> httpx.AsyncClient:
    global _global_client
    if _global_client is None:
        _global_client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
        )
    return _global_client


async def close_global_client() -> None:
    global _global_client
    if _global_client is not None:
        await _global_client.aclose()
        _global_client = None


@dataclass
class ModelResponse:
    """Response from LLM API."""

    content: str
    usage: dict[str, int]
    model: str
    finish_reason: str | None = None


class ModelClientError(Exception):
    """Base exception for model client errors."""

    pass


class ModelClient:
    """Unified client for OpenAI-compatible LLM APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 1,
        timeout: float = 120.0,
    ):
        """Initialize model client.

        Args:
            base_url: API base URL (e.g., https://api.openai.com/v1)
            api_key: API key for authentication
            model: Model name (e.g., gpt-4o)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_retries: Number of retries on failure
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.timeout = timeout

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> ModelResponse:
        """Send chat completion request.

        Args:
            messages: List of message dicts with role and content
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences

        Returns:
            ModelResponse with content and usage

        Raises:
            ModelClientError: On API failure after retries
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if stop:
            payload["stop"] = stop

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                client = await get_global_client()
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    raise ModelClientError(
                        f"API returned status {response.status_code}: {error_text}"
                    )

                data = response.json()

                return ModelResponse(
                    content=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                    model=data.get("model", self.model),
                    finish_reason=data["choices"][0].get("finish_reason"),
                )

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        "LLM API call failed, retrying",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "LLM API call failed after retries",
                        attempts=self.max_retries + 1,
                        error=str(e),
                    )

        raise ModelClientError(f"Failed after {self.max_retries + 1} attempts: {last_error}")

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat completion request.

        Args:
            messages: List of message dicts with role and content
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences

        Yields:
            Content chunks as they arrive

        Raises:
            ModelClientError: On API failure
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": True,
        }
        if stop:
            payload["stop"] = stop

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            client = await get_global_client()
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()

                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line:
                            continue

                        if line == "data: [DONE]":
                            return

                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]

                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse SSE chunk", chunk=data_str[:200])
                            continue

        except httpx.HTTPStatusError as e:
            raise ModelClientError(
                f"API returned status {e.response.status_code}: {e.response.text[:500]}"
            ) from e
        except httpx.HTTPError as e:
            raise ModelClientError(f"Stream request failed: {e}") from e

    async def test_connection(self) -> dict[str, Any]:
        """Test API connection.

        Returns:
            Dict with success, message, latency_ms
        """
        import time

        start_time = time.time()

        try:
            response = await self.chat_completion(
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            latency_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "message": "Connection successful",
                "latency_ms": round(latency_ms, 2),
                "model": response.model,
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "message": str(e),
                "latency_ms": round(latency_ms, 2),
            }


# Factory function
def create_model_client(
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> ModelClient:
    """Create a model client instance.

    Args:
        base_url: API base URL
        api_key: API key
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens

    Returns:
        ModelClient instance
    """
    return ModelClient(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
