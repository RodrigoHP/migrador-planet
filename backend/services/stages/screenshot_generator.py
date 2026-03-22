"""Stage 2b (auxiliary) — Screenshot Generator.

Renders each PDF page as a 150-DPI PNG using PyMuPDF and uploads via
StorageGateway.  For PDFs with more than 500 pages, only ~50
evenly-distributed pages are rendered.

Story 13.2: Uses StorageGateway (injected via context["_storage"]) instead
of writing directly to /tmp.  Falls back to local disk when no gateway is
present (backward compat during migration).
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.parsed_document import ParsedDocument, ParsedPage

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DPI = 150
MAX_SCREENSHOT_PAGES = 50
LARGE_PDF_THRESHOLD = 500


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _select_sample_pages(total_pages: int, max_pages: int = MAX_SCREENSHOT_PAGES) -> List[int]:
    """Return a list of evenly-distributed page indices to screenshot."""
    if total_pages <= max_pages:
        return list(range(total_pages))

    step = total_pages / max_pages
    return [int(math.floor(i * step)) for i in range(max_pages)]


def _render_pages_to_bytes(
    pdf_path: Path,
    pdf_index: int,
) -> Dict[int, tuple]:
    """Render pages to PNG bytes; return mapping page_number -> (page_key, png_bytes)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF (fitz) is required. Install it with: pip install PyMuPDF"
        ) from exc

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    pages_to_render = _select_sample_pages(total_pages)

    matrix = fitz.Matrix(DPI / 72, DPI / 72)  # type: ignore[attr-defined]
    results: Dict[int, tuple] = {}

    for page_num in pages_to_render:
        page = doc[page_num]
        pixmap = page.get_pixmap(matrix=matrix)  # type: ignore[attr-defined]
        page_key = f"page_{pdf_index}_{page_num}"
        png_bytes = pixmap.tobytes("png")
        results[page_num] = (page_key, png_bytes)

    doc.close()
    return results


def generate_screenshots(
    pdf_path: Path,
    screenshots_dir: Path,
    pdf_index: int,
) -> Dict[int, str]:
    """Render pages to PNG (legacy sync API); return mapping page_number -> file path.

    Kept for backward compatibility.  New code should use the async execute()
    which goes through StorageGateway.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF (fitz) is required. Install it with: pip install PyMuPDF"
        ) from exc

    screenshots_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    pages_to_render = _select_sample_pages(total_pages)

    matrix = fitz.Matrix(DPI / 72, DPI / 72)  # type: ignore[attr-defined]
    results: Dict[int, str] = {}

    for page_num in pages_to_render:
        page = doc[page_num]
        pixmap = page.get_pixmap(matrix=matrix)  # type: ignore[attr-defined]
        filename = f"page_{pdf_index}_{page_num}.png"
        out_path = screenshots_dir / filename
        pixmap.save(str(out_path))
        results[page_num] = str(out_path)

    doc.close()
    return results


# ---------------------------------------------------------------------------
# Stage executor (can be chained with text_extraction or run standalone)
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Screenshot generator executor.

    Reads parsed_documents from context and updates screenshot_path per page.
    Uses StorageGateway from context["_storage"] when available.
    """
    job_id: str = context.get("job_id", "")
    tmp_base = Path(context.get("tmp_base", "/tmp/jobs"))
    job_dir = tmp_base / job_id
    storage = context.get("_storage")

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    pdf_files: List[Path] = sorted(job_dir.glob("*.pdf"))

    total_screenshots = 0
    updated_docs: List[Dict[str, Any]] = []

    for doc_dict in parsed_documents:
        pdf_index = doc_dict.get("pdf_index", 0)
        pdf_name = doc_dict.get("pdf_name", "")

        pdf_path = job_dir / pdf_name
        if not pdf_path.exists() and pdf_index < len(pdf_files):
            pdf_path = pdf_files[pdf_index]

        try:
            if storage is not None:
                # New path: render to bytes, upload via gateway
                page_renders = _render_pages_to_bytes(
                    pdf_path=pdf_path,
                    pdf_index=pdf_index,
                )
                page_screenshots: Dict[int, str] = {}
                for page_num, (page_key, png_bytes) in page_renders.items():
                    url = await storage.upload_screenshot(job_id, page_key, png_bytes)
                    page_screenshots[page_num] = url
            else:
                # Legacy fallback: write directly to disk
                screenshots_dir = Path("/tmp") / job_id / "screenshots"
                page_screenshots = generate_screenshots(
                    pdf_path=pdf_path,
                    screenshots_dir=screenshots_dir,
                    pdf_index=pdf_index,
                )
        except Exception:  # noqa: BLE001
            updated_docs.append(doc_dict)
            continue

        parsed = ParsedDocument(**doc_dict)
        new_pages: List[ParsedPage] = []

        for page in parsed.pages:
            shot_path = page_screenshots.get(page.page_number)
            total_screenshots += 1 if shot_path else 0
            new_pages.append(
                ParsedPage(
                    page_number=page.page_number,
                    text_blocks=page.text_blocks,
                    images=page.images,
                    fonts=page.fonts,
                    grid_info=page.grid_info,
                    screenshot_path=shot_path,
                )
            )

        parsed.pages = new_pages
        updated_docs.append(parsed.to_context_dict())

    context["parsed_documents"] = updated_docs

    return {
        "screenshots_generated": total_screenshots,
    }


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_as_stage(registry, stage_number: int = 28) -> None:  # type: ignore[type-arg]
    """Optionally register screenshot generation as an explicit pipeline stage."""
    try:
        registry.remove_stage(stage_number)
    except Exception:  # noqa: BLE001
        pass
    # Screenshot generation requires Block 2 to already exist
    registry.register_stage(
        stage_number=stage_number,
        name="Screenshot Generator",
        block_id=2,
        estimated_duration=3.0,
        execute_fn=execute,
    )


def register(registry) -> None:  # type: ignore[type-arg]
    """Register screenshot generation as Stage 29 (Block 2), after Grid Detection (Stage 6).

    This ensures screenshot_path is populated in ParsedPage for Vision AI (Stage 20+).
    Runs after text extraction so parsed_documents are already in context.
    """
    try:
        registry.remove_stage(29)
    except Exception:  # noqa: BLE001
        pass
    registry.register_stage(
        stage_number=29,
        name="Screenshot Generator",
        block_id=2,
        estimated_duration=3.0,
        execute_fn=execute,
    )
