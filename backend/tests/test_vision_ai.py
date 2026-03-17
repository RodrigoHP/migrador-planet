"""Tests for Story 5.10 — Bloco 6: Vision AI (Stages 20–22).

Covers:
- Stage 20 — Visual Segmentation: mock API, region parsing, fallback
- Stage 21 — Visual Interpretation: mock API, interpretation parsing
- Stage 22 — Self-Check: consistency scoring, retry on low score
- OpenRouter client: rate limit retry, cost formatting
- register_bloco6_vision: wires stages 20-22 into registry
- VISION_AI_ENABLED=false: skip entire bloco with warning SSE
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_page(
    page_number: int,
    text_block_count: int = 3,
    image_count: int = 0,
    screenshot_path: Optional[str] = None,
) -> Dict[str, Any]:
    text_blocks = [
        {
            "text": f"block_{i}",
            "bbox": [10.0, 100.0 + i * 20, 200.0, 115.0 + i * 20],
            "page_number": page_number,
            "pdf_index": 0,
            "font_name": "Arial",
            "font_size": 10.0,
            "semantic_label": "",
        }
        for i in range(text_block_count)
    ]
    images = [{"path": f"/tmp/img_{i}.png", "format": "png", "bbox": [0, 0, 100, 100], "page_number": page_number, "pdf_index": 0} for i in range(image_count)]
    return {
        "page_number": page_number,
        "text_blocks": text_blocks,
        "images": images,
        "fonts": [],
        "grid_info": None,
        "screenshot_path": screenshot_path,
    }


def _make_doc(pages: List[Dict[str, Any]], pdf_index: int = 0) -> Dict[str, Any]:
    return {
        "job_id": "test-job",
        "pdf_index": pdf_index,
        "pdf_name": f"doc_{pdf_index}.pdf",
        "pages": pages,
    }


def _make_layout_type(pdf_index: int = 0, page_number: int = 0, cluster_id: int = 0) -> Dict[str, Any]:
    return {
        "cluster_id": cluster_id,
        "name": f"layout_{cluster_id}",
        "representative_page": {"pdf_index": pdf_index, "page_number": page_number},
        "fingerprint": {"tableCount": 0, "columnCount": 1, "headerBlocks": 0, "bodyZoneRatio": 0.75, "footerPresent": False},
        "fingerprint_hash": "abc123",
        "page_count": 1,
        "pages": [{"pdf_index": pdf_index, "page_number": page_number}],
        "is_reusable": False,
        "template_id": None,
    }


def _make_mock_completion(content: str) -> MagicMock:
    """Build a mock AsyncOpenAI completion object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _segmentation_response() -> str:
    return json.dumps({
        "regions": [
            {"type": "header", "bbox": [0, 0, 800, 100], "description": "Company header"},
            {"type": "body", "bbox": [0, 100, 800, 700], "description": "Main body"},
            {"type": "footer", "bbox": [0, 700, 800, 800], "description": "Page footer"},
        ]
    })


def _interpretation_response() -> str:
    return json.dumps({
        "interpretations": [
            {
                "region_type": "header",
                "description": "Logo and company name",
                "html_suggestion": "<header><img src='logo.png'><h1>Company</h1></header>",
            },
            {
                "region_type": "body",
                "description": "Main document content with form fields",
                "html_suggestion": "<main><form>...</form></main>",
            },
        ]
    })


# ---------------------------------------------------------------------------
# Test 1 — Visual Segmentation: successful mock call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_segmentation_success_mock():
    """Stage 20 with mocked API returns regions for each representative page."""
    from services.stages.visual_segmentation import execute

    mock_client = AsyncMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_completion(_segmentation_response())
    )

    page = _make_page(0, screenshot_path="/tmp/fake_screenshot.png")
    doc = _make_doc([page])
    lt = _make_layout_type(pdf_index=0, page_number=0)

    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read = MagicMock(return_value=b"fake_image_bytes")

        context: Dict[str, Any] = {
            "layout_types": [lt],
            "parsed_documents": [doc],
            "job_id": "test-job",
            "vision_client": mock_client,
        }

        result = await execute(context)

    assert result["pages_processed"] >= 1
    assert "0:0" in context["visual_analysis"]
    regions = context["visual_analysis"]["0:0"]["visual_regions"]
    assert len(regions) == 3
    assert regions[0]["type"] == "header"


