"""Pipeline Context typed models — Pydantic V2.

Story 40.7 — Replaces Dict[str, Any] pipeline context with typed models.
Defines Pydantic models for data flowing between pipeline stages and a
TypedDict for the mutable pipeline context.

Architecture:
  - PipelineContext (TypedDict): top-level mutable dict passed through stages
  - Stage-specific models: Pydantic BaseModel for structured data
  - Backward compatible: models can be constructed from existing dict data
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Shared / Atomic Models
# ---------------------------------------------------------------------------


class BlockInfo(BaseModel):
    """A normalised/abstracted text block from Stage 1 page preprocessing.

    Story 42.10 — typed replacement for plain dicts in PageInfo.core_blocks.
    """

    text_abstract: str
    bbox_norm: list[float]
    x_center: float
    y_center: float

    model_config = {"extra": "forbid"}


class PageReference(BaseModel):
    """Reference to a specific page in a PDF document."""

    pdf_id: str
    page_index: int


class ClusterConfidence(BaseModel):
    """Confidence score for a layout cluster."""

    confidence: float = 0.0
    level: str = "low"
    factors: dict[str, Any] = Field(default_factory=dict)


class PipelineWarning(BaseModel):
    """A warning emitted during pipeline execution."""

    code: str
    severity: str = "info"
    message: str = ""
    stage: int = 0


class PdfDocument(BaseModel):
    """A PDF document input to the pipeline."""

    id: str
    path: str
    name: str = ""


# ---------------------------------------------------------------------------
# Stage 1 Output: Layout Clustering
# ---------------------------------------------------------------------------


class Cluster(BaseModel):
    """A layout cluster produced by Stage 1."""

    cluster_id: str
    pages: list[PageReference] = Field(default_factory=list)
    representative_page: PageReference
    page_count: int = 0
    confidence: ClusterConfidence | float = 0.0

    def get_confidence_value(self) -> float:
        """Extract numeric confidence regardless of storage format."""
        if isinstance(self.confidence, (int, float)):
            return float(self.confidence)
        if isinstance(self.confidence, ClusterConfidence):
            return self.confidence.confidence
        return 0.0


class Stage1Output(BaseModel):
    """Data produced by Stage 1 — Layout Clustering."""

    clusters: list[Cluster] = Field(default_factory=list)
    raw_text_blocks: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 2 Output: Deep Extraction
# ---------------------------------------------------------------------------


class TextBlock(BaseModel):
    """A text block extracted from a PDF page."""

    id: str = ""
    text: str = ""
    bbox: list[float] = Field(default_factory=list)
    font_name: str = ""
    font_size: float = 0.0
    font_color: str = ""
    is_bold: bool = False
    is_italic: bool = False
    # Extra fields used in text_extraction.py
    is_mono: bool = False
    color: int | str = ""  # PDF integer color or CSS string
    sub_spans: list[dict[str, Any]] | None = None

    model_config = {"extra": "forbid"}


class ImageInfo(BaseModel):
    """An extracted image from a PDF page."""

    id: str = ""
    bbox: list[float] = Field(default_factory=list)
    path: str = ""
    width: float = 0.0
    height: float = 0.0
    # Extra fields used in media_extraction.py
    bbox_valid: bool = True
    format: str = ""

    model_config = {"extra": "forbid"}


class TableInfo(BaseModel):
    """A detected table from a PDF page."""

    id: str = ""
    bbox: list[float] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class FontInfo(BaseModel):
    """Font information from a PDF page."""

    name: str = ""
    css_family: str = ""
    size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False

    model_config = {"extra": "forbid"}


class GridInfo(BaseModel):
    """Grid detection result for a page."""

    columns: list[float] = Field(default_factory=list)
    rows: list[float] = Field(default_factory=list)
    column_count: int = 0
    row_count: int = 0

    model_config = {"extra": "forbid"}


class EnrichedPage(BaseModel):
    """A fully extracted page from Stage 2.

    Story 42.4: text_blocks, images, fonts migrated to typed lists.
    tables, grid_info, drawn_elements remain dict until story 42.5+42.6.
    """

    page_index: int
    cluster_id: str = ""
    is_representative: bool = False
    width: float = 0.0
    height: float = 0.0
    text_blocks: list[TextBlock] = Field(default_factory=list)
    images: list[ImageInfo] = Field(default_factory=list)
    fonts: list[FontInfo] = Field(default_factory=list)
    grid_info: dict[str, Any] | None = None
    screenshot_path: str | None = None
    # Story 42.10 — kept as list[dict] because _structure_tables produces rich cell
    # objects (list[list[dict]] headers/rows with bbox per cell) that are incompatible
    # with the simplified TableInfo schema (list[list[str]] rows). Typed migration
    # deferred to a dedicated story once table cell shape is stabilised.
    tables: list[dict[str, Any]] = Field(default_factory=list)
    drawn_elements: list[dict[str, Any]] | None = None

    model_config = {"extra": "forbid"}


class EnrichedDocument(BaseModel):
    """A PDF document with extracted page data from Stage 2."""

    pdf_id: str
    pdf_name: str = ""
    pages: list[EnrichedPage] = Field(default_factory=list)


class ExtractionWarning(BaseModel):
    """A warning from the extraction process."""

    page_index: int = 0
    pdf_id: str = ""
    warning_type: str = ""
    message: str = ""

    model_config = {"extra": "forbid"}


class Stage2Output(BaseModel):
    """Data produced by Stage 2 — Deep Extraction."""

    enriched_documents: list[EnrichedDocument] = Field(default_factory=list)
    extraction_warnings: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 3 Output: Structural Analysis
# ---------------------------------------------------------------------------


class SectionFieldTemplate(BaseModel):
    """Canonical field template for one field within a repeated section item."""

    name: str = ""
    field_type: str = "dynamic"  # "dynamic" | "static"
    value: str | None = None  # texto fixo, se static

    model_config = {"extra": "forbid"}


class SectionTemplate(BaseModel):
    """Canonical structure of one item in a repeated section."""

    fields: list[SectionFieldTemplate] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class SectionInstance(BaseModel):
    """One occurrence (row/item) of a repeated section."""

    bbox: list[float] = Field(default_factory=list)
    texts: list[str] = Field(default_factory=list)
    block_ids: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class RepeatedSection(BaseModel):
    """A group of N≥2 structurally-similar blocks detected on a page.

    Story 48.4 — produced by detect_repeated_sections() in Stage 3.
    Consumed by Stage 4 to generate ListBinding.
    """

    section_id: str
    list_item_count: int
    item_template: SectionTemplate = Field(default_factory=SectionTemplate)
    instances: list[SectionInstance] = Field(default_factory=list)
    page_index: int = 0
    bbox_envelope: list[float] = Field(default_factory=list)  # bbox unindo todas as instâncias

    model_config = {"extra": "forbid"}


class BlockClassification(BaseModel):
    """Classification of a single text block.

    Story 42.5 — explicit fields matching actual bc_entry dict in classification.py.
    """

    semantic: str = ""  # "label", "dynamic", "semi_dynamic", "likely_dynamic", "static", "header", "footer_text"
    stability: str = "unknown"  # "stable", "variable", "rare", "unknown"
    variant: str = "required"  # "required", "optional", "conditional"
    presence_ratio: float = 1.0
    pdf_coverage: float = 1.0
    confidence: float = 0.0
    field_pair: str | None = None  # block_id of the paired label or value
    smart_signals: list[str] | None = None
    present_in_pdfs: list[str] | None = None

    model_config = {"extra": "forbid"}


class ClusterIntelligence(BaseModel):
    """Intelligence summary for a single cluster."""

    block_classifications: dict[str, dict[str, Any]] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    dynamic_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    conditional_fields: list[str] = Field(default_factory=list)
    classification_quality: dict[str, Any] = Field(default_factory=dict)


class DocumentTreeNode(BaseModel):
    """A node in the document tree hierarchy.

    Fields cover all node types built by tree_builder.py:
    zone, section, field, label, value, cell, table, image, chart, barcode, svg, line, rect.
    """

    id: str = ""
    type: str = ""
    children: list[DocumentTreeNode] = Field(default_factory=list)
    # Shared optional fields
    name: str | None = None
    source: str | None = None
    variant: str | None = None
    present_in_pdfs: list[str] | None = None
    bbox: list[float] | None = None
    # Text block fields
    block_id: str | None = None
    text: str | None = None
    is_bold: bool | None = None
    font_weight: str | None = None
    font_size: float | None = None
    font_name: str | None = None
    color: int | str | None = None  # PDF integer color or CSS string
    # Table fields
    table_id: str | None = None
    # Image fields
    image_path: str | None = None
    bbox_valid: bool | None = None
    format: str | None = None
    # Chart / barcode / svg fields
    description: str | None = None
    chart_type: str | None = None
    confidence: float | None = None
    barcode_format: str | None = None
    value: str | None = None
    svg_content: str | None = None
    # Line / rect fields
    orientation: str | None = None
    stroke_color: int | str | None = None  # PDF integer color or CSS string
    width: float | None = None
    fill_color: int | str | None = None  # PDF integer color or CSS string

    model_config = {"extra": "forbid"}


class LayoutTypeInfo(BaseModel):
    """Layout type information derived from Stage 3."""

    id: str
    cluster_id: str
    name: str
    page_width_pts: float = 595.0
    page_height_pts: float = 842.0
    page_count: int = 0

    model_config = {"extra": "forbid"}


class Stage3Output(BaseModel):
    """Data produced by Stage 3 — Structural Analysis."""

    document_trees: dict[str, dict[str, Any]] = Field(default_factory=dict)
    intelligence: dict[str, ClusterIntelligence] = Field(default_factory=dict)
    visual_analysis: dict[str, Any] = Field(default_factory=dict)
    label_value_pairs: dict[str, Any] = Field(default_factory=dict)
    layout_types: list[LayoutTypeInfo] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4 Output: Field Mapping
# ---------------------------------------------------------------------------


class FieldMappingEntry(BaseModel):
    """A single field mapping from PDF to XSD.

    Story 42.6 — expanded to match all fields from _make_mapping_v2 and
    align with frontend FieldMappingEntry interface (pipeline.types.ts).
    """

    # PDF content
    block_id: str = ""
    layout_type_id: str = ""
    pdf_text: str = ""
    label_text: str = ""
    bbox: list[float] | None = None
    page_number: int = 0
    pdf_id: str = ""
    # XSD mapping
    xsd_field_path: str = ""
    xsd_type: str | None = None
    # Confidence & ambiguity
    confidence: float = 0.0
    is_ambiguous: bool = False
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    # Format detection
    detected_format: str | None = None
    # Semantic signals
    smart_signals: list[str] | None = None
    semantic_confirmed: str | None = None
    is_table_cell: bool = False
    from_table: bool = False
    # Frontend interface fields (pipeline.types.ts FieldMappingEntry)
    name: str = ""
    path: str = ""
    type: str = "text"
    status: str = "unmapped"
    isOptional: bool = False

    model_config = {"extra": "forbid"}


class ListBinding(BaseModel):
    """Binding de uma seção repetida (lista) para um nó XSD com maxOccurs > 1.

    Story 48.5 — produzido pelo Stage 4 quando detecta nós repeated_section
    no document tree. Consumido pelo Stage 5 para gerar <repeat data-list="...">.
    """

    section_id: str
    xsd_list_path: str = ""  # ex: "SubGrupo.Segurados.Segurado"
    xsd_max_occurs: str = "unbounded"
    item_fields: list[FieldMappingEntry] = Field(default_factory=list)
    confidence: float = 0.0
    list_item_count: int = 0
    layout_type_id: str = ""
    binding_type: str = "list"  # sempre "list" — para distinguir de FieldMappingEntry no frontend

    model_config = {"extra": "forbid"}


class ConfidenceScoreEntry(BaseModel):
    """Confidence score for a layout's field mappings (raw 0.0–1.0 floats from Stage 4)."""

    layout_stability: float = 0.0
    anchor_detection: float = 0.0
    grid_quality: float = 0.0
    field_variability: float = 0.0
    vision_agreement: float = 0.0
    overall: float = 0.0
    level: str = "low"

    model_config = {"extra": "forbid"}


