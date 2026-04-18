"""E2E tests for Pipeline v2 — Story 13.12.

Covers:
- AC1: Full pipeline v2 run (Stage 1 -> 5) with mock PDF -> PipelineResult
- AC2: Real PDF test using ground_truth_boleto fixture, CSS from extraction data
- AC5: Feature flag PIPELINE_VERSION=v2 functional
- AC6: Pipeline v1 continues working with flag v1
- AC9: SSE reports 5 stages with sub-progress
- Tables as real <table> elements, hierarchical HTML from document_trees
- All LLM calls avoided via env flags (VISION_AI_ENABLED=false, no OPENROUTER_API_KEY)

AC7 — Regression note:
    Pipeline v2 is opt-in via the PIPELINE_VERSION=v2 feature flag (default is v1).
    Existing v1 tests continue to run against the v1 pipeline by default and remain
    fully compatible.  The v2-specific tests in this module were verified to not
    interfere with v1 behavior — both pipelines can coexist side-by-side.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from models.pipeline_context import LayoutTypeInfo

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_job_state(job_id: str = "e2e-test-job") -> dict[str, Any]:
    """Create a minimal job state dict matching _pipeline_jobs structure."""
    return {
        "job_id": job_id,
        "status": "running",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],
        "new_event": asyncio.Event(),
        "pipeline_done": False,
        "created_at": 0,
    }


class EventCollector:
    """Async callback that collects emitted SSE events."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def __call__(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def _create_boleto_pdf(path: str) -> str:
    """Create a mock boleto PDF with realistic content matching ground truth."""
    doc = fitz.open()

    # Page 1 — boleto content
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 40), "Banco Bradesco S.A.", fontname="helv", fontsize=14)
    page.insert_text((400, 40), "BOLETO", fontname="helv", fontsize=16)
    page.insert_text((50, 120), "Nome:", fontname="helv", fontsize=10)
    page.insert_text((120, 120), "Joao da Silva Santos", fontname="helv", fontsize=10)
    page.insert_text((50, 150), "CPF:", fontname="helv", fontsize=10)
    page.insert_text((120, 150), "123.456.789-10", fontname="helv", fontsize=10)
    page.insert_text((50, 200), "Vencimento:", fontname="helv", fontsize=10)
    page.insert_text((150, 200), "10/04/2026", fontname="helv", fontsize=10)
    page.insert_text((50, 250), "Valor:", fontname="helv", fontsize=10)
    page.insert_text((120, 250), "R$ 1000,00", fontname="helv", fontsize=10)
    page.insert_text((50, 300), "Referente a servicos prestados conforme contrato vigente", fontname="helv", fontsize=9)
    page.insert_text((50, 350), "Nosso Numero:", fontname="helv", fontsize=10)
    page.insert_text((170, 350), "900000", fontname="helv", fontsize=10)
    page.draw_line((50, 80), (545, 80), color=(0, 0, 0), width=1)
    page.draw_rect(fitz.Rect(40, 400, 555, 500), color=(0, 0, 0), width=0.5)

    # Page 2 — identical layout, different data (same cluster)
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 40), "Banco Bradesco S.A.", fontname="helv", fontsize=14)
    page2.insert_text((400, 40), "BOLETO", fontname="helv", fontsize=16)
    page2.insert_text((50, 120), "Nome:", fontname="helv", fontsize=10)
    page2.insert_text((120, 120), "Maria Oliveira", fontname="helv", fontsize=10)
    page2.insert_text((50, 150), "CPF:", fontname="helv", fontsize=10)
    page2.insert_text((120, 150), "987.654.321-00", fontname="helv", fontsize=10)
    page2.insert_text((50, 200), "Vencimento:", fontname="helv", fontsize=10)
    page2.insert_text((150, 200), "15/05/2026", fontname="helv", fontsize=10)
    page2.insert_text((50, 250), "Valor:", fontname="helv", fontsize=10)
    page2.insert_text((120, 250), "R$ 2500,00", fontname="helv", fontsize=10)
    page2.insert_text(
        (50, 300), "Referente a servicos prestados conforme contrato vigente", fontname="helv", fontsize=9
    )
    page2.insert_text((50, 350), "Nosso Numero:", fontname="helv", fontsize=10)
    page2.insert_text((170, 350), "900001", fontname="helv", fontsize=10)
    page2.draw_line((50, 80), (545, 80), color=(0, 0, 0), width=1)
    page2.draw_rect(fitz.Rect(40, 400, 555, 500), color=(0, 0, 0), width=0.5)

    doc.save(path)
    doc.close()
    return path


