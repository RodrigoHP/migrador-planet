"""Stage 7 — Skeleton Builder.

Builds a LayoutSkeleton for every page of every parsed PDF.
The skeleton captures text blocks with bounding boxes, table candidates,
layout zones (header / body / footer), and grid info from the previous stage.

Registers itself in the default_registry as Stage 7 (Block 3).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from models.layout_type import LayoutSkeleton, LayoutZones

# Page dimensions: fallback A4 in PDF points
_DEFAULT_WIDTH = 595.0
_DEFAULT_HEIGHT = 842.0

# Zone thresholds (fraction of page height)
_HEADER_BOTTOM = 0.15
_FOOTER_TOP = 0.90


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _table_candidates_from_grid(
    grid_info: Optional[Dict[str, Any]], page_height: float, page_width: float
) -> List[Tuple[float, float, float, float]]:
    """Derive approximate table bounding boxes from grid info.

    Each detected grid row/column pair yields a candidate rectangle.
    Returns an empty list when there is no grid or fewer than 2 rows.
    """
    if grid_info is None:
        return []

    rows: List[float] = grid_info.get("row_positions", [])
    cols: List[float] = grid_info.get("column_positions", [])

    if len(rows) < 2 or len(cols) < 2:
        return []

    # Treat the entire grid extent as a single table candidate
    x0 = cols[0]
    x1 = cols[-1]
    y0 = rows[0]
    y1 = rows[-1]
    return [(x0, y0, x1, y1)]


def _build_skeleton_from_page(
    page_dict: Dict[str, Any],
    pdf_index: int,
) -> LayoutSkeleton:
    """Build a LayoutSkeleton from a serialised ParsedPage dict."""
    page_number: int = page_dict.get("page_number", 0)
    text_blocks_raw: List[Dict[str, Any]] = page_dict.get("text_blocks", [])
    grid_info: Optional[Dict[str, Any]] = page_dict.get("grid_info")

    # Infer page dimensions from block extents (fallback to A4)
    all_y1 = [b["bbox"][3] for b in text_blocks_raw if b.get("bbox")]
    all_x1 = [b["bbox"][2] for b in text_blocks_raw if b.get("bbox")]
    page_height = max(all_y1) if all_y1 else _DEFAULT_HEIGHT
    page_width = max(all_x1) if all_x1 else _DEFAULT_WIDTH
    # Never go below sensible minimums
    page_height = max(page_height, _DEFAULT_HEIGHT)
    page_width = max(page_width, _DEFAULT_WIDTH)

    # Text blocks as (text, bbox) tuples
    text_blocks: List[Tuple[str, Tuple[float, float, float, float]]] = []
    for tb in text_blocks_raw:
        text = tb.get("text", "")
        raw_bbox = tb.get("bbox")
        if not raw_bbox or len(raw_bbox) < 4:
            continue
        bbox: Tuple[float, float, float, float] = (
            float(raw_bbox[0]),
            float(raw_bbox[1]),
            float(raw_bbox[2]),
            float(raw_bbox[3]),
        )
        text_blocks.append((text, bbox))

    # Table candidates derived from grid info
    table_candidates = _table_candidates_from_grid(grid_info, page_height, page_width)

    zones = LayoutZones(
        header_top=0.0,
        header_bottom=_HEADER_BOTTOM,
        body_top=_HEADER_BOTTOM,
        body_bottom=_FOOTER_TOP,
        footer_top=_FOOTER_TOP,
        footer_bottom=1.0,
    )

    return LayoutSkeleton(
        page_number=page_number,
        pdf_index=pdf_index,
        text_blocks=text_blocks,
        table_candidates=table_candidates,
        zones=zones,
        grid_info=grid_info,
        page_width=page_width,
        page_height=page_height,
    )


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 7 executor — Skeleton Builder.

    Reads context["parsed_documents"] (list of ParsedDocument dicts).
    Writes context["skeletons"] = list of LayoutSkeleton.to_dict() mappings
    (skeletons are also kept in context["_skeleton_objects"] as Python objects
    for use by downstream stages in the same process).
    """
    emit = context.get("emit_progress")

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])

    skeletons: List[LayoutSkeleton] = []
    total_pages = 0

    for doc in parsed_documents:
        pdf_index: int = doc.get("pdf_index", 0)
        pages: List[Dict[str, Any]] = doc.get("pages", [])
        for page_dict in pages:
            skeleton = _build_skeleton_from_page(page_dict, pdf_index=pdf_index)
            skeletons.append(skeleton)
            total_pages += 1

    context["_skeleton_objects"] = skeletons
    context["skeletons"] = [s.to_dict() for s in skeletons]

    if emit:
        try:
            emit(
                {
                    "stage": 7,
                    "stage_name": "Skeleton Builder",
                    "status": "completed",
                    "summary": {
                        "total_skeletons": len(skeletons),
                        "total_pages": total_pages,
                    },
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return {
        "total_skeletons": len(skeletons),
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 7 in the given registry with this implementation."""
    registry.remove_stage(7)
    registry.register_stage(
        stage_number=7,
        name="Skeleton Builder",
        block_id=3,
        estimated_duration=1.5,
        execute_fn=execute,
    )