class NormalizedConfidenceScore(BaseModel):
    """Confidence score normalized to 0–100 integers for frontend display (Stage 5 output).

    DT-42-3 — replaces dict[str, Any] in PipelineResult.confidence_scores.
    Backward-compat validator: accepts float 0.0–1.0 and coerces to int 0–100.
    """

    layout_stability: int = 50
    anchor_detection: int = 50
    grid_quality: int = 50
    field_variability: int = 50
    vision_agreement: int = 50
    overall: int = 50
    status: str = "review_recommended"

    model_config = {"extra": "forbid"}

    @field_validator(
        "layout_stability",
        "anchor_detection",
        "grid_quality",
        "field_variability",
        "vision_agreement",
        "overall",
        mode="before",
    )
    @classmethod
    def coerce_to_int(cls, v: Any) -> int:
        """Coerce float 0.0–1.0 scale to int 0–100. Handles legacy cached results."""
        if isinstance(v, float):
            return round(v * 100) if v <= 1.0 else round(v)
        return int(v) if v is not None else 50


class DocumentStructure(BaseModel):
    """Top-level document structure assembled by Stage 5.

    DT-42-3 — replaces dict[str, Any] in PipelineResult.document_structure.
    extra='allow' preserves forward compatibility with evolving stage output.
    """

    pages: list[Any] = Field(default_factory=list)
    layout_types: list[Any] = Field(default_factory=list)
    root: Any = None
    trees_by_layout: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class ValidationResult(BaseModel):
    """Result of Stage 4 consistency validation."""

    warnings: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    orphans: list[str] = Field(default_factory=list)
    unmapped_required: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class Stage4Output(BaseModel):
    """Data produced by Stage 4 — Field Mapping."""

    field_tree: dict[str, Any] | None = None
    field_mappings: list[dict[str, Any]] = Field(default_factory=list)
    format_functions: dict[str, str] = Field(default_factory=dict)
    confidence_scores: dict[str, Any] = Field(default_factory=dict)
    validation_result: ValidationResult = Field(default_factory=ValidationResult)
    ambiguous_fields: list[dict[str, Any]] = Field(default_factory=list)
    block_classifications_confirmed: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 5 Output: Template Generation