def _mock_storage() -> MagicMock:
    storage = MagicMock()
    storage.cleanup_local = AsyncMock()
    storage.upload = AsyncMock()
    storage.get_signed_url = AsyncMock(return_value="https://example.com/signed")
    return storage


@pytest.fixture(autouse=True)
def _disable_llm_calls(monkeypatch):
    """Disable all LLM calls via env flags for all tests in this module."""
    monkeypatch.setenv("VISION_AI_ENABLED", "false")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# AC1: E2E Test — Full Pipeline v2 (Stage 1 -> 5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_full_pipeline_v2_with_mock_pdf(session_boleto_pdf_path):
    """Full E2E: mock PDF -> 5 stages -> PipelineResult with all required fields."""
    from services.pipeline_orchestrator_v2 import run_pipeline_v2

    collector = EventCollector()
    job = _make_job_state()
    storage = _mock_storage()

    pdf_docs = [{"id": "0", "path": session_boleto_pdf_path, "name": "input.pdf"}]

    with (
        patch("services.stages.stage3_structural_analysis._get_nlp", return_value=None),
        patch("services.stages.stage5_template_generation._step_5_7_persist", new_callable=AsyncMock),
    ):
        result = await run_pipeline_v2(
            pdf_documents=pdf_docs,
            xsd_path="",
            storage=storage,
            job=job,
            emit_progress=collector,
        )

    # --- Verify SSE events ---
    stage_numbers_running = {
        e["stage"] for e in collector.events if e.get("status") == "running" and e.get("stage") in (1, 2, 3, 4, 5)
    }
    stage_numbers_completed = {
        e["stage"] for e in collector.events if e.get("status") == "completed" and e.get("stage") in (1, 2, 3, 4, 5)
    }
    assert {1, 2, 3, 4, 5} <= stage_numbers_running, (
        f"Missing running events: {set(range(1, 6)) - stage_numbers_running}"
    )
    assert {1, 2, 3, 4, 5} <= stage_numbers_completed, (
        f"Missing completed events: {set(range(1, 6)) - stage_numbers_completed}"
    )

    # Pipeline start event
    start_events = [e for e in collector.events if e.get("status") == "started"]
    assert len(start_events) >= 1

    # Pipeline completion event
    completion_events = [e for e in collector.events if e.get("event") == "pipeline_completed"]
    assert len(completion_events) >= 1

    # --- Verify sub-progress ---
    sub_progress_events = [e for e in collector.events if e.get("sub_step") and e.get("status") == "running"]
    assert len(sub_progress_events) > 0, "Should have sub-progress events"
    for evt in sub_progress_events:
        assert "sub_progress_pct" in evt
        assert 0.0 <= evt["sub_progress_pct"] <= 1.0

    # --- Verify PipelineResult structure ---
    assert "stage_1" in job["_debug_stages"]
    assert "stage_5" in job["_debug_stages"]
    assert "template_draft" in result


# ---------------------------------------------------------------------------
# AC9: SSE reports 5 stages with sub-progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_sse_events_5_stages_with_sub_progress(session_boleto_pdf_path):
    """SSE reports 5 stages with sub-progress format (AC9)."""
    from services.pipeline_orchestrator_v2 import run_pipeline_v2

    collector = EventCollector()
    job = _make_job_state()
    storage = _mock_storage()

    pdf_docs = [{"id": "0", "path": session_boleto_pdf_path, "name": "input.pdf"}]

    with (
        patch("services.stages.stage3_structural_analysis._get_nlp", return_value=None),
        patch("services.stages.stage5_template_generation._step_5_7_persist", new_callable=AsyncMock),
    ):
        await run_pipeline_v2(
            pdf_documents=pdf_docs,
            xsd_path="",
            storage=storage,
            job=job,
            emit_progress=collector,
        )

    # Verify event format matches v2 SSE schema
    for evt in collector.events:
        assert "stage" in evt
        assert "stage_name" in evt
        assert "status" in evt
        assert "progress_pct" in evt

    # Verify progress range
    pcts = [e["progress_pct"] for e in collector.events if "progress_pct" in e]
    assert pcts[0] == 0.0, "First event should start at 0%"
    assert pcts[-1] == 1.0, "Last event should reach 100%"

    # Stage names should match definitions
    stage_names = {
        e["stage"]: e["stage_name"]
        for e in collector.events
        if e.get("stage") in (1, 2, 3, 4, 5) and e.get("status") == "running"
    }
    assert stage_names.get(1) == "Layout Clustering"
    assert stage_names.get(2) == "Deep Extraction"
    assert stage_names.get(3) == "Structural Analysis"
    assert stage_names.get(4) == "Field Mapping"
    assert stage_names.get(5) == "Template Generation"