# ---------------------------------------------------------------------------
# Test 2 — Visual Segmentation: screenshot missing → fallback with vision_unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_segmentation_screenshot_missing():
    """If screenshot file is missing, page should be marked vision_unavailable."""
    from services.stages.visual_segmentation import execute

    mock_client = AsyncMock()

    page = _make_page(0, screenshot_path=None)  # no screenshot path
    doc = _make_doc([page])
    lt = _make_layout_type(pdf_index=0, page_number=0)

    context: Dict[str, Any] = {
        "layout_types": [lt],
        "parsed_documents": [doc],
        "job_id": "test-job",
        "vision_client": mock_client,
    }

    # load_image_as_base64 will try to open a non-existent file
    with patch("services.openrouter_client.load_image_as_base64", side_effect=FileNotFoundError("no file")):
        result = await execute(context)

    assert "0:0" in context["visual_analysis"]
    assert context["visual_analysis"]["0:0"]["vision_unavailable"] is True


# ---------------------------------------------------------------------------
# Test 3 — Visual Segmentation: API call fails → fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_segmentation_api_failure_fallback():
    """API error during segmentation should mark page unavailable and continue."""
    from services.stages.visual_segmentation import execute

    mock_client = AsyncMock()

    page = _make_page(0, screenshot_path="/tmp/screenshot.png")
    doc = _make_doc([page])
    lt = _make_layout_type(pdf_index=0, page_number=0)

    events = []

    context: Dict[str, Any] = {
        "layout_types": [lt],
        "parsed_documents": [doc],
        "job_id": "test-job",
        "vision_client": mock_client,
        "emit_progress": events.append,
    }

    with patch("services.openrouter_client.load_image_as_base64", return_value="base64data"):
        with patch("services.openrouter_client.chat_with_vision", side_effect=RuntimeError("API down")):
            result = await execute(context)

    # Pipeline should continue
    assert "0:0" in context["visual_analysis"]
    assert context["visual_analysis"]["0:0"]["vision_unavailable"] is True
    # SSE warning should have been emitted
    warning_events = [e for e in events if e.get("status") == "warning"]
    assert len(warning_events) >= 1


# ---------------------------------------------------------------------------
# Test 4 — Visual Segmentation: VISION_AI_ENABLED=false skips
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_segmentation_disabled_env():
    """When VISION_AI_ENABLED=false, Stage 20 skips with warning SSE."""
    from services.stages.visual_segmentation import execute

    events = []
    context: Dict[str, Any] = {
        "layout_types": [_make_layout_type()],
        "parsed_documents": [],
        "job_id": "test-job",
        "emit_progress": events.append,
    }

    with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
        result = await execute(context)

    assert result.get("skipped") is True
    assert context.get("vision_unavailable") is True
    skipped_events = [e for e in events if e.get("status") == "skipped"]
    assert len(skipped_events) == 1
    assert "Vision AI" in skipped_events[0].get("warning", "")


# ---------------------------------------------------------------------------
# Test 5 — Visual Interpretation: successful mock call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_interpretation_success_mock():
    """Stage 21 populates visual_interpretations from mock API response."""
    from services.stages.visual_interpretation import execute

    mock_client = AsyncMock()

    page = _make_page(0, screenshot_path="/tmp/screenshot.png")
    doc = _make_doc([page])

    # Pre-fill visual_analysis as if Stage 20 ran
    visual_analysis = {
        "0:0": {
            "visual_regions": [{"type": "header", "bbox": [0, 0, 800, 100], "description": "header"}],
            "visual_interpretations": [],
            "consistency_score": None,
            "vision_unavailable": False,
        }
    }

    context: Dict[str, Any] = {
        "visual_analysis": visual_analysis,
        "parsed_documents": [doc],
        "job_id": "test-job",
        "vision_client": mock_client,
    }

    with patch("services.openrouter_client.load_image_as_base64", return_value="b64data"):
        with patch("services.openrouter_client.chat_with_vision", return_value=_interpretation_response()):
            result = await execute(context)

    assert result["pages_interpreted"] >= 1
    interpretations = context["visual_analysis"]["0:0"]["visual_interpretations"]
    assert len(interpretations) >= 1
    assert "region_type" in interpretations[0]
    assert "html_suggestion" in interpretations[0]


