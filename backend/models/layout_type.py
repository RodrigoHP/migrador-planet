"""Layout discovery models: LayoutSkeleton, LayoutFingerprint, LayoutType.

These models represent the output of Bloco 3 — Layout Discovery (Stages 7–11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# LayoutSkeleton — per-page structural skeleton (Stage 7 output)
# ---------------------------------------------------------------------------


@dataclass
class LayoutZones:
    """Vertical zone boundaries for a page (fractions of page height)."""

    header_top: float = 0.0
    header_bottom: float = 0.15
    body_top: float = 0.15
    body_bottom: float = 0.90
    footer_top: float = 0.90
    footer_bottom: float = 1.0


@dataclass
class LayoutSkeleton:
    """Structural skeleton for a single PDF page.

    Attributes:
        page_number:       0-based page index within the PDF.
        pdf_index:         Index of the source PDF in the job.
        text_blocks:       List of (text, bbox) tuples extracted from the page.
        table_candidates:  List of bounding boxes that look like tables.
        zones:             Header / body / footer zone boundaries.
        grid_info:         Column/row grid detected by Stage 6 (may be None).
        page_width:        Page width in PDF points (used for density calc).
        page_height:       Page height in PDF points.
    """

    page_number: int
    pdf_index: int
    text_blocks: List[Tuple[str, Tuple[float, float, float, float]]] = field(
        default_factory=list
    )
    table_candidates: List[Tuple[float, float, float, float]] = field(
        default_factory=list
    )
    zones: LayoutZones = field(default_factory=LayoutZones)
    grid_info: Optional[Dict[str, Any]] = None
    page_width: float = 595.0   # A4 default
    page_height: float = 842.0  # A4 default

    # --- Feature vector helpers --------------------------------------------

    @property
    def num_blocks(self) -> int:
        return len(self.text_blocks)

    @property
    def avg_font_size(self) -> float:
        """Return the average font size from text_blocks.

        Text blocks are stored as (text, bbox) — font size is inferred from
        the block height (y1 - y0) as a proxy when no explicit size is stored.
        """
        if not self.text_blocks:
            return 0.0
        sizes = [abs(bbox[3] - bbox[1]) for _, bbox in self.text_blocks]
        return sum(sizes) / len(sizes)

    @property
    def table_count(self) -> int:
        return len(self.table_candidates)

    @property
    def text_density(self) -> float:
        """Total text-block area / page area."""
        if self.page_width <= 0 or self.page_height <= 0:
            return 0.0
        total_text_area = sum(
            abs((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
            for _, bbox in self.text_blocks
        )
        return total_text_area / (self.page_width * self.page_height)

    @property
    def header_height_ratio(self) -> float:
        return self.zones.header_bottom - self.zones.header_top

    def to_feature_vector(self) -> List[float]:
        """Return [num_blocks, avg_font_size, table_count, text_density, header_height_ratio]."""
        return [
            float(self.num_blocks),
            self.avg_font_size,
            float(self.table_count),
            self.text_density,
            self.header_height_ratio,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "pdf_index": self.pdf_index,
            "num_blocks": self.num_blocks,
            "table_count": self.table_count,
            "text_density": self.text_density,
            "grid_info": self.grid_info,
            "page_width": self.page_width,
            "page_height": self.page_height,
        }


# ---------------------------------------------------------------------------
# LayoutFingerprint — structural signature of a layout cluster (Stage 10)
# ---------------------------------------------------------------------------


@dataclass
class LayoutFingerprint:
    """Structural fingerprint for a cluster of similar pages.

    Attributes:
        table_count:      Average number of table candidates in the cluster.
        column_count:     Number of grid columns (0 if no grid detected).
        header_blocks:    Average number of text blocks in the header zone.
        body_zone_ratio:  Fraction of the page occupied by the body zone.
        footer_present:   True when any page in the cluster has footer content.
        fingerprint_hash: SHA-256 hex digest of the canonical fingerprint dict.
    """

    table_count: float = 0.0
    column_count: int = 0
    header_blocks: float = 0.0
    body_zone_ratio: float = 0.75
    footer_present: bool = False
    fingerprint_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tableCount": self.table_count,
            "columnCount": self.column_count,
            "headerBlocks": self.header_blocks,
            "bodyZoneRatio": self.body_zone_ratio,
            "footerPresent": self.footer_present,
        }


# ---------------------------------------------------------------------------
# LayoutType — a discovered layout cluster (AC #7)
# ---------------------------------------------------------------------------


@dataclass
class LayoutType:
    """A single layout type identified during Bloco 3 processing.

    Attributes:
        cluster_id:           Integer cluster label (0-based).
        name:                 Auto-generated human-readable name.
        representative_page:  Dict with page_number + pdf_index of the best
                              representative page for this cluster.
        fingerprint:          Structural fingerprint of this layout type.
        page_count:           Total number of pages in this cluster.
        pages:                List of (pdf_index, page_number) for all pages.
        is_reusable:          True when a matching template was found in the
                              Supabase layout_registry.
        template_id:          Existing template UUID, or None if new.
    """

    cluster_id: int
    name: str
    representative_page: Dict[str, int]
    fingerprint: LayoutFingerprint
    page_count: int = 0
    pages: List[Dict[str, int]] = field(default_factory=list)
    is_reusable: bool = False
    template_id: Optional[str] = None

    # Internal working fields used by pipeline stages (excluded from repr/serialisation)
    _centroid: Optional[List[float]] = field(default=None, repr=False)
    _cluster_skeletons: List[Any] = field(default_factory=list, repr=False)
    _intelligence: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": f"layout-{self.cluster_id}",
            "cluster_id": self.cluster_id,
            "name": self.name,
            "representative_page": self.representative_page,
            "fingerprint": self.fingerprint.to_dict(),
            "fingerprint_hash": self.fingerprint.fingerprint_hash,
            "page_count": self.page_count,
            "pages": self.pages,
            "is_reusable": self.is_reusable,
            "template_id": self.template_id,
        }
