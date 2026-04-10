"""Stage 3 — Semantic Classification sub-module (Step 3.3).

Responsibilities:
  - Per-block semantic classification (label/dynamic/semi_dynamic/etc.)
  - Zone detection (header/body/footer)
  - Label-value pairing via adjacency analysis

Story 41.3 — extracted from stage3_structural_analysis.py
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from models.pipeline_context import BlockClassification
from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Zone detection helpers
# ---------------------------------------------------------------------------


def _get_visual_zone(
    bbox: list[float],
    visual_analysis: dict[str, dict[str, Any]],
    page_key: str,
) -> str | None:
    """Determine zone from visual_analysis regions."""
    va = visual_analysis.get(page_key)
    if not va or not va.get("regions"):
        return None

    block_cy = (bbox[1] + bbox[3]) / 2

    for region in va["regions"]:
        ry0 = region["bbox"][1]
        ry1 = region["bbox"][3]
        rtype = region["type"]
        if ry0 <= block_cy <= ry1 and rtype in ("header", "footer", "sidebar"):
            return rtype

    return None


def _get_zone_by_threshold(
    bbox: list[float],
    page_height: float,
) -> str | None:
    """Fallback zone detection by threshold."""
    y_mid = (bbox[1] + bbox[3]) / 2
    relative = y_mid / page_height if page_height > 0 else 0.5

    if relative <= 0.10:
        return "header"
    if relative >= 0.90:
        return "footer"
    return None


# ---------------------------------------------------------------------------
# Position matching and adjacency
# ---------------------------------------------------------------------------


def _find_position_match(
    block_bbox: list[float],
    page_width: float,
    page_height: float,
    position_classifications: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the classification from 3.1 that matches this block position."""
    if not position_classifications or page_width <= 0 or page_height <= 0:
        return None

    block_xc = ((block_bbox[0] + block_bbox[2]) / 2) / page_width
    block_yc = ((block_bbox[1] + block_bbox[3]) / 2) / page_height

    best = None
    best_dist = float("inf")
    tolerance = 0.03  # 3% normalized

    for pc in position_classifications:
        pos = pc.get("position", [0, 0])
        dx = abs(block_xc - pos[0])
        dy = abs(block_yc - pos[1])
        dist = (dx**2 + dy**2) ** 0.5

        if dist < best_dist and dx < tolerance and dy < tolerance:
            best = pc
            best_dist = dist

    return best


def _find_adjacent_value(
    label_block: dict[str, Any],
    dynamics: list[dict[str, Any]],
    page_width: float,
    page_height: float,
) -> dict[str, Any] | None:
    """Find the value block nearest to a label.

    Priority:
      1. Right of label (same Y, within 40% page width)
      2. Below label (same X, within 3.5% page height)
    """
    lx0, ly0, lx1, ly1 = label_block["bbox"]
    below_threshold = page_height * 0.035
    best = None
    best_dist = float("inf")

    for d in dynamics:
        if d.get("_paired"):
            continue
        dx0, dy0, dx1, dy1 = d["bbox"]

        # Right: same Y (within 5pts), X right after label
        if abs(dy0 - ly0) < 5 and dx0 > lx1 and dx0 - lx1 < page_width * 0.4:
            dist = dx0 - lx1
            if dist < best_dist:
                best, best_dist = d, dist

        # Below: same X (within 10pts), Y just below label
        elif abs(dx0 - lx0) < 10 and dy0 > ly1 and dy0 - ly1 < below_threshold:
            dist = dy0 - ly1 + 1000  # penalize to prefer "right"
            if dist < best_dist:
                best, best_dist = d, dist

    return best


# ---------------------------------------------------------------------------
# Sub-step 3.3 — Semantic Classification + Label-Value Pairing
# ---------------------------------------------------------------------------


