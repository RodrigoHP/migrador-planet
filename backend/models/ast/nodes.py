"""Planet AST v0 — Intermediate representation for template engine.

Spike: spike/ast-validation — validates AST as source-of-truth for Epic 49.

Design invariant (MJML #1630): binding is a TYPED field on FieldNode.
Renderer transforms FieldNode → {{x | formatter}}. Never post-compiled string.

8 node types MVP: text, field, section, repeating, image, table, page, raw_html.
raw_html promoted from v2 to v0 MVP (lesson from Contentful rigid schema).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class BBox(BaseModel):
    """Bounding box with page reference."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_coords(self) -> BBox:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError(f"Invalid bbox: ({self.x0},{self.y0}) → ({self.x1},{self.y1})")
        return self

    @classmethod
    def from_list(cls, coords: list[float], page: int = 0) -> BBox:
        """Construct from a [x0, y0, x1, y1] list (Stage 2/3 format)."""
        if len(coords) < 4:
            return cls(page=page, x0=0, y0=0, x1=0, y1=0)
        return cls(page=page, x0=coords[0], y0=coords[1], x1=coords[2], y1=coords[3])


class FormatterSpec(BaseModel):
    """Describes how a dynamic field value should be formatted for display."""

    kind: Literal["date", "currency", "number", "percent", "raw"]
    pattern: str | None = None  # ex: "dd/MM/yyyy", "R$ #.##0,00"
    locale: str = "pt-BR"

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


class TextNode(BaseModel):
    """Static text content (labels, fixed values)."""

    type: Literal["text"]
    content: str
    bbox: BBox
    font_family: str | None = None
    font_size: float | None = None
    font_weight: str | None = None
    color: str | None = None

    model_config = {"extra": "forbid"}


class FieldNode(BaseModel):
    """Dynamic field — mapped to a data source path.

    INVARIANT (MJML #1630): bind_path and formatter are TYPED fields, never
    post-compiled strings. Renderer transforms FieldNode → {{bind_path | formatter}}.
    """

    type: Literal["field"]
    bind_path: str  # ex: "boleto.vencimento", "segurado.nome"
    formatter: FormatterSpec
    bbox: BBox
    label: str | None = None  # associated label text for context

    model_config = {"extra": "forbid"}


class SectionNode(BaseModel):
    """Logical section grouping child nodes."""

    type: Literal["section"]
    name: str | None = None
    children: list[AstNode] = Field(default_factory=list)
    bbox: BBox

    model_config = {"extra": "forbid"}


class RepeatingNode(BaseModel):
    """Repeating structure (list/table rows) bound to an iterable data path."""

    type: Literal["repeating"]
    iterator: str  # ex: "segurados[]", "itens[]"
    item_template: AstNode
    bbox: BBox
    item_count_hint: int | None = None  # observed count in sample

    model_config = {"extra": "forbid"}


class ImageNode(BaseModel):
    """Static or dynamic image (logos, barcodes, signatures)."""

    type: Literal["image"]
    source: Literal["static", "dynamic"]
    bind_path: str | None = None  # required when source="dynamic"
    bbox: BBox
    alt: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _dynamic_requires_path(self) -> ImageNode:
        if self.source == "dynamic" and not self.bind_path:
            raise ValueError("ImageNode with source='dynamic' requires bind_path")
        return self


class TableNode(BaseModel):
    """Table structure with rows of AST nodes per cell."""

    type: Literal["table"]
    rows: list[list[AstNode]] = Field(default_factory=list)
    bbox: BBox
    headers: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class PageNode(BaseModel):
    """Top-level page container."""

    type: Literal["page"]
    page_num: int
    children: list[AstNode] = Field(default_factory=list)
    width: float | None = None
    height: float | None = None

    model_config = {"extra": "forbid"}


class RawHtmlNode(BaseModel):
    """Escape hatch for structures not expressible in typed nodes.

    Promoted to v0 MVP (lesson from Contentful rigid schema — must handle
    unexpected structures without breaking the whole document).
    """

    type: Literal["raw_html"]
    html: str
    bbox: BBox
    reason: str | None = None  # why raw_html was used instead of typed node

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Discriminated union — the core AstNode type
# ---------------------------------------------------------------------------

AstNode = Annotated[
    Union[
        TextNode,
        FieldNode,
        SectionNode,
        RepeatingNode,
        ImageNode,
        TableNode,
        PageNode,
        RawHtmlNode,
    ],
    Field(discriminator="type"),
]

# Resolve forward references after all types are defined
for _cls in (SectionNode, RepeatingNode, TableNode, PageNode):
    _cls.model_rebuild()


# ---------------------------------------------------------------------------
# Root document model
# ---------------------------------------------------------------------------


class PlanetAstV0(BaseModel):
    """Root document AST — planet-ast-v0.

    Wraps a PageNode (or SectionNode for single-page clusters) as the tree root.
    schema_version allows future migration tooling to identify and transform
    documents when the schema evolves.
    """

    schema_version: Literal["planet-ast-v0"] = "planet-ast-v0"
    root: AstNode
    layout_type_id: str = ""
    source_cluster_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
