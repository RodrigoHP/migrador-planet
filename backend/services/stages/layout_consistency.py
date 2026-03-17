"""Stage 26 — Layout Consistency Validation.

Validates cross-consistency between skeleton/layout detection results and the
final field mapping results from Stage 23/24.

Checks:
    1. Skeleton vs result: TextBlocks classified as 'value' should have a
       corresponding field_mapping entry.
    2. XSD coverage: all XSD paths in field_tree.flat_paths should be mapped
       or reported as unmapped (warnings).
    3. No orphan mappings: every xsd_field_path in field_mappings must exist
       in field_tree.flat_paths (errors if not).
    4. Tables: if context["tables"] has entries with headers, check that at
       least one field_mapping references a table cell.

Reads:
    context["field_mappings"]   — List[Dict] from Stage 23/24
    context["field_tree"]       — Dict with "flat_paths" key
    context["parsed_documents"] — List[Dict] to count 'value' blocks
    context["tables"]           — optional List[Dict] from Stage 18

Writes:
    context["validation_result"] — Dict:
        {
          "warnings": List[str],
          "errors": List[str],
          "orphan_count": int,
          "unmapped_xsd_fields": List[str],
        }

Registers itself as Stage 26 (Block 8).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _collect_value_block_count(parsed_documents: List[Dict[str, Any]]) -> int:
    """Return the total number of 'value' semantic blocks across all documents."""
    count = 0
    for doc in parsed_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("semantic_label") == "value":
                    count += 1
    return count


def _check_skeleton_vs_mappings(
    value_block_count: int,
    field_mappings: List[Dict[str, Any]],
    warnings: List[str],
) -> None:
    """Warn if many value blocks are unmapped."""
    mapped_count = len(field_mappings)
    if value_block_count > 0 and mapped_count < value_block_count:
        diff = value_block_count - mapped_count
        warnings.append(
            f"skeleton_vs_result: {diff} value block(s) have no field_mapping entry "
            f"({mapped_count}/{value_block_count} mapped)."
        )


def _check_xsd_coverage(
    flat_paths: List[str],
    mapped_paths: Set[str],
    warnings: List[str],
) -> List[str]:
    """Return list of XSD fields not covered by any mapping; append warnings."""
    unmapped = [p for p in flat_paths if p not in mapped_paths and p != ""]
    if unmapped:
        warnings.append(
            f"xsd_coverage: {len(unmapped)} XSD field(s) have no mapping: "
            + ", ".join(unmapped[:10])
            + ("..." if len(unmapped) > 10 else "")
        )
    return unmapped


def _check_orphan_mappings(
    flat_paths_set: Set[str],
    field_mappings: List[Dict[str, Any]],
    errors: List[str],
) -> int:
    """Return count of orphan mappings; append errors for each orphan."""
    orphans = 0
    for m in field_mappings:
        path = m.get("xsd_field_path", "")
        if path and path not in flat_paths_set:
            orphans += 1
            errors.append(
                f"orphan_mapping: xsd_field_path '{path}' does not exist in field_tree.flat_paths."
            )
    return orphans


def _check_table_coverage(
    tables: List[Dict[str, Any]],
    field_mappings: List[Dict[str, Any]],
    warnings: List[str],
) -> None:
    """Warn if a table with headers has no corresponding field_mapping."""
    tables_with_headers = [t for t in tables if t.get("headers")]
    if not tables_with_headers:
        return

    # Check if any mapping references a table cell (is_table_cell key or from_table)
    has_table_mapping = any(
        m.get("is_table_cell") or m.get("from_table")
        for m in field_mappings
    )
    if not has_table_mapping:
        warnings.append(
            f"table_coverage: {len(tables_with_headers)} table(s) with headers detected "
            "but no field_mapping references a table cell."
        )


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 26 executor — Layout Consistency Validation."""
    emit = context.get("emit_progress")

    if emit:
        try:
            emit(
                {
                    "stage": 26,
                    "stage_name": "Layout Consistency Validation",
                    "status": "running",
                    "summary": {},
                }
            )
        except Exception:  # noqa: BLE001
            pass

    field_mappings: List[Dict[str, Any]] = context.get("field_mappings", [])
    field_tree: Dict[str, Any] = context.get("field_tree") or {}
    flat_paths: List[str] = field_tree.get("flat_paths", [])
    flat_paths_set: Set[str] = set(p for p in flat_paths if p)

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    tables: List[Dict[str, Any]] = context.get("tables", [])

    warnings: List[str] = []
    errors: List[str] = []

    # 1. Skeleton vs result
    value_block_count = _collect_value_block_count(parsed_documents)
    _check_skeleton_vs_mappings(value_block_count, field_mappings, warnings)

    # 2. XSD coverage
    mapped_paths: Set[str] = {m.get("xsd_field_path", "") for m in field_mappings}
    unmapped_xsd_fields = _check_xsd_coverage(flat_paths, mapped_paths, warnings)

    # 3. Orphan mappings
    orphan_count = _check_orphan_mappings(flat_paths_set, field_mappings, errors)

    # 4. Table coverage
    _check_table_coverage(tables, field_mappings, warnings)

    validation_result: Dict[str, Any] = {
        "warnings": warnings,
        "errors": errors,
        "orphan_count": orphan_count,
        "unmapped_xsd_fields": unmapped_xsd_fields,
    }

    context["validation_result"] = validation_result

    summary = {
        "warning_count": len(warnings),
        "error_count": len(errors),
        "orphan_count": orphan_count,
        "unmapped_xsd_count": len(unmapped_xsd_fields),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 26,
                    "stage_name": "Layout Consistency Validation",
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
    """Replace stub Stage 26 with this implementation."""
    registry.remove_stage(26)
    registry.register_stage(
        stage_number=26,
        name="Layout Consistency",
        block_id=8,
        estimated_duration=1.0,
        execute_fn=execute,
    )
