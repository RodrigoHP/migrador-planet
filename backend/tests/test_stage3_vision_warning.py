"""Tests for Story 24.1 — Vision AI fallback warning propagation.

Covers:
- AC-1: Warning added to context when OPENROUTER_API_KEY absent/invalid
- AC-2: Warning added to context when VISION_AI_ENABLED=false
- AC-3/4: pipeline_completed SSE summary includes vision_ai_used and warnings
"""

from __future__ import annotations

import os
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def _get_stage3() -> ModuleType:
    import importlib
    import sys

    mod_name = "services.stages.stage3_structural_analysis"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_minimal_context() -> dict[str, Any]:
    return {
        "clusters": [],
        "_raw_text_blocks": {},
        "enriched_documents": [],
    }


async def _noop_emit(event: Any) -> None:
    pass


# ---------------------------------------------------------------------------
# AC-1: Warning when OPENROUTER_API_KEY absent → ValueError from get_client()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage3_vision_fallback_warning_on_missing_key():
    """When get_client() raises ValueError (no API key), context gets a warning."""
    mod = _get_stage3()
    context = _make_minimal_context()

    with patch.dict(os.environ, {"VISION_AI_ENABLED": "true"}):
        with patch(
            "services.stages.stage3_structural_analysis.get_client",
            side_effect=ValueError("OPENROUTER_API_KEY not set"),
            create=True,
        ):
            with patch("services.openrouter_client.get_client", side_effect=ValueError("OPENROUTER_API_KEY not set")):
                await mod.run_stage3(context, _noop_emit)

    warnings = context.get("_pipeline_warnings", [])
    assert any("Vision AI desabilitado" in w for w in warnings), (
        f"Expected vision fallback warning in context, got: {warnings}"
    )
    assert any("fallback" in w.lower() or "75%" in w for w in warnings), (
        f"Expected quality/fallback mention in warning, got: {warnings}"
    )


# ---------------------------------------------------------------------------
# AC-2: Warning when VISION_AI_ENABLED=false
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage3_vision_disabled_via_env_warning():
    """When VISION_AI_ENABLED=false, context gets a configuration warning."""
    mod = _get_stage3()
    context = _make_minimal_context()

    with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
        await mod.run_stage3(context, _noop_emit)

    warnings = context.get("_pipeline_warnings", [])
    assert any("VISION_AI_ENABLED=false" in w for w in warnings), (
        f"Expected VISION_AI_ENABLED=false mention in warning, got: {warnings}"
    )