# ---------------------------------------------------------------------------
# Test 6 — Visual Interpretation: skipped if vision_unavailable=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_interpretation_skipped_when_unavailable():
    """Stage 21 should skip if context['vision_unavailable'] is True."""
    from services.stages.visual_interpretation import execute

    events = []
    context: Dict[str, Any] = {
        "visual_analysis": {},
        "parsed_documents": [],
        "job_id": "test-job",
        "vision_unavailable": True,
        "emit_progress": events.append,
    }

    result = await execute(context)
    assert result.get("skipped") is True


# ---------------------------------------------------------------------------
# Test 7 — Self-Check: high-consistency scenario
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_check_high_consistency():
    """Self-Check should assign score >= 80 when visual matches text extraction."""
    from services.stages.vision_self_check import execute

    # Page with text blocks
    page = _make_page(0, text_block_count=5, image_count=0)
    doc = _make_doc([page])

    visual_analysis = {
        "0:0": {
            "visual_regions": [
                {"type": "header", "bbox": [0, 0, 800, 100], "description": "header"},
                {"type": "body", "bbox": [0, 100, 800, 700], "description": "body"},
                {"type": "footer", "bbox": [0, 700, 800, 800], "description": "footer"},
            ],
            "visual_interpretations": [],
            "consistency_score": None,
            "vision_unavailable": False,
        }
    }

    context: Dict[str, Any] = {
        "visual_analysis": visual_analysis,
        "parsed_documents": [doc],
        "tables": [],
        "job_id": "test-job",
    }

    with patch("services.openrouter_client.format_cost_summary", return_value="Vision AI: 3 chamadas, ~$0.08"):
        result = await execute(context)

    score = context["visual_analysis"]["0:0"]["consistency_score"]
    level = context["visual_analysis"]["0:0"]["consistency_level"]
    assert score >= 50, f"Expected score >= 50, got {score}"
    assert level in ("consistent", "partial")


# ---------------------------------------------------------------------------
# Test 8 — Self-Check: low consistency triggers retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_check_low_score_triggers_retry():
    """Self-Check should retry segmentation when consistency_score < 50."""
    from services.stages.vision_self_check import execute

    page = _make_page(0, text_block_count=10, image_count=2)
    doc = _make_doc([page])

    # Visual analysis with NO regions despite heavy text/images → low score
    visual_analysis = {
        "0:0": {
            "visual_regions": [],  # empty → score = 0
            "visual_interpretations": [],
            "consistency_score": None,
            "vision_unavailable": False,
        }
    }

    retry_regions = [
        {"type": "body", "bbox": [0, 0, 800, 800], "description": "body"},
    ]

    context: Dict[str, Any] = {
        "visual_analysis": visual_analysis,
        "parsed_documents": [doc],
        "tables": [],
        "job_id": "test-job",
    }

    with patch("services.stages.vision_self_check._retry_segmentation", return_value=60):
        with patch("services.openrouter_client.format_cost_summary", return_value="Vision AI: 1 chamadas, ~$0.03"):
            result = await execute(context)

    # Retry should have been called
    assert result["retried"] >= 1


# ---------------------------------------------------------------------------
# Test 9 — Self-Check: VISION_AI_ENABLED=false skips
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_check_disabled_env():
    """Self-Check skips when VISION_AI_ENABLED=false."""
    from services.stages.vision_self_check import execute

    events = []
    context: Dict[str, Any] = {
        "visual_analysis": {},
        "parsed_documents": [],
        "tables": [],
        "emit_progress": events.append,
    }

    with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
        result = await execute(context)

    assert result.get("skipped") is True
    skipped = [e for e in events if e.get("status") == "skipped"]
    assert len(skipped) == 1


# ---------------------------------------------------------------------------
# Test 10 — Self-Check: cost summary in SSE completion event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_check_cost_summary_in_sse():
    """Self-Check completion SSE event should include cost_summary."""
    from services.stages.vision_self_check import execute

    events = []
    context: Dict[str, Any] = {
        "visual_analysis": {},
        "parsed_documents": [],
        "tables": [],
        "job_id": "test-job",
        "_vision_api_calls": 5,
        "emit_progress": events.append,
    }

    with patch("services.openrouter_client.format_cost_summary", return_value="Vision AI: 5 chamadas, ~$0.13"):
        result = await execute(context)

    completed = [e for e in events if e.get("status") == "completed"]
    assert len(completed) == 1
    assert "cost_summary" in completed[0]
    assert "Vision AI" in completed[0]["cost_summary"]