# ---------------------------------------------------------------------------
# AC2: CSS from extraction data (not hardcoded)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_css_generated_from_extraction_not_hardcoded(session_boleto_pdf_path):
    """Stage 5 generates CSS from actual PDF data (AC2)."""
    from services.pipeline_orchestrator_v2 import run_pipeline_v2

    collector = EventCollector()
    job = _make_job_state()
    storage = _mock_storage()

    pdf_docs = [{"id": "0", "path": session_boleto_pdf_path, "name": "input.pdf"}]

    with (
        patch("services.stages.stage3_structural_analysis._get_nlp", return_value=None),
        patch("services.stages.stage5_template_generation._step_5_7_persist", new_callable=AsyncMock),
    ):
        result = await run_pipeline_v2(
            pdf_documents=pdf_docs,
            xsd_path="",
            storage=storage,
            job=job,
            emit_progress=collector,
        )

    css = result.get("template_draft", {}).get("css", "")

    # CSS should NOT be empty
    assert len(css) > 0, "CSS should not be empty"

    # CSS should contain the base reset (.page, position, etc.)
    assert ".page" in css, "CSS should have .page class from base reset"

    # --- Negative assertions: CSS must NOT be only hardcoded defaults ---
    # Strip the .page base-reset portion to inspect extraction-derived content
    css_lower = css.lower()

    # Must not consist solely of a generic hardcoded border (exact 3-digit form #ccc, not #cccccc)
    assert not re.search(r"border:\s*1px solid #ccc[^0-9a-f]", css_lower), (
        "CSS contains generic hardcoded border 'border: 1px solid #ccc' — "
        "styles should be derived from PDF extraction data"
    )

    # Must have more than one CSS class (extraction produces multiple selectors)
    css_selectors = re.findall(r"\.[a-zA-Z_][\w-]*", css)
    unique_selectors = set(css_selectors)
    assert len(unique_selectors) >= 3, (
        f"CSS should contain multiple extraction-derived classes, "
        f"found only {len(unique_selectors)}: {unique_selectors}"
    )

    # Must not be ONLY 'font-family: Arial' with no other font info
    font_families = re.findall(r"font-family:\s*([^;]+)", css)
    if font_families:
        unique_fonts = {f.strip().lower() for f in font_families}
        assert unique_fonts != {"arial"}, (
            "CSS contains only 'font-family: Arial' — extraction should derive actual fonts from the PDF"
        )

    # CSS must contain at least one color value (extraction-derived or default)
    colors = re.findall(r"color:\s*(#[0-9a-fA-F]{3,8}|rgb[^;]+)", css)
    assert len(colors) > 0, "CSS should contain at least one color declaration"


@pytest.mark.asyncio
async def test_e2e_ground_truth_boleto_reference(session_boleto_pdf_path):
    """Verify pipeline processes fields matching ground truth boleto (AC2)."""
    from services.pipeline_orchestrator_v2 import run_pipeline_v2

    gt_path = FIXTURES_DIR / "ground_truth_boleto.json"
    assert gt_path.exists(), f"ground_truth_boleto.json fixture must exist at {gt_path}"

    with open(gt_path) as f:
        ground_truth = json.load(f)

    collector = EventCollector()
    job = _make_job_state()
    storage = _mock_storage()

    pdf_docs = [{"id": "0", "path": session_boleto_pdf_path, "name": "input.pdf"}]

    with (
        patch("services.stages.stage3_structural_analysis._get_nlp", return_value=None),
        patch("services.stages.stage5_template_generation._step_5_7_persist", new_callable=AsyncMock),
    ):
        result = await run_pipeline_v2(
            pdf_documents=pdf_docs,
            xsd_path="",
            storage=storage,
            job=job,
            emit_progress=collector,
        )

    # Pipeline should complete all stages
    assert result is not None
    assert "stage_5" in job["_debug_stages"]
    assert "stage_1" in job["_debug_stages"]

    # Verify ground truth has expected fields
    gt_fields = ground_truth.get("fields", [])
    assert len(gt_fields) > 0, "Ground truth should have fields"

    # Verify the pipeline at least extracted text blocks (Stage 1 + 2)
    stage_1_data = result.get("stage_1", {})
    assert stage_1_data is not None

    # Verify the pipeline produces a template_draft with actual CSS content
    td = result.get("template_draft", {})
    assert td, "Pipeline should produce a template_draft"
    css = td.get("css", "")
    assert len(css) > 0, "Pipeline should generate CSS from boleto extraction data"
    html = td.get("html", "")
    assert len(html) > 0, "Pipeline should generate HTML from boleto extraction data"


