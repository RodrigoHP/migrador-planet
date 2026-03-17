"""Stage 10 — Fingerprint Generation.

For each LayoutType produced by Stage 9 (Representative Selection), generates
a structural fingerprint:

    {
        "tableCount":     average table candidates per page in the cluster,
        "columnCount":    number of grid columns from representative page,
        "headerBlocks":   average text blocks in the header zone,
        "bodyZoneRatio":  fraction of page occupied by body zone,
        "footerPresent":  True when any cluster page has footer-zone blocks,
    }

A SHA-256 hash of the canonical JSON of this dict is also computed for quick
lookup in the Supabase layout_registry.

Registers itself in the default_registry as Stage 10 (Block 3).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from models.layout_type import LayoutFingerprint, LayoutSkeleton, LayoutType


# ---------------------------------------------------------------------------
# Fingerprint computation
# ---------------------------------------------------------------------------


def _compute_fingerprint(
    skeletons: List[LayoutSkeleton],
) -> LayoutFingerprint:
    """Derive a LayoutFingerprint from a list of page skeletons."""
    if not skeletons:
        return LayoutFingerprint()

    n = len(skeletons)

    # tableCount — average table candidates per page
    table_count = sum(s.table_count for s in skeletons) / n

    # columnCount — from grid_info of the representative (or any available)
    column_count = 0
    for s in skeletons:
        if s.grid_info and s.grid_info.get("columns", 0) > 0:
            column_count = int(s.grid_info["columns"])
            break

    # headerBlocks — text blocks whose Y-centre falls in the header zone
    header_block_counts = []
    for s in skeletons:
        header_bottom_abs = s.zones.header_bottom * s.page_height
        count = sum(
            1
            for _, bbox in s.text_blocks
            if (bbox[1] + bbox[3]) / 2.0 <= header_bottom_abs
        )
        header_block_counts.append(count)
    header_blocks = sum(header_block_counts) / n if header_block_counts else 0.0

    # bodyZoneRatio — fraction of page occupied by the body zone
    body_zone_ratio = (
        skeletons[0].zones.body_bottom - skeletons[0].zones.body_top
        if skeletons
        else 0.75
    )

    # footerPresent — any page has blocks in the footer zone
    footer_present = False
    for s in skeletons:
        footer_top_abs = s.zones.footer_top * s.page_height
        for _, bbox in s.text_blocks:
            y_centre = (bbox[1] + bbox[3]) / 2.0
            if y_centre >= footer_top_abs:
                footer_present = True
                break
        if footer_present:
            break

    fp = LayoutFingerprint(
        table_count=table_count,
        column_count=column_count,
        header_blocks=header_blocks,
        body_zone_ratio=body_zone_ratio,
        footer_present=footer_present,
    )

    # Generate SHA-256 hash
    canonical = json.dumps(fp.to_dict(), sort_keys=True, separators=(",", ":"))
    fp.fingerprint_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return fp


def compute_fingerprint_hash(fingerprint_dict: Dict[str, Any]) -> str:
    """Compute SHA-256 of a canonical fingerprint dict (public helper)."""
    canonical = json.dumps(fingerprint_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 10 executor — Fingerprint Generation.

    Reads context["_layout_type_objects"] (list of LayoutType).
    Updates each LayoutType's fingerprint in-place.
    Re-serialises context["layout_types"] with updated fingerprints.
    """
    emit = context.get("emit_progress")

    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])

    for lt in layout_types:
        cluster_skeletons: List[LayoutSkeleton] = getattr(
            lt, "_cluster_skeletons", []
        )
        fp = _compute_fingerprint(cluster_skeletons)
        lt.fingerprint = fp

        # Update the name now that we have a real fingerprint
        from services.stages.representative_selection import _name_for_fingerprint
        lt.name = _name_for_fingerprint(fp, lt.cluster_id)

    # Re-serialise
    context["layout_types"] = [lt.to_dict() for lt in layout_types]

    if emit:
        try:
            emit(
                {
                    "stage": 10,
                    "stage_name": "Fingerprint Generation",
                    "status": "completed",
                    "summary": {"fingerprints_generated": len(layout_types)},
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return {"fingerprints_generated": len(layout_types)}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 10 in the given registry with this implementation."""
    registry.remove_stage(10)
    registry.register_stage(
        stage_number=10,
        name="Fingerprint Generation",
        block_id=3,
        estimated_duration=1.0,
        execute_fn=execute,
    )