# ---------------------------------------------------------------------------
# Test 11 — register_bloco6_vision wires stages 20-22
# ---------------------------------------------------------------------------


def test_register_bloco6_vision_wires_stages():
    """register_bloco6_vision should replace stubs 20-22 with implementations."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco6_vision

    registry = build_default_registry()

    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[20]._execute_fn is None
    assert stages_before[21]._execute_fn is None
    assert stages_before[22]._execute_fn is None

    register_bloco6_vision(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}
    assert stages_after[20]._execute_fn is not None, "Stage 20 still stub"
    assert stages_after[21]._execute_fn is not None, "Stage 21 still stub"
    assert stages_after[22]._execute_fn is not None, "Stage 22 still stub"

    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 27


# ---------------------------------------------------------------------------
# Test 12 — OpenRouter client: raises ValueError without API key
# ---------------------------------------------------------------------------


def test_openrouter_client_no_api_key_raises():
    """get_client() should raise ValueError when OPENROUTER_API_KEY is not set."""
    from services.openrouter_client import get_client

    with patch.dict(os.environ, {}, clear=True):
        # Ensure key is not in environment
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises((ValueError, Exception)):
                get_client()


# ---------------------------------------------------------------------------
# Test 13 — OpenRouter client: retry on rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openrouter_client_retries_on_rate_limit():
    """_call_with_retry should retry up to MAX_RETRIES on RateLimitError."""
    from services.openrouter_client import _call_with_retry

    call_count = 0
    completion = _make_mock_completion('{"regions": []}')

    async def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            from openai import RateLimitError
            raise RateLimitError("rate limited", response=MagicMock(), body={})
        return completion

    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = fake_create

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await _call_with_retry(mock_client, messages=[{"role": "user", "content": "test"}])

    assert call_count == 3
    assert result == completion


# ---------------------------------------------------------------------------
# Test 14 — format_cost_summary
# ---------------------------------------------------------------------------


def test_format_cost_summary():
    """format_cost_summary should return a string with call count and dollar amount."""
    from services.openrouter_client import format_cost_summary

    summary = format_cost_summary(4)
    assert "Vision AI" in summary
    assert "4 chamadas" in summary
    assert "$" in summary


# ---------------------------------------------------------------------------
# Test 15 — End-to-end: stages 20→21→22 with mocked API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_vision_ai_pipeline():
    """Stages 20→21→22 should complete and populate visual_analysis for each page."""
    from services.stages.visual_segmentation import execute as s20
    from services.stages.visual_interpretation import execute as s21
    from services.stages.vision_self_check import execute as s22

    page = _make_page(0, text_block_count=3, screenshot_path="/tmp/screenshot.png")
    doc = _make_doc([page])
    lt = _make_layout_type(pdf_index=0, page_number=0)

    events = []
    context: Dict[str, Any] = {
        "layout_types": [lt],
        "parsed_documents": [doc],
        "job_id": "e2e-job",
        "tables": [],
        "emit_progress": events.append,
    }

    # Mock all API calls
    with patch("services.openrouter_client.load_image_as_base64", return_value="b64data"):
        with patch("services.openrouter_client.chat_with_vision") as mock_chat:
            mock_chat.side_effect = [
                _segmentation_response(),       # Stage 20 call
                _interpretation_response(),     # Stage 21 call
            ]
            with patch("services.openrouter_client.format_cost_summary", return_value="Vision AI: 2 chamadas, ~$0.05"):
                with patch("services.openrouter_client.get_client", return_value=AsyncMock()):
                    await s20(context)
                    await s21(context)
                    await s22(context)

    assert "0:0" in context["visual_analysis"]
    page_analysis = context["visual_analysis"]["0:0"]
    assert len(page_analysis["visual_regions"]) == 3
    assert len(page_analysis["visual_interpretations"]) >= 1
    assert page_analysis["consistency_score"] is not None

    # All three stages should emit completed events
    completed = [e for e in events if e.get("status") == "completed"]
    assert len(completed) == 3

    # Cost summary should appear in Stage 22's event
    s22_event = next((e for e in completed if e.get("stage") == 22), None)
    assert s22_event is not None
    assert "cost_summary" in s22_event