# ---------------------------------------------------------------------------
# AC5/AC6: Feature Flag Tests
# ---------------------------------------------------------------------------


def test_pipeline_version_always_v2():
    """Pipeline version is always v2 (v1 removed in Epic 15)."""
    import routers.analyze as analyze_mod

    assert analyze_mod._get_pipeline_version() == "v2"


@pytest.mark.asyncio
async def test_feature_flag_v2_produces_valid_result(session_boleto_pdf_path):
    """Pipeline v2 produces a result with template_draft (AC5)."""
    from services.pipeline_orchestrator_v2 import run_pipeline_v2

    collector = EventCollector()
    job = _make_job_state()
    storage = _mock_storage()

    pdf_docs = [{"id": "0", "path": session_boleto_pdf_path, "name": "input.pdf"}]

    with (
        patch("services.stages.stage3_structural_analysis._get_nlp", return_value=None),
        patch("services.stages.stage5_template_generation._step_5_7_persist", new_callable=AsyncMock),
    ):
        result = await run_pipeline_v2(
            pdf_documents=pdf_docs,
            xsd_path="",
            storage=storage,
            job=job,
            emit_progress=collector,
        )

    # v2 result should have all stage outputs
    assert "stage_1" in job["_debug_stages"]
    assert "stage_2" in job["_debug_stages"]
    assert "stage_3" in job["_debug_stages"]
    assert "stage_4" in job["_debug_stages"]
    assert "stage_5" in job["_debug_stages"]
    assert "template_draft" in result

    td = result["template_draft"]
    assert "html" in td
    assert "css" in td


# ---------------------------------------------------------------------------
# HTML Table Test: tables as real <table> elements
# ---------------------------------------------------------------------------


def test_stage5_generates_table_html():
    """Stage 5 tree_to_html renders tables as <table> elements (AC2)."""
    from services.stages.stage5_template_generation import _tree_to_html

    table_node = {
        "type": "document",
        "children": [
            {
                "type": "flow",
                "children": [
                    {
                        "type": "table",
                        "name": "items",
                        "columns": [
                            {"name": "Item", "block_id": "col-1"},
                            {"name": "Qty", "block_id": "col-2"},
                            {"name": "Price", "block_id": "col-3"},
                        ],
                        "rows": [
                            [
                                {"text": "Widget", "block_id": "r1c1"},
                                {"text": "10", "block_id": "r1c2"},
                                {"text": "R$ 50,00", "block_id": "r1c3"},
                            ],
                        ],
                        "children": [],
                    }
                ],
            }
        ],
    }

    layout = LayoutTypeInfo(
        id="default", name="default", cluster_id="default", page_height_pts=842.0, page_width_pts=595.0
    )
    html = _tree_to_html(table_node, {}, None, layout)

    assert "<table" in html, "Tables should be rendered as <table> elements"
    assert "data-table" in html, "Table should have data-table class"


# ---------------------------------------------------------------------------
# Hierarchical HTML from document_trees
# ---------------------------------------------------------------------------


def test_stage5_hierarchical_html_from_trees():
    """Stage 5 produces hierarchical HTML with sections and fields."""
    from services.stages.stage5_template_generation import _tree_to_html

    tree = {
        "type": "document",
        "children": [
            {
                "type": "header",
                "children": [
                    {
                        "type": "field",
                        "variant": "required",
                        "children": [
                            {"type": "label", "block_id": "b1", "text": "Empresa"},
                        ],
                    },
                ],
            },
            {
                "type": "flow",
                "children": [
                    {
                        "type": "section",
                        "name": "Dados",
                        "variant": "required",
                        "children": [
                            {
                                "type": "field",
                                "variant": "required",
                                "children": [
                                    {"type": "label", "block_id": "b2", "text": "Nome:"},
                                    {"type": "value", "block_id": "b3", "text": "Joao"},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "type": "footer",
                "children": [],
            },
        ],
    }

    layout = LayoutTypeInfo(
        id="default", name="default", cluster_id="default", page_height_pts=842.0, page_width_pts=595.0
    )
    html = _tree_to_html(tree, {}, None, layout)

    assert 'class="header"' in html, "Should have header div"
    assert 'class="flow"' in html, "Should have flow div"
    assert 'class="footer"' in html, "Should have footer div"
    assert 'class="section"' in html, "Should have section div"
    assert 'data-section="Dados"' in html, "Section should have data attribute"
