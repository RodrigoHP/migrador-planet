"""Stage 13 — Multi-Example Analysis.

Compares text blocks at the same position across multiple PDFs in the same
cluster to distinguish:

  * label      — text that is identical in all documents (e.g. "Cliente:")
  * dynamic    — text that varies across documents (e.g. "João" / "Maria")

When only one PDF is available, heuristics are applied instead:
  * text ending in ":"        → inferred label
  * text that is numeric/date → inferred dynamic
  * bold/large font text      → inferred label (when font_size available)
  * Confidence is set to "inferred" rather than "confirmed"

Reads:
    context["_layout_type_objects"]  — List[LayoutType]
    context["_skeleton_objects"]     — List[LayoutSkeleton]
    context["parsed_documents"]      — List[ParsedDocument dicts] (for font info)
    context["alignment_offsets"]     — offsets from Stage 12 (optional)
    context["intelligence_metadata"] — may contain single_document flag

Writes:
    context["_element_labels"]       — Dict[cluster_id → List[element_analysis]]
      where element_analysis = {
          "bbox_key": str,   # normalised bbox string used as position key
          "text_samples": List[str],
          "classification": "label" | "dynamic",
          "confidence": "confirmed" | "inferred",
      }

Registers itself as Stage 13 (Block 4).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from models.layout_type import LayoutSkeleton, LayoutType

# Overlap threshold for matching bboxes across pages (fraction of smaller area)
_OVERLAP_THRESHOLD = 0.80

# Heuristic patterns for single-document mode
_LABEL_SUFFIX_RE = re.compile(r":\s*$")
_NUMERIC_RE = re.compile(
    r"^\s*[\d.,/\-]+\s*$"               # plain numbers / dates
    r"|^\s*R\$\s*[\d.,]+\s*$"           # currency
    r"|^\d{2}/\d{2}/\d{4}\s*$"         # date dd/mm/yyyy
    r"|^\d{3}\.\d{3}\.\d{3}-\d{2}\s*$" # CPF
)


# ---------------------------------------------------------------------------
# Bbox comparison helpers
# ---------------------------------------------------------------------------


def _bbox_key(bbox: Tuple[float, float, float, float], precision: int = 1) -> str:
    """Return a rounded string key for bbox comparison."""
    return f"{round(bbox[0], precision)},{round(bbox[1], precision)},{round(bbox[2], precision)},{round(bbox[3], precision)}"


def _bbox_area(bbox: Tuple[float, float, float, float]) -> float:
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return max(0.0, w) * max(0.0, h)


def _bbox_overlap_ratio(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
) -> float:
    """Intersection-over-smaller-area ratio."""
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    smaller = min(_bbox_area(a), _bbox_area(b))
    if smaller <= 0:
        return 0.0
    return inter / smaller


# ---------------------------------------------------------------------------
# Multi-PDF analysis
# ---------------------------------------------------------------------------


def _analyse_cluster_multi_pdf(
    skeletons: List[LayoutSkeleton],
    cluster_pages: List[Dict[str, int]],
    offsets: Dict[int, Tuple[float, float]],
) -> List[Dict[str, Any]]:
    """Compare text blocks in the same position across PDFs.

    Groups skeletons by page position, then collects all texts found at that
    position across different PDFs. Identical → label; differing → dynamic.
    """
    skel_map: Dict[Tuple[int, int], LayoutSkeleton] = {
        (s.pdf_index, s.page_number): s for s in skeletons
    }

    # Collect pages per pdf_index for this cluster
    pdf_skels: Dict[int, List[LayoutSkeleton]] = {}
    for page_ref in cluster_pages:
        key = (page_ref["pdf_index"], page_ref["page_number"])
        skel = skel_map.get(key)
        if skel is None:
            continue
        pdf_skels.setdefault(page_ref["pdf_index"], []).append(skel)

    if len(pdf_skels) < 2:
        # Fall back to single-PDF heuristics
        all_skels = [s for skels in pdf_skels.values() for s in skels]
        return _analyse_cluster_single_pdf(all_skels)

    # Build position → text map
    # Key: normalised bbox string; value: set of texts seen
    position_texts: Dict[str, List[str]] = {}
    position_bbox: Dict[str, Tuple[float, float, float, float]] = {}

    for pdf_idx, skels in pdf_skels.items():
        dx, dy = offsets.get(pdf_idx, (0.0, 0.0))
        for skel in skels:
            for text, bbox in skel.text_blocks:
                # Apply alignment offset
                norm_bbox: Tuple[float, float, float, float] = (
                    bbox[0] + dx,
                    bbox[1] + dy,
                    bbox[2] + dx,
                    bbox[3] + dy,
                )
                # Find matching key (overlap-based)
                matched_key: Optional[str] = None
                for existing_key, existing_bbox in position_bbox.items():
                    if _bbox_overlap_ratio(norm_bbox, existing_bbox) >= _OVERLAP_THRESHOLD:
                        matched_key = existing_key
                        break

                if matched_key is None:
                    matched_key = _bbox_key(norm_bbox)
                    position_bbox[matched_key] = norm_bbox
                    position_texts[matched_key] = []

                position_texts[matched_key].append(text.strip())

    # Classify each position
    results: List[Dict[str, Any]] = []
    for bbox_key, texts in position_texts.items():
        unique_texts = set(texts)
        if len(unique_texts) <= 1:
            classification = "label"
            confidence = "confirmed"
        else:
            classification = "dynamic"
            confidence = "confirmed"

        results.append(
            {
                "bbox_key": bbox_key,
                "text_samples": sorted(unique_texts)[:5],  # keep up to 5 samples
                "classification": classification,
                "confidence": confidence,
            }
        )

    return results


def _analyse_cluster_single_pdf(
    skeletons: List[LayoutSkeleton],
) -> List[Dict[str, Any]]:
    """Single-PDF heuristic analysis.

    Returns element analysis with confidence="inferred".
    """
    seen_keys: Dict[str, Dict[str, Any]] = {}

    for skel in skeletons:
        for text, bbox in skel.text_blocks:
            key = _bbox_key(bbox)
            if key in seen_keys:
                continue

            stripped = text.strip()

            # Heuristic classification
            if _LABEL_SUFFIX_RE.search(stripped):
                classification = "label"
            elif _NUMERIC_RE.match(stripped):
                classification = "dynamic"
            elif len(stripped) <= 3 and stripped.isupper():
                # Short uppercase abbreviations often labels
                classification = "label"
            else:
                # Default: unknown short strings → label; longer → dynamic
                classification = "label" if len(stripped) <= 30 else "dynamic"

            seen_keys[key] = {
                "bbox_key": key,
                "text_samples": [stripped],
                "classification": classification,
                "confidence": "inferred",
            }

    return list(seen_keys.values())


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 13 executor — Multi-Example Analysis."""
    emit = context.get("emit_progress")

    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])
    skeletons: List[LayoutSkeleton] = context.get("_skeleton_objects", [])
    alignment_offsets: Dict[int, Dict[int, Tuple[float, float]]] = context.get(
        "alignment_offsets", {}
    )
    intel_meta: Dict[str, Any] = context.get("intelligence_metadata", {})
    single_doc: bool = intel_meta.get("single_document", False)

    element_labels: Dict[int, List[Dict[str, Any]]] = {}
    total_labels = 0
    total_dynamic = 0

    for lt in layout_types:
        cluster_id = lt.cluster_id
        offsets = alignment_offsets.get(cluster_id, {})

        if single_doc:
            cluster_skels = [
                s for s in skeletons
                if any(
                    s.pdf_index == p["pdf_index"] and s.page_number == p["page_number"]
                    for p in lt.pages
                )
            ]
            analysis = _analyse_cluster_single_pdf(cluster_skels)
        else:
            analysis = _analyse_cluster_multi_pdf(skeletons, lt.pages, offsets)

        element_labels[cluster_id] = analysis
        total_labels += sum(1 for e in analysis if e["classification"] == "label")
        total_dynamic += sum(1 for e in analysis if e["classification"] == "dynamic")

    context["_element_labels"] = element_labels

    summary = {
        "clusters_analysed": len(layout_types),
        "total_labels": total_labels,
        "total_dynamic": total_dynamic,
        "single_document": single_doc,
        "confidence_mode": "inferred" if single_doc else "confirmed",
    }

    if emit:
        try:
            emit(
                {
                    "stage": 13,
                    "stage_name": "Multi-Example Analysis",
                    "status": "completed",
                    "summary": summary,
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return summary


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace stub Stage 13 with this implementation."""
    registry.remove_stage(13)
    registry.register_stage(
        stage_number=13,
        name="Multi-Example Analysis",
        block_id=4,
        estimated_duration=2.0,
        execute_fn=execute,
    )
