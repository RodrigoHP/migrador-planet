"""Stage 2 — Deep Extraction (So Representativas).

Story 13.5 — Extracts complete data (text, fonts, images, tables, drawn elements)
from representative pages only, reducing extraction time from ~20min (100 pages)
to ~10s (~6 representatives).

Story 41.3 — Decomposed into sub-modules under stage2_extraction/:
  - text_extraction.py      : FONT_MAP, spans, block merge, font-to-css
  - media_extraction.py     : image extraction, screenshot
  - grid_table_extraction.py: grid detection, table detect/structure, quality check

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 6 (Stage 2)
Output contract: Section 3.2
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Re-exports — backward compatibility
# ---------------------------------------------------------------------------
from services.stages.stage2_extraction.grid_table_extraction import (  # noqa: F401
    _check_ruling_lines,
    _color_to_int,
    _detect_grid_jenks,
    _detect_header_rows,
    _detect_tables,
    _extract_drawn_elements,
    _fallback_gap_groups,
    _jenks_1d,
    _line_orientation,
    _quality_check,
    _structure_tables,
)
from services.stages.stage2_extraction.media_extraction import (  # noqa: F401
    _extract_images,
    _take_screenshot,
)
from services.stages.stage2_extraction.text_extraction import (  # noqa: F401
    FONT_MAP,
    _build_block_from_spans,
    _collect_page_fonts,
    _extract_spans_from_page,
    _font_to_css,
    _merge_spans_to_blocks,
    _normalize_pdf_font_name,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# PyMuPDF version check
# ---------------------------------------------------------------------------

_MINIMUM_PYMUPDF_VERSION = (1, 23, 0)


def check_pymupdf_version() -> None:
    """Verify PyMuPDF >= 1.23.0 (find_tables, get_drawings support)."""
    version_str = fitz.version[0]  # e.g. "1.24.0"
    parts = tuple(int(x) for x in version_str.split(".")[:3])
    if parts < _MINIMUM_PYMUPDF_VERSION:
        raise RuntimeError(
            f"PyMuPDF >= {'.'.join(str(v) for v in _MINIMUM_PYMUPDF_VERSION)} required, found {version_str}"
        )


# ---------------------------------------------------------------------------
# Sub-progress helper
# ---------------------------------------------------------------------------


async def _emit_sub(
    emit: EmitProgressFn,
    sub_step: str,
    sub_pct: float,
) -> None:
    """Emit a Stage 2 sub-progress event."""
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    event = make_sub_progress_event(
        stage=2,
        stage_name="Deep Extraction",
        status="running",
        progress_pct=compute_overall_progress(2, sub_pct),
        sub_step=sub_step,
        sub_progress_pct=sub_pct,
    )
    await emit(event)


# ---------------------------------------------------------------------------
# Stage entry point
# ---------------------------------------------------------------------------


async def run_stage2(
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, Any]:
    """Stage 2: Deep Extraction — ONLY representative pages.

    Args:
        context: Pipeline context with clusters, pdf_documents, _storage, job_id.
        emit_progress: Async callback for SSE events.

    Returns:
        Updated context with enriched_documents, extraction_warnings.
    """
    context["_current_stage"] = 2
    context["_current_stage_name"] = "Deep Extraction"

    # Check PyMuPDF version
    check_pymupdf_version()

    clusters: list[dict[str, Any]] = context.get("clusters", [])
    pdf_documents: list[dict[str, str]] = context.get("pdf_documents", [])
    storage = context.get("_storage")
    job_id = context.get("job_id", "")

    if not clusters or not pdf_documents:
        context["enriched_documents"] = []
        context["extraction_warnings"] = []
        from services.pipeline_orchestrator_v2 import compute_overall_progress, make_sub_progress_event

        await emit_progress(
            make_sub_progress_event(
                stage=2,
                stage_name="Deep Extraction",
                status="running",
                progress_pct=compute_overall_progress(2, 1.0),
                sub_step="2.0 Complete",
                sub_progress_pct=1.0,
                summary={"pages_processed": 0, "warnings": 0},
            )
        )
        return context

    # Build pdf_id -> path map
    pdf_docs_map: dict[str, str] = {}
    pdf_names_map: dict[str, str] = {}
    for doc in pdf_documents:
        pid = str(doc["id"])
        pdf_docs_map[pid] = doc["path"]
        pdf_names_map[pid] = doc.get("name", "")

    # Identify representative pages and build cluster membership
    representative_pages: list[dict[str, Any]] = []
    page_cluster_map: dict[str, str] = {}  # "pdf_id:page_index" -> cluster_id
    page_representative_map: dict[str, bool] = {}  # "pdf_id:page_index" -> is_representative

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        rep = cluster.get("representative_page", {})
        rep_key = f"{rep['pdf_id']}:{rep['page_index']}"

        for page_info in cluster.get("pages", []):
            pk = f"{page_info['pdf_id']}:{page_info['page_index']}"
            page_cluster_map[pk] = cluster_id
            page_representative_map[pk] = pk == rep_key

        representative_pages.append(
            {
                "pdf_id": rep["pdf_id"],
                "page_index": rep["page_index"],
                "cluster_id": cluster_id,
            }
        )

    # ===================================================
    # Process ONLY representative pages
    # ===================================================

    # Group by pdf_id for efficient PDF opening
    reps_by_pdf: dict[str, list[dict[str, Any]]] = {}
    for rp in representative_pages:
        reps_by_pdf.setdefault(rp["pdf_id"], []).append(rp)

    # Result containers
    enriched_by_pdf: dict[str, dict[str, Any]] = {}
    all_warnings: list[dict[str, Any]] = []

    total_reps = len(representative_pages)
    processed = 0

    for pdf_id, reps in reps_by_pdf.items():
        pdf_path = pdf_docs_map.get(pdf_id)
        if not pdf_path:
            continue

        doc = fitz.open(pdf_path)
        pdf_name = pdf_names_map.get(pdf_id, "")

        if pdf_id not in enriched_by_pdf:
            enriched_by_pdf[pdf_id] = {
                "pdf_id": pdf_id,
                "pdf_name": pdf_name,
                "pages": [],
            }

        for rp in reps:
            page_index = rp["page_index"]
            cluster_id = rp["cluster_id"]

            if page_index >= len(doc):
                continue

            page = doc[page_index]

            # --- 2.1 Full Text + Metadata ---
            await _emit_sub(emit_progress, "2.1 Text Extraction", processed / max(total_reps, 1) * 0.15)
            spans, width, height = _extract_spans_from_page(page)

            # --- 2.2 Text Reconstruction ---
            await _emit_sub(emit_progress, "2.2 Text Reconstruction", processed / max(total_reps, 1) * 0.25)
            text_blocks = _merge_spans_to_blocks(spans)

            # --- 2.3 Font -> CSS ---
            fonts = _collect_page_fonts(text_blocks)

            # --- 2.4 Image Extraction ---
            await _emit_sub(emit_progress, "2.4 Image Extraction", 0.30 + processed / max(total_reps, 1) * 0.15)
            if storage is not None:
                images = await _extract_images(page, doc, page_index, pdf_id, storage, job_id)
            else:
                images = []

            # --- 2.5 Screenshot ---
            await _emit_sub(emit_progress, "2.5 Screenshot", 0.45 + processed / max(total_reps, 1) * 0.10)
            if storage is not None:
                screenshot_path = await _take_screenshot(page, page_index, pdf_id, storage, job_id)
            else:
                screenshot_path = None

            # --- 2.6 Grid Detection ---
            await _emit_sub(emit_progress, "2.6 Grid Detection", 0.55 + processed / max(total_reps, 1) * 0.10)
            grid_info = _detect_grid_jenks(text_blocks, height)

            # --- 2.7 Table Detection ---
            await _emit_sub(emit_progress, "2.7 Table Detection", 0.65 + processed / max(total_reps, 1) * 0.10)
            raw_tables = _detect_tables(page)

            # --- 2.8 Table Structuring ---
            await _emit_sub(emit_progress, "2.8 Table Structuring", 0.75 + processed / max(total_reps, 1) * 0.10)
            tables = _structure_tables(raw_tables, text_blocks, height)

            # --- 2.9 Quality Check + Drawn Elements ---
            await _emit_sub(emit_progress, "2.9 Quality Check", 0.85 + processed / max(total_reps, 1) * 0.15)
            drawn_elements = _extract_drawn_elements(page)

            page_data: dict[str, Any] = {
                "page_index": page_index,
                "cluster_id": cluster_id,
                "is_representative": True,
                "width": width,
                "height": height,
                "text_blocks": text_blocks,
                "images": images,
                "fonts": fonts,
                "grid_info": grid_info,
                "screenshot_path": screenshot_path,
                "tables": tables,
                "drawn_elements": drawn_elements,
            }

            # Quality check
            page_warnings = _quality_check(page_data, page_index, pdf_id)
            all_warnings.extend(page_warnings)

            enriched_by_pdf[pdf_id]["pages"].append(page_data)
            processed += 1

        doc.close()

    # Also add non-representative pages with minimal data (cluster_id, is_representative=False)
    non_rep_by_pdf: dict[str, list[tuple[int, str]]] = {}  # pdf_id -> [(page_index, cluster_id)]
    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        rep = cluster.get("representative_page", {})
        rep_key = f"{rep['pdf_id']}:{rep['page_index']}"

        for page_info in cluster.get("pages", []):
            pk = f"{page_info['pdf_id']}:{page_info['page_index']}"
            if pk == rep_key:
                continue  # already processed

            pdf_id = page_info["pdf_id"]
            page_index = page_info["page_index"]
            non_rep_by_pdf.setdefault(pdf_id, []).append((page_index, cluster_id))

    for pdf_id, pages_info in non_rep_by_pdf.items():
        if pdf_id not in enriched_by_pdf:
            enriched_by_pdf[pdf_id] = {
                "pdf_id": pdf_id,
                "pdf_name": pdf_names_map.get(pdf_id, ""),
                "pages": [],
            }

        pdf_path = pdf_docs_map.get(pdf_id)
        _doc = None
        if pdf_path:
            try:
                _doc = fitz.open(pdf_path)
            except Exception:
                pass

        for page_index, cluster_id in pages_info:
            w, h = 0.0, 0.0
            if _doc is not None and page_index < len(_doc):
                _page = _doc[page_index]
                w = float(_page.rect.width)
                h = float(_page.rect.height)

            enriched_by_pdf[pdf_id]["pages"].append(
                {
                    "page_index": page_index,
                    "cluster_id": cluster_id,
                    "is_representative": False,
                    "width": w,
                    "height": h,
                    "text_blocks": [],
                    "images": [],
                    "fonts": [],
                    "grid_info": None,
                    "screenshot_path": None,
                    "tables": [],
                    "drawn_elements": None,
                }
            )

        if _doc is not None:
            _doc.close()

    # Build final output
    enriched_documents = list(enriched_by_pdf.values())

    # Sort pages within each document
    for doc_data in enriched_documents:
        doc_data["pages"].sort(key=lambda p: p["page_index"])

    context["enriched_documents"] = enriched_documents
    context["extraction_warnings"] = all_warnings

    await _emit_sub(emit_progress, "2.9 Complete", 1.0)

    logger.info(
        "Stage 2 complete: %d representative pages processed, %d warnings",
        processed,
        len(all_warnings),
    )

    # Emit final summary for the accordion
    from services.pipeline_orchestrator_v2 import compute_overall_progress, make_sub_progress_event

    rep_pages = [p for doc_data in enriched_documents for p in doc_data.get("pages", []) if p.get("is_representative")]
    total_blocks = sum(len(p.get("text_blocks", [])) for p in rep_pages)
    total_images = sum(len(p.get("images", [])) for p in rep_pages)
    total_tables = sum(len(p.get("tables", [])) for p in rep_pages)
    total_fonts = sum(len(p.get("fonts", [])) for p in rep_pages)
    await emit_progress(
        make_sub_progress_event(
            stage=2,
            stage_name="Deep Extraction",
            status="running",
            progress_pct=compute_overall_progress(2, 1.0),
            sub_step="2.9 Complete",
            sub_progress_pct=1.0,
            summary={
                "pages_processed": processed,
                "blocks_extracted": total_blocks,
                "warnings": len(all_warnings),
                "images_extracted": total_images,
                "tables_detected": total_tables,
                "fonts_identified": total_fonts,
            },
        )
    )

    return context
