"""Tests for Story 24.3 — Real Vision AI cost tracking via completion.usage.

Covers:
- AC-1: chat_with_vision returns (text, cost) tuple
- AC-2: Cost calculated from completion.usage tokens
- AC-5: Fallback to ESTIMATED_COST_PER_VISION_CALL when usage is None
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _get_client_module():
    import importlib

    return importlib.import_module("services.openrouter_client")


def _make_completion(text: str, prompt_tokens: int | None, completion_tokens: int | None) -> MagicMock:
    """Build a mock completion object mimicking openai ChatCompletion."""
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = text

    if prompt_tokens is None and completion_tokens is None:
        completion.usage = None
    else:
        completion.usage = MagicMock()
        completion.usage.prompt_tokens = prompt_tokens
        completion.usage.completion_tokens = completion_tokens

    return completion


# ---------------------------------------------------------------------------
# AC-1 + AC-2: returns tuple, cost from usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_with_vision_returns_tuple_with_real_cost():
    """chat_with_vision must return (text, cost) and calculate cost from usage."""
    mod = _get_client_module()

    # 1000 input tokens × $0.005/1K + 200 output tokens × $0.015/1K = $0.005 + $0.003 = $0.008
    mock_completion = _make_completion(
        text='{"regions": []}',
        prompt_tokens=1000,
        completion_tokens=200,
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    text, cost = await mod.chat_with_vision(mock_client, image_b64="abc", prompt="analyze")

    assert text == '{"regions": []}'
    expected_cost = (1000 * mod.COST_PER_1K_INPUT_TOKENS + 200 * mod.COST_PER_1K_OUTPUT_TOKENS) / 1000
    assert abs(cost - expected_cost) < 1e-9, f"Expected {expected_cost}, got {cost}"


# ---------------------------------------------------------------------------
# AC-5: fallback when usage is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_with_vision_falls_back_when_usage_none():
    """When completion.usage is None, cost must be ESTIMATED_COST_PER_VISION_CALL."""
    mod = _get_client_module()

    mock_completion = _make_completion(text="{}", prompt_tokens=None, completion_tokens=None)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    text, cost = await mod.chat_with_vision(mock_client, image_b64="abc", prompt="analyze")

    assert text == "{}"
    assert cost == mod.ESTIMATED_COST_PER_VISION_CALL, (
        f"Expected fallback cost {mod.ESTIMATED_COST_PER_VISION_CALL}, got {cost}"
    )
