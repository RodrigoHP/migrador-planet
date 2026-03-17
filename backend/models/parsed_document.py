"""Parsed document models for Bloco 2 — PDF Parsing output structures."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Primitive models
# ---------------------------------------------------------------------------


class TextBlock(BaseModel):
    """A single reconstructed text block extracted from a PDF page."""

    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1) in PDF points
    font_name: str = ""
    font_size: float = 0.0
    page_number: int
    pdf_index: int = 0  # index of the PDF in the multi-PDF job
    semantic_label: str = ""  # filled by Stage 19 — Semantic Analysis


class CSSFont(BaseModel):
    """A normalised CSS font description derived from a PDF font."""

    font_family: str
    font_size: float
    font_weight: str = "normal"  # "normal" | "bold"
    font_style: str = "normal"   # "normal" | "italic"


class ParsedImage(BaseModel):
    """An image extracted from a PDF page."""

    path: str              # local /tmp path or Supabase storage path
    format: str            # e.g. "png", "jpeg"
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page_number: int
    pdf_index: int = 0


class GridInfo(BaseModel):
    """Column/row grid structure detected on a page or document."""

    columns: int
    rows: int
    column_positions: List[float] = Field(default_factory=list)
    row_positions: List[float] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Page and Document
# ---------------------------------------------------------------------------


class ParsedPage(BaseModel):
    """All extracted data for one page of a PDF."""

    page_number: int
    text_blocks: List[TextBlock] = Field(default_factory=list)
    images: List[ParsedImage] = Field(default_factory=list)
    fonts: List[CSSFont] = Field(default_factory=list)
    grid_info: Optional[GridInfo] = None
    screenshot_path: Optional[str] = None


class ParsedDocument(BaseModel):
    """Top-level output for one PDF file after Bloco 2 processing."""

    job_id: str
    pdf_index: int
    pdf_name: str
    pages: List[ParsedPage] = Field(default_factory=list)

    def to_context_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict suitable for the pipeline context."""
        return self.model_dump()
