"""Stage 15 — Variant Detection.

Analyses the stability_map from Stage 14 to detect structural variants:

  * optional_field       — element with classification "absent"
                           (present in some docs, missing in others)
  * conditional_section  — group of adjacent "absent" elements that share
                           the same absence pattern (all present / all absent
                           together across documents)
  * dynamic_table        — table candidates whose row count varies across
                           documents in the cluster

Reads:
    context["_stability_map"]        — Dict[cluster_id → stability_map]
    context["_element_labels"]       — Dict[cluster_id → List[element_analysis]]
    context["_layout_type_objects"]  — List[LayoutType]
    context["_skeleton_objects"]     — List[LayoutSkeleton] (for table row counts)
    context["intelligence_metadata"] — may contain single_document flag

Writes:
    context["_variants"]             — Dict[cluster_id → List[variant]]
      variant = {
          "type": "optional_field" | "conditional_section" | "dynamic_table",
          "elements": List[bbox_key],
          "presence_pattern": str,   # e.g. "3/5 docs"
      }
    context["_conditional_sections"] — Dict[cluster_id → List[section]]
      section = {
          "elements": List[bbox_key],
          "presence_pattern": str,
      }

Registers itself as Stage 15 (Block 4).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from models.layout_type import LayoutSkeleton, LayoutType

# Minimum group size to declare a conditional section
_MIN_SECTION_SIZE = 2

# Y-proximity threshold for "adjacent" blocks (in PDF points)
_ADJACENCY_Y_THRESHOLD = 30.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_bbox_key(key: str) -> Tuple[float, float, float, float]:
    """Parse a bbox_key string back to a tuple."""
    parts = key.split(",")
    if len(parts) != 4:
        return (0.0, 0.0, 0.0, 0.0)
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


def _are_adjacent_y(
    bbox_a: Tuple[float, float, float, float],
    bbox_b: Tuple[float, float, float, float],
    threshold: float = _ADJACENCY_Y_THRESHOLD,
) -> bool:
    """True when the vertical gap between two bboxes is within threshold."""
    # Check overlap or close proximity on Y axis
    top_a, bot_a = min(bbox_a[1], bbox_a[3]), max(bbox_a[1], bbox_a[3])
    top_b, bot_b = min(bbox_b[1], bbox_b[3]), max(bbox_b[1], bbox_b[3])
    gap = max(0.0, max(top_a, top_b) - min(bot_a, bot_b))
    return gap <= threshold


def _group_adjacent_absent(
    absent_keys: List[str],
    stability_map: Dict[str, Dict[str, Any]],
) -> List[List[str]]:
    """Group absent elements that are vertically adjacent into sections."""
    if not absent_keys:
        return []

    # Sort by y0 coordinate
    keyed = [(k, _parse_bbox_key(k)) for k in absent_keys]
    keyed.sort(key=lambda t: t[1][1])

    groups: List[List[str]] = []
    current_group: List[str] = [keyed[0][0]]

    for i in range(1, len(keyed)):
        prev_bbox = _parse_bbox_key(current_group[-1])
        curr_bbox = keyed[i][1]
        if _are_adjacent_y(prev_bbox, curr_bbox):
            current_group.append(keyed[i][0])
        else:
            groups.append(current_group)
            current_group = [keyed[i][0]]
    groups.append(current_group)

    return groups


def _detect_dynamic_tables(
    lt: LayoutType,
    skeletons: List[LayoutSkeleton],
) -> List[Dict[str, Any]]:
    """Detect table candidates with varying row counts across PDFs."""
    skel_map: Dict[Tuple[int, int], LayoutSkeleton] = {
        (s.pdf_index, s.page_number): s for s in skeletons
    }

    # Count table candidates per PDF in this cluster
    pdf_table_counts: Dict[int, List[int]] = {}
    for page_ref in lt.pages:
        key = (page_ref["pdf_index"], page_ref["page_number"])
        skel = skel_map.get(key)
        if skel is None:
            continue
        pdf_idx = page_ref["pdf_index"]
        pdf_table_counts.setdefault(pdf_idx, []).append(skel.table_count)

    if len(pdf_table_counts) < 2:
        return []

    # Average table count per PDF
    avg_counts = {
        pdf_idx: sum(counts) / len(counts)
        for pdf_idx, counts in pdf_table_counts.items()
    }
    values = list(avg_counts.values())
    if max(values) - min(values) > 0.5:
        return [
            {
                "type": "dynamic_table",
                "elements": ["table_candidates"],
                "presence_pattern": f"table_count varies: min={min(values):.1f} max={max(values):.1f}",
            }
        ]
    return []


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 15 executor — Variant Detection."""
    emit = context.get("emit_progress")

    stability_maps: Dict[int, Dict[str, Dict[str, Any]]] = context.get(
        "_stability_map", {}
    )
    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])
    skeletons: List[LayoutSkeleton] = context.get("_skeleton_objects", [])
    intel_meta: Dict[str, Any] = context.get("intelligence_metadata", {})
    single_doc: bool = intel_meta.get("single_document", False)

    all_variants: Dict[int, List[Dict[str, Any]]] = {}
    all_conditional_sections: Dict[int, List[Dict[str, Any]]] = {}

    total_optional = 0
    total_conditional = 0
    total_dynamic_tables = 0

    for lt in layout_types:
        cluster_id = lt.cluster_id
        smap = stability_maps.get(cluster_id, {})
        variants: List[Dict[str, Any]] = []
        sections: List[Dict[str, Any]] = []

        if single_doc:
            # Cannot determine variants without multiple docs
            all_variants[cluster_id] = []
            all_conditional_sections[cluster_id] = []
            continue

        total_docs = next(
            (v["total_docs"] for v in smap.values() if v), 1
        )

        # Optional fields: absent elements
        absent_keys = [
            k for k, v in smap.items() if v["classification"] == "absent"
        ]
        for k in absent_keys:
            info = smap[k]
            variants.append(
                {
                    "type": "optional_field",
                    "elements": [k],
                    "presence_pattern": f"{info['doc_count']}/{total_docs} docs",
                }
            )
            total_optional += 1

        # Conditional sections: groups of adjacent absent elements
        groups = _group_adjacent_absent(absent_keys, smap)
        for group in groups:
            if len(group) >= _MIN_SECTION_SIZE:
                doc_count = smap[group[0]]["doc_count"]
                sections.append(
                    {
                        "elements": group,
                        "presence_pattern": f"{doc_count}/{total_docs} docs",
                    }
                )
                total_conditional += 1

        # Dynamic tables
        dyn_tables = _detect_dynamic_tables(lt, skeletons)
        variants.extend(dyn_tables)
        total_dynamic_tables += len(dyn_tables)

        all_variants[cluster_id] = variants
        all_conditional_sections[cluster_id] = sections

    context["_variants"] = all_variants
    context["_conditional_sections"] = all_conditional_sections

    summary = {
        "clusters_scanned": len(layout_types),
        "total_optional_fields": total_optional,
        "total_conditional_sections": total_conditional,
        "total_dynamic_tables": total_dynamic_tables,
        "single_document": single_doc,
    }

    if emit:
        try:
            emit(
                {
                    "stage": 15,
                    "stage_name": "Variant Detection",
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
    """Replace stub Stage 15 with this implementation."""
    registry.remove_stage(15)
    registry.register_stage(
        stage_number=15,
        name="Variant Detection",
        block_id=4,
        estimated_duration=1.0,
        execute_fn=execute,
    )
