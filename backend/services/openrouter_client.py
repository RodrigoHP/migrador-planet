"""OpenRouter API client with rate limiting and exponential backoff retry.

Uses the OpenAI Python SDK with a custom base_url pointing to OpenRouter.

Configuration:
    OPENROUTER_API_KEY  — required (raises ValueError if missing and not mocked)
    VISION_AI_ENABLED   — default "true"; set to "false" to skip Vision AI

Usage:
    from services.openrouter_client import get_client, chat_with_vision

    client = get_client()
    response = await chat_with_vision(client, image_b64="...", prompt="...")
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o"
MAX_RETRIES = 3
RETRY_DELAYS = (1.0, 2.0, 4.0)  # seconds
REQUEST_TIMEOUT = 30.0

# Cost estimates per 1K tokens (approximate for gpt-4o vision)
COST_PER_1K_INPUT_TOKENS = 0.005
COST_PER_1K_OUTPUT_TOKENS = 0.015
# Estimate for a vision call with image (~765 tokens input + ~300 output)
ESTIMATED_COST_PER_VISION_CALL = 0.025


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def get_client(api_key: Optional[str] = None):  # type: ignore[return]
    """Return an AsyncOpenAI client configured for OpenRouter.

    Args:
        api_key: Override the OPENROUTER_API_KEY env var (useful in tests).

    Returns:
        AsyncOpenAI instance

    Raises:
        ValueError: If api_key is None and OPENROUTER_API_KEY is not set.
    """
    from openai import AsyncOpenAI  # type: ignore[import-untyped]

    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is not set. "
            "Set it or pass api_key= to get_client()."
        )

    return AsyncOpenAI(
        api_key=key,
        base_url=OPENROUTER_BASE_URL,
        timeout=REQUEST_TIMEOUT,
        default_headers={
            "HTTP-Referer": "https://migrador-planet.app",
            "X-Title": "Migrador Planet",
        },
    )


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------


async def _call_with_retry(
    client: Any,
    messages: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
    response_format: Optional[Dict[str, str]] = None,
) -> Any:
    """Call client.chat.completions.create with exponential backoff retry.

    Retries on RateLimitError (429) and APIStatusError (5xx).  After
    MAX_RETRIES exhausted, re-raises the last exception.

    Returns the raw completion object.
    """
    from openai import APIStatusError, RateLimitError  # type: ignore[import-untyped]

    kwargs: Dict[str, Any] = {"model": model, "messages": messages}
    if response_format:
        kwargs["response_format"] = response_format

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            return await client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            last_exc = exc
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning("Rate limit hit (attempt %d/%d). Retrying in %.1fs", attempt + 1, MAX_RETRIES, delay)
            await asyncio.sleep(delay)
        except APIStatusError as exc:
            if exc.status_code and exc.status_code >= 500:
                last_exc = exc
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                logger.warning("Server error %d (attempt %d/%d). Retrying in %.1fs", exc.status_code, attempt + 1, MAX_RETRIES, delay)
                await asyncio.sleep(delay)
            else:
                raise
        except Exception:
            raise

    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# High-level vision call
# ---------------------------------------------------------------------------


async def chat_with_vision(
    client: Any,
    image_b64: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
) -> tuple[str, float]:
    """Send a vision request and return (response_text, cost_usd).

    Args:
        client:    AsyncOpenAI client (get_client() or a mock).
        image_b64: Base64-encoded PNG image.
        prompt:    Instruction text for GPT-4o.
        model:     Model identifier (default: openai/gpt-4o).

    Returns:
        Tuple of (raw text content, cost in USD).
        Cost is calculated from completion.usage when available;
        falls back to ESTIMATED_COST_PER_VISION_CALL when usage is None.
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        }
    ]
    completion = await _call_with_retry(
        client,
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
    )
    text = completion.choices[0].message.content or ""

    # Calculate real cost from usage tokens when available
    if completion.usage:
        cost = (
            completion.usage.prompt_tokens * COST_PER_1K_INPUT_TOKENS
            + completion.usage.completion_tokens * COST_PER_1K_OUTPUT_TOKENS
        ) / 1000
    else:
        cost = ESTIMATED_COST_PER_VISION_CALL  # fallback when provider omits usage

    return text, cost


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap around JSON."""
    stripped = re.sub(r'^```(?:\w*)\s*\n?', '', text.strip())
    stripped = re.sub(r'\n?```\s*$', '', stripped)
    return stripped.strip()


def load_image_as_base64(path: str) -> str:
    """Read an image file from disk and return base64-encoded string."""
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def format_cost_summary(call_count: int) -> str:
    """Return human-readable cost summary string for SSE event."""
    estimated = call_count * ESTIMATED_COST_PER_VISION_CALL
    return f"Vision AI: {call_count} chamadas, ~${estimated:.2f}"
