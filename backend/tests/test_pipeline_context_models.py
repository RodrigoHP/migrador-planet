"""Tests for pipeline context typed models — Story 40.7.

Validates:
  - Pydantic model construction from dict data (backward compat)
  - PipelineContext wrapper typed access
  - Stage output models validate correctly
  - Models reject invalid data appropriately
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure backend is on sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models.pipeline_context import (  # noqa: E402
    Cluster,
    ClusterConfidence,
    ClusterIntelligence,
    ConfidenceScoreEntry,
    EnrichedDocument,
    EnrichedPage,
    FieldMappingEntry,
    LayoutTypeInfo,
    PageReference,
    PdfDocument,
    PipelineContext,
    PipelineResult,
    PipelineWarning,
    Stage1Output,
    Stage2Output,
    Stage3Output,
    Stage4Output,
    Stage5Result,
    StageDefinition,
    SubProgressEvent,
    ValidationResult,
)

# ---------------------------------------------------------------------------
# PageReference
# ---------------------------------------------------------------------------


class TestPageReference:
    def test_basic_construction(self):
        ref = PageReference(pdf_id="pdf-1", page_index=0)
        assert ref.pdf_id == "pdf-1"
        assert ref.page_index == 0

    def test_from_dict(self):
        data = {"pdf_id": "pdf-2", "page_index": 3}
        ref = PageReference(**data)
        assert ref.pdf_id == "pdf-2"
        assert ref.page_index == 3

    def test_serialization_roundtrip(self):
        ref = PageReference(pdf_id="abc", page_index=5)
        d = ref.model_dump()
        ref2 = PageReference(**d)
        assert ref == ref2


# ---------------------------------------------------------------------------
# ClusterConfidence
# ---------------------------------------------------------------------------


class TestClusterConfidence:
    def test_defaults(self):
        cc = ClusterConfidence()
        assert cc.confidence == 0.0
        assert cc.level == "low"
        assert cc.factors == {}

    def test_from_pipeline_data(self):
        data = {"confidence": 0.95, "level": "high", "factors": {"consensus": True}}
        cc = ClusterConfidence(**data)
        assert cc.confidence == 0.95
        assert cc.level == "high"


# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------


class TestCluster:
    def test_from_stage1_output(self):
        """Cluster model can be constructed from actual Stage 1 output format."""
        data = {
            "cluster_id": "A",
            "pages": [
                {"pdf_id": "p1", "page_index": 0},
                {"pdf_id": "p1", "page_index": 1},
            ],
            "representative_page": {"pdf_id": "p1", "page_index": 0},
            "page_count": 2,
            "confidence": {"confidence": 0.92, "level": "high", "factors": {}},
        }
        cluster = Cluster(**data)
        assert cluster.cluster_id == "A"
        assert len(cluster.pages) == 2
        assert cluster.pages[0].pdf_id == "p1"
        assert cluster.get_confidence_value() == 0.92

    def test_confidence_as_float(self):
        """Cluster accepts raw float confidence (special clusters)."""
        data = {
            "cluster_id": "_blank",
            "pages": [{"pdf_id": "p1", "page_index": 5}],
            "representative_page": {"pdf_id": "p1", "page_index": 5},
            "page_count": 1,
            "confidence": 1.0,
        }
        cluster = Cluster(**data)
        assert cluster.get_confidence_value() == 1.0


class TestStage1Output:
    def test_construction(self):
        out = Stage1Output(
            clusters=[
                Cluster(
                    cluster_id="A",
                    pages=[PageReference(pdf_id="p1", page_index=0)],
                    representative_page=PageReference(pdf_id="p1", page_index=0),
                    page_count=1,
                )
            ],
            raw_text_blocks={"p1:0": [{"x0": 0, "y0": 0, "text": "hello"}]},
        )
        assert len(out.clusters) == 1
        assert "p1:0" in out.raw_text_blocks


# ---------------------------------------------------------------------------
# Stage 2 models
# ---------------------------------------------------------------------------


class TestEnrichedPage:
    def test_from_stage2_output(self):
        """EnrichedPage can be constructed from actual Stage 2 page_data."""
        data = {
            "page_index": 0,
            "cluster_id": "A",
            "is_representative": True,
            "width": 595.0,
            "height": 842.0,
            "text_blocks": [{"id": "b1", "text": "Hello", "bbox": [0, 0, 100, 20]}],
            "images": [],
            "fonts": [{"name": "Helvetica", "css_family": "Arial"}],
            "grid_info": {"columns": [100, 300], "column_count": 2},
            "screenshot_path": "/tmp/s.png",
            "tables": [],
            "drawn_elements": [],
        }
        page = EnrichedPage(**data)
        assert page.page_index == 0
        assert page.is_representative is True
        assert page.width == 595.0


class TestEnrichedDocument:
    def test_from_stage2_output(self):
        doc = EnrichedDocument(
            pdf_id="p1",
            pdf_name="test.pdf",
            pages=[
                EnrichedPage(page_index=0, cluster_id="A", is_representative=True, width=595.0, height=842.0),
            ],
        )
        assert doc.pdf_id == "p1"
        assert len(doc.pages) == 1


class TestStage2Output:
    def test_construction(self):
        out = Stage2Output(
            enriched_documents=[
                EnrichedDocument(pdf_id="p1", pages=[]),
            ],
            extraction_warnings=[{"warning_type": "low_quality", "message": "test"}],
        )
        assert len(out.enriched_documents) == 1
        assert len(out.extraction_warnings) == 1


# ---------------------------------------------------------------------------
# Stage 3 models
# ---------------------------------------------------------------------------


class TestClusterIntelligence:
    def test_from_stage3_data(self):
        data = {
            "block_classifications": {
                "b1": {"semantic": "label", "confidence": 0.9},
                "b2": {"semantic": "dynamic", "confidence": 0.85},
            },
            "labels": ["b1"],
            "dynamic_fields": ["b2"],
            "optional_fields": [],
            "conditional_fields": [],
            "classification_quality": {"total_pdfs": 2, "statistical_strength": "strong"},
        }
        intel = ClusterIntelligence(**data)
        assert len(intel.labels) == 1
        assert len(intel.dynamic_fields) == 1


class TestLayoutTypeInfo:
    def test_from_stage3_data(self):
        data = {
            "id": "A",
            "cluster_id": "A",
            "name": "A",
            "page_width_pts": 595.0,
            "page_height_pts": 842.0,
            "page_count": 3,
        }
        lt = LayoutTypeInfo(**data)
        assert lt.id == "A"
        assert lt.page_count == 3


class TestStage3Output:
    def test_construction(self):
        out = Stage3Output(
            document_trees={"A": {"id": "root", "type": "document", "children": []}},
            intelligence={"A": ClusterIntelligence(labels=["b1"])},
            visual_analysis={},
            label_value_pairs={},
            layout_types=[LayoutTypeInfo(id="A", cluster_id="A", name="A")],
        )
        assert "A" in out.document_trees
        assert "A" in out.intelligence


# ---------------------------------------------------------------------------
# Stage 4 models
# ---------------------------------------------------------------------------


class TestFieldMappingEntry:
    def test_from_stage4_data(self):
        data = {
            "id": "fm-1",
            "pdf_text": "R$ 1.234,56",
            "label_text": "Valor Total",
            "xsd_field_path": "/nfe/total/valor",
            "layout_type_id": "A",
            "confidence": 0.87,
            "detected_format": "currency_brl",
            "status": "mapped",
        }
        fm = FieldMappingEntry(**data)
        assert fm.xsd_field_path == "/nfe/total/valor"
        assert fm.detected_format == "currency_brl"


class TestValidationResult:
    def test_from_stage4_data(self):
        vr = ValidationResult(
            warnings=[{"msg": "orphan field"}],
            errors=[],
            orphans=["b5"],
            unmapped_required=["/nfe/dest/cnpj"],
        )
        assert len(vr.warnings) == 1
        assert len(vr.unmapped_required) == 1


class TestStage4Output:
    def test_construction(self):
        out = Stage4Output(
            field_tree={"flat_paths": ["/a", "/b"]},
            field_mappings=[{"id": "fm-1"}],
            format_functions={"currency_brl": "function(){}"},
            confidence_scores={"A": {"overall": 0.85}},
            validation_result=ValidationResult(),
        )
        assert out.field_tree is not None
        assert len(out.field_mappings) == 1


# ---------------------------------------------------------------------------
# Stage 5 models
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_from_result_json(self):
        """PipelineResult can be constructed from Stage 5 result_json."""
        data = {
            "layout_types": [{"id": "A", "name": "Layout A"}],
            "field_mappings": [{"id": "fm-1"}],
            "trees_by_layout": {"A": {"id": "root"}},
            "document_structure": {"pages": 5},
            "confidence_scores": {"A": {"overall": 0.9}},
            "coverage": {"A": 0.85},
            "template_draft": {"html": "<div/>", "css": "body{}"},
            "template_name": "test-template",
        }
        result = PipelineResult(**data)
        assert result.template_name == "test-template"
        assert len(result.layout_types) == 1


class TestStage5Result:
    def test_construction(self):
        s5 = Stage5Result(
            template_draft={"html": "<div/>"},
            coverage={"A": 0.85},
            overlay_count=42,
            multi_doc_pdfs=3,
        )
        assert s5.overlay_count == 42


# ---------------------------------------------------------------------------
# StageDefinition & SubProgressEvent
# ---------------------------------------------------------------------------


class TestStageDefinition:
    def test_construction(self):
        sd = StageDefinition(stage=1, name="Layout Clustering", weight=0.20)
        assert sd.stage == 1
        assert sd.weight == 0.20


class TestSubProgressEvent:
    def test_from_make_sub_progress(self):
        """SubProgressEvent validates the output of make_sub_progress_event."""
        data = {
            "stage": 1,
            "stage_name": "Layout Clustering",
            "status": "running",
            "progress_pct": 0.15,
            "sub_step": "1.2 Block Extraction",
            "sub_progress_pct": 0.12,
            "summary": {"pages_processed": 10},
        }
        event = SubProgressEvent(**data)
        assert event.stage == 1
        assert event.progress_pct == 0.15


# ---------------------------------------------------------------------------
# PipelineContext wrapper
# ---------------------------------------------------------------------------


class TestPipelineContext:
    def test_empty_context(self):
        ctx = PipelineContext()
        assert ctx.current_stage == 0
        assert ctx.pdf_documents == []
        assert ctx.clusters == []

    def test_initialized_context(self):
        ctx = PipelineContext(
            {
                "_storage": "mock_storage",
                "_current_stage": 0,
                "pdf_documents": [{"id": "p1", "path": "/tmp/p1.pdf", "name": "p1.pdf"}],
                "xsd_path": "/tmp/schema.xsd",
                "job_id": "job-123",
                "_job": {"job_id": "job-123"},
            }
        )
        assert ctx.storage == "mock_storage"
        assert ctx.job_id == "job-123"
        assert len(ctx.pdf_documents) == 1

    def test_stage1_writes(self):
        ctx = PipelineContext({})
        ctx.clusters = [{"cluster_id": "A", "pages": []}]
        ctx.raw_text_blocks = {"p1:0": [{"text": "hello"}]}
        assert len(ctx.clusters) == 1
        assert "p1:0" in ctx.raw_text_blocks

    def test_stage2_writes(self):
        ctx = PipelineContext({})
        ctx.enriched_documents = [{"pdf_id": "p1", "pages": []}]
        assert len(ctx.enriched_documents) == 1

    def test_stage3_writes(self):
        ctx = PipelineContext({})
        ctx.document_trees = {"A": {"id": "root"}}
        ctx.intelligence = {"A": {"labels": ["b1"]}}
        ctx.layout_types = [{"id": "A"}]
        assert "A" in ctx.document_trees

    def test_stage4_writes(self):
        ctx = PipelineContext({})
        ctx.field_mappings = [{"id": "fm-1"}]
        ctx.confidence_scores = {"A": {"overall": 0.9}}
        ctx.validation_result = {"warnings": [], "errors": []}
        assert len(ctx.field_mappings) == 1

    def test_stage5_writes(self):
        ctx = PipelineContext({})
        ctx.result_json = {"layout_types": []}
        assert "layout_types" in ctx.result_json

    def test_to_dict_returns_same_reference(self):
        data: dict[str, Any] = {"key": "value"}
        ctx = PipelineContext(data)
        assert ctx.to_dict() is data

    def test_dict_interface(self):
        ctx = PipelineContext({"clusters": [{"id": "A"}]})
        assert "clusters" in ctx
        assert ctx["clusters"] == [{"id": "A"}]
        ctx["new_key"] = "new_value"
        assert ctx.get("new_key") == "new_value"
        assert ctx.get("missing", "default") == "default"

    def test_setdefault(self):
        ctx = PipelineContext({})
        result = ctx.setdefault("_pipeline_warnings", [])
        assert result == []
        ctx.setdefault("_pipeline_warnings", ["should not replace"])
        assert ctx["_pipeline_warnings"] == []

    def test_vision_api_tracking(self):
        ctx = PipelineContext({})
        ctx.vision_api_calls = 5
        ctx.vision_api_cost = 0.0125
        assert ctx.vision_api_calls == 5
        assert ctx.vision_api_cost == 0.0125

    def test_backward_compatible_with_raw_dict(self):
        """PipelineContext wraps the same dict — changes reflect in both."""
        raw: dict[str, Any] = {}
        ctx = PipelineContext(raw)
        ctx.clusters = [{"id": "X"}]
        assert raw["clusters"] == [{"id": "X"}]
        raw["field_mappings"] = [{"id": "fm-1"}]
        assert ctx.field_mappings == [{"id": "fm-1"}]


# ---------------------------------------------------------------------------
# PdfDocument & PipelineWarning
# ---------------------------------------------------------------------------


class TestPdfDocument:
    def test_from_input(self):
        doc = PdfDocument(id="p1", path="/tmp/test.pdf", name="test.pdf")
        assert doc.id == "p1"

    def test_from_dict(self):
        data = {"id": "p2", "path": "/tmp/p2.pdf"}
        doc = PdfDocument(**data)
        assert doc.name == ""


class TestPipelineWarning:
    def test_construction(self):
        w = PipelineWarning(code="spacy_unavailable", severity="info", message="NER disabled", stage=3)
        assert w.code == "spacy_unavailable"
        assert w.stage == 3


# ---------------------------------------------------------------------------
# ConfidenceScoreEntry
# ---------------------------------------------------------------------------


class TestConfidenceScoreEntry:
    def test_from_stage4_data(self):
        data = {
            "layout_stability": 0.9,
            "anchor_detection": 0.8,
            "grid_quality": 0.85,
            "field_variability": 0.7,
            "vision_agreement": 0.95,
            "overall": 0.84,
            "level": "high",
        }
        cs = ConfidenceScoreEntry(**data)
        assert cs.overall == 0.84
        assert cs.level == "high"


# ---------------------------------------------------------------------------
# Extra fields (model_config extra=allow)
# ---------------------------------------------------------------------------


class TestExtraFieldsAllowed:
    """Models with extra='allow' accept unexpected keys from pipeline data."""

    def test_enriched_page_extra_fields(self):
        page = EnrichedPage(
            page_index=0,
            cluster_id="A",
            extra_field="should not crash",
        )
        assert page.page_index == 0

    def test_field_mapping_entry_extra(self):
        fm = FieldMappingEntry(
            id="fm-1",
            pdf_text="test",
            some_new_field=True,
        )
        assert fm.id == "fm-1"
