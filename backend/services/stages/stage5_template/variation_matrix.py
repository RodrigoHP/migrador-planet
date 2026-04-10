"""Stage 5 -- Variation Matrix sub-module (Step 5.5).

Responsibilities:
  - _step_5_5_variation_matrix: build variant + present_in_pdfs per layout

Story 41.3 -- extracted from stage5_template_generation.py
"""

from __future__ import annotations

import logging
from typing import Any

from models.pipeline_context import LayoutTypeInfo

logger = logging.getLogger(__name__)


def _step_5_5_variation_matrix(
    intelligence: dict[str, Any],
    clusters: list[dict[str, Any]],
    layout_types: list[LayoutTypeInfo],
    pdf_documents: list[dict[str, Any]],
    enriched_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """5.5 â€” Build VariationMatrix + Detections from block_classifications.

    Iterates nodes with variant != 'required' to build the matrix and
    detection list.
    """
    # 1. Build pdf list from clusters
    all_pdf_ids: set[str] = set()
    layout_pdf_map: dict[str, set[str]] = {}

    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        pdf_ids = {p.get("pdf_id") for p in cluster.get("pages", []) if p.get("pdf_id")}
        all_pdf_ids |= pdf_ids
        layout_pdf_map[layout_id] = pdf_ids

    if not all_pdf_ids:
        return {"pdfs": [], "matrix": {"layoutIds": [], "variationIds": [], "cells": {}}, "detections": []}

    # Determine base PDF (most cluster coverage)
    pdf_cluster_coverage: dict[str, int] = {}
    for cluster in clusters:
        contributing = {p.get("pdf_id") for p in cluster.get("pages", []) if p.get("pdf_id")}
        for pid in contributing:
            pdf_cluster_coverage[pid] = pdf_cluster_coverage.get(pid, 0) + 1

    base_pdf_id = max(
        sorted(all_pdf_ids),
        key=lambda pid: pdf_cluster_coverage.get(pid, 0),
    )

    # Build pdf metadata
    pdf_doc_map = {str(d.get("id", "")): d for d in (pdf_documents or [])}
    pdfs = []
    for pid in sorted(all_pdf_ids):
        doc_info = pdf_doc_map.get(pid, {})
        pdfs.append(
            {
                "id": pid,
                "name": doc_info.get("name", f"document-{pid}"),
                "role": "base" if pid == base_pdf_id else "variation",
                "sizeKB": 0,
                "pages": 0,
                "uploadedAt": "",
            }
        )

    # 2. Build cells: layoutId x pdfId -> present (layout-level)
    layout_ids = [lt.id for lt in layout_types]
    variation_ids = sorted(all_pdf_ids)

    cells: dict[str, dict[str, bool]] = {}
    for layout_id in layout_ids:
        cells[layout_id] = {}
        for pdf_id in variation_ids:
            cells[layout_id][pdf_id] = pdf_id in layout_pdf_map.get(layout_id, set())

    # Story 35.6: Build field-level matrix from block_classifications
    field_ids: list[str] = []
    field_cells: dict[str, dict[str, bool]] = {}

    for layout_id, intel_data in intelligence.items():
        block_classifications = intel_data.get("block_classifications", {})
        for block_id, classification in block_classifications.items():
            if block_id in field_cells:
                continue
            field_ids.append(block_id)
            present_in = set(classification.get("present_in_pdfs") or [])
            field_cells[block_id] = {}
            for pdf_id in variation_ids:
                field_cells[block_id][pdf_id] = pdf_id in present_in

    matrix = {
        "layoutIds": layout_ids,
        "variationIds": variation_ids,
        "cells": cells,
        "fieldIds": field_ids,
        "fieldCells": field_cells,
    }

    # 3. Generate Detections from block_classifications
    detections: list[dict[str, Any]] = []
    for layout_id, intel_data in intelligence.items():
        block_classifications = intel_data.get("block_classifications", {})

        # Story 35.8: Group adjacent blocks with same present_in_pdfs
        ordered_blocks = list(block_classifications.items())
        i = 0
        while i < len(ordered_blocks):
            block_id, classification = ordered_blocks[i]
            variant = classification.get("variant", "required")
            if variant == "required":
                i += 1
                continue

            present_in = classification.get("present_in_pdfs", [])
            present_key = tuple(sorted(present_in))

            # Look ahead for adjacent blocks with same present_in_pdfs
            group = [block_id]
            j = i + 1
            while j < len(ordered_blocks):
                next_id, next_cls = ordered_blocks[j]
                next_variant = next_cls.get("variant", "required")
                if next_variant == "required":
                    break
                next_present = tuple(sorted(next_cls.get("present_in_pdfs", [])))
                if next_present != present_key:
                    break
                group.append(next_id)
                j += 1

            if len(group) >= 2:
                # Story 35.8: Emit optional_section detection for the group
                section_id = f"section-{group[0]}-{group[-1]}"
                block_labels = ", ".join(group)
                detections.append(
                    {
                        "id": f"det-{section_id}",
                        "pdfId": present_in[0] if present_in else "",
                        "type": "optional_section",
                        "description": f"SeÃ§Ã£o opcional: [{block_labels}] â€” presente em {len(present_in)}/{len(all_pdf_ids)} PDFs",
                        "confidence": len(present_in) / len(all_pdf_ids) if all_pdf_ids else 0,
                        "nodeBinding": group[0],
                        "groupedBlocks": group,
                    }
                )
            else:
                det_type = "conditional_section" if variant == "conditional" else "optional_field"
                detections.append(
                    {
                        "id": f"det-{block_id}",
                        "pdfId": present_in[0] if present_in else "",
                        "type": det_type,
                        "description": f"Bloco presente em {len(present_in)}/{len(all_pdf_ids)} PDFs",
                        "confidence": len(present_in) / len(all_pdf_ids) if all_pdf_ids else 0,
                        "nodeBinding": block_id,
                    }
                )

            i = j

    # Story 35.9: Detect dynamic tables (varying row counts across PDFs)
    if enriched_documents and len(enriched_documents) > 1:
        # Collect row_count per table_id per pdf_id
        table_row_counts: dict[str, dict[str, int]] = {}
        for doc in enriched_documents:
            pdf_id = str(doc.get("pdf_id", doc.get("id", "")))
            for page in doc.get("pages", []):
                for table in page.get("tables", []):
                    tid = table.get("table_id", "")
                    if not tid:
                        continue
                    row_count = table.get("row_count", 0)
                    if tid not in table_row_counts:
                        table_row_counts[tid] = {}
                    table_row_counts[tid][pdf_id] = row_count

        for tid, counts_by_pdf in table_row_counts.items():
            if len(counts_by_pdf) < 2:
                continue
            row_values = list(counts_by_pdf.values())
            min_rows = min(row_values)
            max_rows = max(row_values)
            if min_rows != max_rows:
                detections.append(
                    {
                        "id": f"det-dyntable-{tid}",
                        "pdfId": "",
                        "type": "dynamic_table",
                        "description": f"Tabela dinÃ¢mica: {min_rows}-{max_rows} linhas",
                        "confidence": 0.85,
                        "nodeBinding": tid,
                        "rowRange": {"min": min_rows, "max": max_rows},
                    }
                )

    return {"pdfs": pdfs, "matrix": matrix, "detections": detections}


# ---------------------------------------------------------------------------
# 5.6 PipelineResult Assembly
# ---------------------------------------------------------------------------
