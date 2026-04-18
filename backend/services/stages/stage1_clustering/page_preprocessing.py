"""Stage 1 — Page Preprocessing sub-module.

Responsibilities:
  - Page classification (text / scanned / blank)
  - Block extraction from PDF pages
  - Normalisation (rotation + bbox normalisation)
  - Content abstraction (replace dynamic values with tokens)
  - Region filtering (detect header / footer boundaries)

Story 41.3 — extracted from stage1_layout_clustering.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF

from models.pipeline_context import BlockInfo

# ---------------------------------------------------------------------------
# Content Abstraction Patterns
# ---------------------------------------------------------------------------

ABSTRACTION_PATTERNS: list[tuple[str, str]] = [
    # Most specific patterns first to avoid false matches
    (r"\d{3}\.\d{3}\.\d{3}-\d{2}", "CPF"),
    (r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "CNPJ"),
    (r"\d{2}/\d{2}/\d{4}", "DATE"),
    (r"\d{4}-\d{2}-\d{2}", "DATE"),
    (r"[A-Za-z\u00C0-\u00FF][a-z\u00E0-\u00FF]+ \d{4}", "DATE"),
    (r"R\$\s*[\d.,]+", "NUMBER"),
    (r"\d+[.,]\d{2}", "NUMBER"),
]

_COMPILED_PATTERNS = [(re.compile(p), repl) for p, repl in ABSTRACTION_PATTERNS]


# ---------------------------------------------------------------------------
# ClusteringConfig — centralised thresholds (G14)
# ---------------------------------------------------------------------------


@dataclass
class ClusteringConfig:
    """Centralised thresholds for Stage 1 with documented rationale."""

    # Similarity & Clustering
    clustering_threshold: float = 0.75  # lowered: list expansion makes scores ~0.80-0.98
    position_tolerance: float = 0.05
    structural_region_tolerance: float = 0.20  # raised: list items span >10% of page height

    # Region Filtering
    region_presence_threshold: float = 0.70
    region_header_min: float = 0.08
    region_header_max: float = 0.30
    region_footer_min: float = 0.75
    region_footer_max: float = 0.95

    # Detection (Layer 2)
    phash_max_distance: int = 10
    quality_outlier_threshold: float = 0.75
    quality_outlier_avg_threshold: float = 0.78

    # Homogeneity Check
    homogeneity_mismatch_threshold: float = 0.20

    # Confidence
    checkpoint_confidence_threshold: float = 0.70

    # Auto-correction
    merge_threshold: float = 0.90

    @classmethod
    def from_job_config(cls, job_config: dict) -> ClusteringConfig:
        config = cls()
        overrides = job_config.get("clustering_config", {})
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# ---------------------------------------------------------------------------
# Internal page representation
# ---------------------------------------------------------------------------


@dataclass
class PageInfo:
    """Internal representation of a single page during clustering."""

    pdf_id: str
    page_index: int
    page_type: str = "text"  # text | scanned | blank
    is_processable: bool = True
    rotation: int = 0
    width: float = 0.0
    height: float = 0.0
    raw_blocks: list[dict[str, Any]] = field(default_factory=list)
    norm_blocks: list[dict[str, Any]] = field(default_factory=list)
    abstract_blocks: list[BlockInfo] = field(default_factory=list)
    core_blocks: list[BlockInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1.1 — Page Classification
# ---------------------------------------------------------------------------


def _classify_pages(
    pdf_path: str,
    pdf_id: str,
) -> list[PageInfo]:
    """Step 1.1 — Classify pages as text / scanned / blank."""
    doc = fitz.open(pdf_path)
    pages: list[PageInfo] = []
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text("text") or ""
        char_count = len(text.strip())

        if char_count < 5:
            # Check if it has images (scanned) or is truly blank
            images = page.get_images(full=False)
            if images:
                page_type = "scanned"
            else:
                page_type = "blank"
            is_processable = False
        else:
            page_type = "text"
            is_processable = True

        pi = PageInfo(
            pdf_id=pdf_id,
            page_index=idx,
            page_type=page_type,
            is_processable=is_processable,
            rotation=page.rotation,
            width=page.rect.width,
            height=page.rect.height,
        )
        pages.append(pi)
    doc.close()
    return pages


# ---------------------------------------------------------------------------
# 1.2 — Block Extraction
# ---------------------------------------------------------------------------


def _extract_blocks(
    pdf_path: str,
    pages: list[PageInfo],
) -> dict[str, list[dict[str, Any]]]:
    """Step 1.2 — Extract blocks via get_text('blocks') and preserve raw text blocks.

    Returns _raw_text_blocks dict keyed by '{pdf_id}:{page_index}'.
    """
    doc = fitz.open(pdf_path)
    raw_text_blocks: dict[str, list[dict[str, Any]]] = {}

    for pi in pages:
        page = doc[pi.page_index]
        blocks = page.get_text("blocks")
        page_key = f"{pi.pdf_id}:{pi.page_index}"

        page_blocks: list[dict[str, Any]] = []
        raw_page_blocks: list[dict[str, Any]] = []

        for b in blocks:
            # blocks tuple: (x0, y0, x1, y1, text_or_img, block_no, type)
            btype = int(b[6])
            x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
            text = str(b[4]).strip() if btype == 0 else ""

            block_dict = {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "text": text,
                "type": btype,
            }
            page_blocks.append(block_dict)

            # Preserve type=0 (text) blocks for _raw_text_blocks
            if btype == 0 and text:
                w = pi.width if pi.width > 0 else 1.0
                h = pi.height if pi.height > 0 else 1.0
                raw_page_blocks.append(
                    {
                        "text": text,
                        "bbox_norm": [x0 / w, y0 / h, x1 / w, y1 / h],
                        "x_center": ((x0 + x1) / 2) / w,
                        "y_center": ((y0 + y1) / 2) / h,
                        "type": 0,
                    }
                )

        pi.raw_blocks = page_blocks
        raw_text_blocks[page_key] = raw_page_blocks

    doc.close()
    return raw_text_blocks


# ---------------------------------------------------------------------------
# 1.3 — Normalisation
# ---------------------------------------------------------------------------


def _normalize(pages: list[PageInfo]) -> None:
    """Step 1.3 — Apply rotation correction and normalize bbox to [0,1]."""
    for pi in pages:
        w = pi.width if pi.width > 0 else 1.0
        h = pi.height if pi.height > 0 else 1.0

        # For rotated pages (90/270), swap width/height for normalization
        if pi.rotation in (90, 270):
            w, h = h, w

        norm_blocks: list[dict[str, Any]] = []
        for b in pi.raw_blocks:
            if b["type"] != 0:
                continue
            if not b["text"]:
                continue

            x0_n = b["x0"] / w
            y0_n = b["y0"] / h
            x1_n = b["x1"] / w
            y1_n = b["y1"] / h

            # Clamp to [0, 1]
            x0_n = max(0.0, min(1.0, x0_n))
            y0_n = max(0.0, min(1.0, y0_n))
            x1_n = max(0.0, min(1.0, x1_n))
            y1_n = max(0.0, min(1.0, y1_n))

            norm_blocks.append(
                {
                    "text": b["text"],
                    "bbox_norm": [x0_n, y0_n, x1_n, y1_n],
                    "x_center": (x0_n + x1_n) / 2,
                    "y_center": (y0_n + y1_n) / 2,
                }
            )
        pi.norm_blocks = norm_blocks


# ---------------------------------------------------------------------------
# 1.4 — Content Abstraction
# ---------------------------------------------------------------------------


def _abstract_text(text: str) -> str:
    """Apply abstraction patterns to a text string."""
    for pattern, replacement in _COMPILED_PATTERNS:
        if pattern.search(text):
            return replacement
    if len(text) < 20:
        return "TEXT_S"
    return "TEXT_L"


def _abstract_content(pages: list[PageInfo]) -> None:
    """Step 1.4 — Replace variable content with abstract tokens via regex."""
    for pi in pages:
        abstract_blocks: list[BlockInfo] = []
        for b in pi.norm_blocks:
            text = b["text"].strip()
            abstract_text = _abstract_text(text)
            abstract_blocks.append(
                BlockInfo(
                    text_abstract=abstract_text,
                    bbox_norm=b["bbox_norm"],
                    x_center=b["x_center"],
                    y_center=b["y_center"],
                )
            )
        pi.abstract_blocks = abstract_blocks


# ---------------------------------------------------------------------------
# 1.5 — Region Filtering
# ---------------------------------------------------------------------------


def _detect_body_region(
    pages_blocks: list[list[BlockInfo]],
    config: ClusteringConfig,
) -> tuple[float, float]:
    """Detect where header ends and footer starts (adaptive)."""
    n_pages = len(pages_blocks)
    if n_pages == 0:
        return 0.12, 0.88

    # Collect Y centers frequency across pages
    y_frequency: dict[float, int] = {}
    for page_blocks in pages_blocks:
        seen_y: set[float] = set()
        for b in page_blocks:
            y_center = round(b.y_center, 2)
            if y_center not in seen_y:
                y_frequency[y_center] = y_frequency.get(y_center, 0) + 1
                seen_y.add(y_center)

    # Stable Y positions: appear in >70% of pages
    stable_ys = {y for y, count in y_frequency.items() if count / n_pages >= config.region_presence_threshold}

    # Header: last stable Y in top region
    header_candidates = sorted(y for y in stable_ys if y <= config.region_header_max)
    header_end = header_candidates[-1] + 0.02 if header_candidates else config.region_header_min

    # Footer: first stable Y in bottom region
    footer_candidates = sorted(y for y in stable_ys if y >= config.region_footer_min)
    footer_start = footer_candidates[0] - 0.02 if footer_candidates else config.region_footer_max

    # Clamp
    header_end = max(config.region_header_min, min(header_end, config.region_header_max))
    footer_start = max(config.region_footer_min, min(footer_start, config.region_footer_max))

    return header_end, footer_start


def _filter_regions(
    pages: list[PageInfo],
    config: ClusteringConfig,
) -> tuple[float, float]:
    """Step 1.5 — Adaptive region filtering: detect header/footer boundaries.

    Returns (header_end, footer_start) as normalised y-coordinates.
    Sets pi.core_blocks to body-region blocks only.
    """
    # Detect body region across all pages (pool-level)
    all_abstract = [pi.abstract_blocks for pi in pages if pi.is_processable]
    header_end, footer_start = _detect_body_region(all_abstract, config)

    # Filter blocks to body region
    for pi in pages:
        if not pi.is_processable:
            pi.core_blocks = []
            continue
        pi.core_blocks = [b for b in pi.abstract_blocks if header_end <= b.y_center <= footer_start]

    return header_end, footer_start