# ---------------------------------------------------------------------------


class TemplateDraft(BaseModel):
    """Draft template generated by Stage 5."""

    html: str = ""
    css: str = ""

    model_config = {"extra": "forbid"}


class Stage5Result(BaseModel):
    """Summary data from Stage 5."""

    template_draft: dict[str, Any] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    overlay_count: int = 0
    multi_doc_pdfs: int = 0


class PipelineResult(BaseModel):
    """Final pipeline output — the result_json assembled by Stage 5.

    Story 42.7 — canonical response model. Shape matches result_assembly.py output
    exactly. Aligned with frontend pipeline.types.ts via story 42.8.
    """

    # Core fields
    layout_types: list[dict[str, Any]] = Field(default_factory=list)
    field_mappings: list[FieldMappingEntry] = Field(default_factory=list)
    document_structure: DocumentStructure = Field(default_factory=DocumentStructure)
    confidence_scores: dict[str, NormalizedConfidenceScore] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    template_draft: dict[str, Any] = Field(default_factory=dict)
    document_type: str = ""
    document_type_confidence: float = 0.0
    # Extended fields
    ambiguous_fields: list[dict[str, Any]] = Field(default_factory=list)
    format_functions: dict[str, str] = Field(default_factory=dict)
    overlay_items: dict[str, Any] = Field(default_factory=dict)
    visual_analysis: dict[str, Any] | None = None
    intelligence: dict[str, Any] | None = None
    validation_result: dict[str, Any] | None = None
    block_classifications_confirmed: dict[str, Any] | None = None
    multi_doc: dict[str, Any] = Field(default_factory=dict)  # {pdfs, matrix, detections} from stage5
    page_config: dict[str, Any] = Field(default_factory=dict)
    anchors: dict[str, Any] = Field(default_factory=dict)
    synthetic_data: Any = None
    synthetic_exemplo_js: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Stage Definition
