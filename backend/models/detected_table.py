"""Detected table models for Bloco 5 — Table Detection output structures."""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class TableCell(BaseModel):
    """A single cell within a table row."""

    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    column_index: int


class TableRow(BaseModel):
    """A row within a detected table."""

    cells: List[TableCell] = Field(default_factory=list)
    row_index: int = 0
    is_header: bool = False


class DetectedTable(BaseModel):
    """A table region detected within one or more pages of a PDF."""

    table_id: str
    page_number: int
    pdf_index: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)  # rows[row_idx][col_idx]
    column_widths: List[float] = Field(default_factory=list)
    is_multi_page: bool = False
    continuation_pages: List[int] = Field(default_factory=list)
    confidence: float = 0.0  # 0.0 – 1.0
    detection_method: str = ""  # "grid_lines", "alignment", "pattern", "combined"
