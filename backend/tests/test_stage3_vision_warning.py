"""Tests for Story 24.1 — Visual analysis fallback warning propagation.

Updated in Story 46.2: GPT-4o Vision eliminated; Mistral now drives Stage 3.2.
Fallback trigger changed from VISION_AI_ENABLED=false / missing OPENROUTER_API_KEY
to missing MISTRAL_API_KEY.

Covers:
- AC-1: Warning added to context when MISTRAL_API_KEY absent
- AC-3/4: pipeline_completed SSE summary includes warnings
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
# AC-1: Warning when MISTRAL_API_KEY absent → threshold-based fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage3_mistral_key_absent_warning():
    """When MISTRAL_API_KEY is absent, context gets a configuration warning (Story 46.2)."""
    mod = _get_stage3()
    context = _make_minimal_context()

    with patch.dict(os.environ, {"MISTRAL_API_KEY": ""}):
        await mod.run_stage3(context, _noop_emit)

    warnings = context.get("_pipeline_warnings", [])
    # Story 46.2: warning must reference MISTRAL_API_KEY and ~75% quality
    assert any("MISTRAL_API_KEY" in str(w) for w in warnings), (
        f"Expected MISTRAL_API_KEY mention in warning, got: {warnings}"
    )
    assert any("75%" in str(w) or "threshold" in str(w).lower() for w in warnings), (
        f"Expected quality/threshold mention in warning, got: {warnings}"
    )


@pytest.mark.asyncio
async def test_stage3_mistral_key_present_no_fallback_warning():
    """When MISTRAL_API_KEY is present, no threshold-fallback warning is emitted."""
    mod = _get_stage3()
    context = _make_minimal_context()

    # With key present but empty clusters, Mistral path runs but no clusters to process
    with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key-123"}):
        await mod.run_stage3(context, _noop_emit)

    warnings = [w for w in context.get("_pipeline_warnings", []) if isinstance(w, str)]
    assert not any("MISTRAL_API_KEY" in w for w in warnings), (
        f"Expected no MISTRAL_API_KEY warning when key is present, got: {warnings}"
    )