# ---------------------------------------------------------------------------


class StageDefinition(BaseModel):
    """Definition of a pipeline stage."""

    stage: int
    name: str
    weight: float = 0.20


# ---------------------------------------------------------------------------
# Sub-Progress Event
# ---------------------------------------------------------------------------


class SubProgressEvent(BaseModel):
    """SSE sub-progress event emitted during pipeline execution."""

    stage: int
    stage_name: str
    status: str
    progress_pct: float
    sub_step: str = ""
    sub_progress_pct: float = 0.0
    summary: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# API Response Wrapper
# ---------------------------------------------------------------------------


class PipelineResultResponse(BaseModel):
    """HTTP response wrapper for GET /api/v1/analyze/{job_id}/result.

    Story 42.7 — declared as response_model in the router to enforce schema.
    template_name is job metadata (not pipeline result data) — lives here, not in PipelineResult.
    """

    job_id: str
    status: str
    template_name: str | None = None
    result: PipelineResult | None = None
    error: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Pipeline Context TypedDict
# ---------------------------------------------------------------------------

# We use a regular class with typed attributes instead of TypedDict because
# the pipeline context is highly dynamic (stages add keys progressively).
# This serves as documentation and enables IDE autocompletion.


class PipelineContext:
    """Typed wrapper around the pipeline context dict.

    This provides typed access to the pipeline context while maintaining
    backward compatibility with the existing dict-based approach.
    Stages can use this for type-safe reads/writes or continue using
    the raw dict — both approaches work.

    Usage:
        ctx = PipelineContext(context)
        docs = ctx.pdf_documents  # typed access
        ctx.clusters = [...]      # typed write
        raw = ctx.to_dict()       # back to dict
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data if data is not None else {}

    def _get(self, key: str, default: Any = None) -> Any:
        """Internal typed getter — callers cast the result."""
        return self._data.get(key, default)

    # --- Infrastructure keys ---

    @property
    def storage(self) -> Any:
        return self._data.get("_storage")

    @storage.setter
    def storage(self, value: Any) -> None:
        self._data["_storage"] = value

    @property
    def current_stage(self) -> int:
        return cast(int, self._data.get("_current_stage", 0))

    @current_stage.setter
    def current_stage(self, value: int) -> None:
        self._data["_current_stage"] = value

    @property
    def current_stage_name(self) -> str:
        return cast(str, self._data.get("_current_stage_name", ""))

    @current_stage_name.setter
    def current_stage_name(self, value: str) -> None:
        self._data["_current_stage_name"] = value

    @property
    def job_id(self) -> str:
        return cast(str, self._data.get("job_id", ""))

    @job_id.setter
    def job_id(self, value: str) -> None:
        self._data["job_id"] = value

    @property
    def job(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("_job", {}))

    @job.setter
    def job(self, value: dict[str, Any]) -> None:
        self._data["_job"] = value

    # --- Input keys ---

    @property
    def pdf_documents(self) -> list[dict[str, str]]:
        return cast(list[dict[str, str]], self._data.get("pdf_documents", []))

    @pdf_documents.setter
    def pdf_documents(self, value: list[dict[str, str]]) -> None:
        self._data["pdf_documents"] = value

    @property
    def xsd_path(self) -> str:
        return cast(str, self._data.get("xsd_path", ""))

    @xsd_path.setter
    def xsd_path(self, value: str) -> None:
        self._data["xsd_path"] = value

    # --- Stage 1 keys ---

    @property
    def clusters(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("clusters", []))

    @clusters.setter
    def clusters(self, value: list[dict[str, Any]]) -> None:
        self._data["clusters"] = value

    @property
    def raw_text_blocks(self) -> dict[str, list[dict[str, Any]]]:
        return cast(dict[str, list[dict[str, Any]]], self._data.get("_raw_text_blocks", {}))

    @raw_text_blocks.setter
    def raw_text_blocks(self, value: dict[str, list[dict[str, Any]]]) -> None:
        self._data["_raw_text_blocks"] = value

    # --- Stage 2 keys ---

    @property
    def enriched_documents(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("enriched_documents", []))

    @enriched_documents.setter
    def enriched_documents(self, value: list[dict[str, Any]]) -> None:
        self._data["enriched_documents"] = value

    @property
    def extraction_warnings(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("extraction_warnings", []))

    @extraction_warnings.setter
    def extraction_warnings(self, value: list[dict[str, Any]]) -> None:
        self._data["extraction_warnings"] = value

    # --- Stage 3 keys ---

    @property
    def document_trees(self) -> dict[str, dict[str, Any]]:
        return cast(dict[str, dict[str, Any]], self._data.get("document_trees", {}))

    @document_trees.setter
    def document_trees(self, value: dict[str, dict[str, Any]]) -> None:
        self._data["document_trees"] = value

    @property
    def intelligence(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("intelligence", {}))

    @intelligence.setter
    def intelligence(self, value: dict[str, Any]) -> None:
        self._data["intelligence"] = value

    @property
    def visual_analysis(self) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._data.get("visual_analysis"))

    @visual_analysis.setter
    def visual_analysis(self, value: dict[str, Any] | None) -> None:
        self._data["visual_analysis"] = value

    @property
    def label_value_pairs(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("label_value_pairs", {}))

    @label_value_pairs.setter
    def label_value_pairs(self, value: dict[str, Any]) -> None:
        self._data["label_value_pairs"] = value

    @property
    def layout_types(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("layout_types", []))

    @layout_types.setter
    def layout_types(self, value: list[dict[str, Any]]) -> None:
        self._data["layout_types"] = value

    @property
    def pipeline_warnings(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("_pipeline_warnings", []))

    @pipeline_warnings.setter
    def pipeline_warnings(self, value: list[dict[str, Any]]) -> None:
        self._data["_pipeline_warnings"] = value

    # --- Stage 4 keys ---

    @property
    def field_tree(self) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._data.get("field_tree"))

    @field_tree.setter
    def field_tree(self, value: dict[str, Any] | None) -> None:
        self._data["field_tree"] = value

    @property
    def field_mappings(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("field_mappings", []))

    @field_mappings.setter
    def field_mappings(self, value: list[dict[str, Any]]) -> None:
        self._data["field_mappings"] = value

    @property
    def format_functions(self) -> dict[str, str]:
        return cast(dict[str, str], self._data.get("format_functions", {}))

    @format_functions.setter
    def format_functions(self, value: dict[str, str]) -> None:
        self._data["format_functions"] = value

    @property
    def confidence_scores(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("confidence_scores", {}))

    @confidence_scores.setter
    def confidence_scores(self, value: dict[str, Any]) -> None:
        self._data["confidence_scores"] = value

    @property
    def validation_result(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("validation_result", {}))

    @validation_result.setter
    def validation_result(self, value: dict[str, Any]) -> None:
        self._data["validation_result"] = value

    @property
    def ambiguous_fields(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._data.get("ambiguous_fields", []))

    @ambiguous_fields.setter
    def ambiguous_fields(self, value: list[dict[str, Any]]) -> None:
        self._data["ambiguous_fields"] = value

    @property
    def block_classifications_confirmed(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("block_classifications_confirmed", {}))

    @block_classifications_confirmed.setter
    def block_classifications_confirmed(self, value: dict[str, Any]) -> None:
        self._data["block_classifications_confirmed"] = value

    # --- Stage 5 keys ---

    @property
    def result_json(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("result_json", {}))

    @result_json.setter
    def result_json(self, value: dict[str, Any]) -> None:
        self._data["result_json"] = value

    # --- Stage result summaries ---

    @property
    def stage_1_result(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("stage_1_result", {}))

    @stage_1_result.setter
    def stage_1_result(self, value: dict[str, Any]) -> None:
        self._data["stage_1_result"] = value

    @property
    def stage_2_result(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("stage_2_result", {}))

    @stage_2_result.setter
    def stage_2_result(self, value: dict[str, Any]) -> None:
        self._data["stage_2_result"] = value

    @property
    def stage_3_result(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("stage_3_result", {}))

    @stage_3_result.setter
    def stage_3_result(self, value: dict[str, Any]) -> None:
        self._data["stage_3_result"] = value

    @property
    def stage_4_result(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("stage_4_result", {}))

    @stage_4_result.setter
    def stage_4_result(self, value: dict[str, Any]) -> None:
        self._data["stage_4_result"] = value

    @property
    def stage_5_result(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("stage_5_result", {}))

    @stage_5_result.setter
    def stage_5_result(self, value: dict[str, Any]) -> None:
        self._data["stage_5_result"] = value

    # --- Vision API tracking ---

    @property
    def vision_api_calls(self) -> int:
        return cast(int, self._data.get("_vision_api_calls", 0))

    @vision_api_calls.setter
    def vision_api_calls(self, value: int) -> None:
        self._data["_vision_api_calls"] = value

    @property
    def vision_api_cost(self) -> float | None:
        return cast(float | None, self._data.get("_vision_api_cost"))

    @vision_api_cost.setter
    def vision_api_cost(self, value: float | None) -> None:
        self._data["_vision_api_cost"] = value

    # --- Dict interface ---

    def to_dict(self) -> dict[str, Any]:
        """Return the underlying dict (same reference, not a copy)."""
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-compatible get for backward compatibility."""
        return cast(dict[str, Any], self._data.get(key, default))

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def setdefault(self, key: str, default: Any = None) -> Any:
        return self._data.setdefault(key, default)