def _run_3_3(
    enriched_documents: list[dict[str, Any]],
    position_classifications_by_cluster: dict[str, Any],
    visual_analysis: dict[str, dict[str, Any]],
    clusters: list[dict[str, Any]],
) -> tuple[dict[str, BlockClassification], list[dict[str, Any]]]:
    """Sub-step 3.3 — Semantic Classification + Label-Value Pairing.

    Returns (block_classifications, label_value_pairs).
    block_classifications: dict[block_id, BlockClassification] — typed in Stage 3.
    Callers serialize to dicts at context boundary via bc.model_dump().
    """
    block_classifications: dict[str, BlockClassification] = {}
    label_value_pairs: list[dict[str, Any]] = []

    # Build cluster_id -> cluster lookup
    _cluster_map = {c["cluster_id"]: c for c in clusters if not c["cluster_id"].startswith("_")}  # noqa: F841

    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            if not page.get("is_representative"):
                continue

            cluster_id = page.get("cluster_id", "")
            page_key = f"{pdf_id}:{page['page_index']}"
            page_width = page.get("width", 595.0)
            page_height = page.get("height", 842.0)

            # Get position classifications for this cluster
            cluster_data = position_classifications_by_cluster.get(cluster_id, {})
            pos_classifications = cluster_data.get("classifications", [])

            # Classify each block
            for block in page.get("text_blocks", []):
                block_id = block.get("id", str(uuid.uuid4()))

                # Match position to 3.1 classification
                pos_class = _find_position_match(block["bbox"], page_width, page_height, pos_classifications)

                # Determine zone via visual analysis
                zone = _get_visual_zone(block["bbox"], visual_analysis, page_key)
                if zone is None:
                    zone = _get_zone_by_threshold(block["bbox"], page_height)

                # Build classification
                if pos_class:
                    semantic = pos_class.get("classification", "unknown")
                    stability = pos_class.get("stability", "unknown")
                    variant = pos_class.get("variant", "required")
                    confidence = pos_class.get("confidence", 0.50)
                    presence_ratio = pos_class.get("presence_ratio", 1.0)
                    pdf_coverage = pos_class.get("pdf_coverage", 1.0)
                    smart_signals = pos_class.get("smart_signals")
                else:
                    # Fallback: heuristic
                    text = block.get("text", "").strip()
                    if text.endswith(":"):
                        semantic = "label"
                    elif any(p.search(text) for p, _, _ in _COMPILED_DYNAMIC_PATTERNS):
                        semantic = "dynamic"
                    else:
                        semantic = "label" if len(text) <= 30 else "dynamic"
                    stability = "unknown"
                    variant = "required"
                    confidence = 0.50
                    presence_ratio = 1.0
                    pdf_coverage = 1.0
                    smart_signals = None

                # Zone override: header/footer text
                semantic_label = semantic
                if zone == "header":
                    semantic_label = "header"
                elif zone == "footer":
                    semantic_label = "footer_text"

                block["semantic_label"] = semantic_label
                block["_classification"] = semantic

                bc_entry = BlockClassification(
                    semantic=semantic,
                    stability=stability,
                    variant=variant,
                    presence_ratio=presence_ratio,
                    pdf_coverage=pdf_coverage,
                    confidence=confidence,
                    field_pair=None,
                    smart_signals=smart_signals,
                )

                # Propagate present_in_pdfs from position classification
                if pos_class and pos_class.get("present_in_pdfs"):
                    bc_entry.present_in_pdfs = pos_class["present_in_pdfs"]

                block_classifications[block_id] = bc_entry

            # Label-Value Pairing
            _empty_bc = BlockClassification()
            labels = [
                b
                for b in page.get("text_blocks", [])
                if block_classifications.get(b.get("id", ""), _empty_bc).semantic == "label"
            ]
            dynamics = [
                b
                for b in page.get("text_blocks", [])
                if block_classifications.get(b.get("id", ""), _empty_bc).semantic
                in ("dynamic", "semi_dynamic", "likely_dynamic")
            ]

            for label_block in labels:
                pair = _find_adjacent_value(label_block, dynamics, page_width, page_height)
                if pair:
                    lid = label_block.get("id", "")
                    vid = pair.get("id", "")
                    if lid in block_classifications:
                        block_classifications[lid].field_pair = vid
                    if vid in block_classifications:
                        block_classifications[vid].field_pair = lid
                    pair["_paired"] = True

                    label_value_pairs.append(
                        {
                            "label_block_id": lid,
                            "value_block_id": vid,
                            "confidence": min(
                                block_classifications.get(lid, _empty_bc).confidence,
                                block_classifications.get(vid, _empty_bc).confidence,
                            ),
                            "method": "adjacency",
                        }
                    )

    return block_classifications, label_value_pairs
