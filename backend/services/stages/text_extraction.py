"""Stage 2 — Text Extraction.

Extracts TextBlocks (with bbox, font metadata) from every page of every PDF
in the job directory using PyMuPDF (fitz).

Registers itself in the default_registry as Stage 2 (Block 2).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from models.parsed_document import ParsedDocument, ParsedPage, TextBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_SCREENSHOT_PAGES = 50  # used by screenshot_generator; exported here for reuse


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _extract_text_from_pdf(
    pdf_path: Path,
    job_id: str,
    pdf_index: int,
) -> ParsedDocument:
    """Open a PDF, extract text blocks per page, return a ParsedDocument.

    Raises ValueError if the PDF is password-protected.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError("PyMuPDF (fitz) is required. Install it with: pip install PyMuPDF") from exc

    doc = fitz.open(str(pdf_path))

    if doc.is_encrypted:
        doc.close()
        raise ValueError(
            "PDF protegido por senha — remova a proteção e faça upload novamente"
        )

    parsed_doc = ParsedDocument(
        job_id=job_id,
        pdf_index=pdf_index,
        pdf_name=pdf_path.name,
    )

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw = page.get_text("dict")  # type: ignore[attr-defined]

        blocks: List[TextBlock] = []
        for block in raw.get("blocks", []):
            if block.get("type") != 0:  # 0 = text, 1 = image
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = span["bbox"]
                    blocks.append(
                        TextBlock(
                            text=text,
                            bbox=(x0, y0, x1, y1),
                            font_name=span.get("font", ""),
                            font_size=float(span.get("size", 0.0)),
                            page_number=page_num,
                            pdf_index=pdf_index,
                        )
                    )

        parsed_page = ParsedPage(page_number=page_num, text_blocks=blocks)
        parsed_doc.pages.append(parsed_page)

    doc.close()
    return parsed_doc


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 2 executor — Text Extraction.

    Expects context["job_id"] to point to a job that has PDF files in
    /tmp/jobs/{job_id}/ (or TMP_BASE/{job_id}/).

    Writes parsed documents into context["parsed_documents"] (list of dicts).
    """
    job_id: str = context.get("job_id", "")
    tmp_base = Path(context.get("tmp_base", "/tmp/jobs"))
    job_dir = tmp_base / job_id

    pdf_files: List[Path] = sorted(job_dir.glob("*.pdf"))

    if not pdf_files:
        # Fallback: look one level up for PDFs (some upload routers store them flat)
        pdf_files = sorted(Path("/tmp") / "jobs" / job_id / "" for _ in [None]).__class__(
            [p for p in job_dir.rglob("*.pdf")]
        )

    parsed_documents: List[Dict[str, Any]] = []
    errors: List[str] = []

    for idx, pdf_path in enumerate(pdf_files):
        try:
            doc = _extract_text_from_pdf(pdf_path, job_id=job_id, pdf_index=idx)
            parsed_documents.append(doc.to_context_dict())
        except ValueError as exc:
            # Password-protected PDF — record error, continue with others
            errors.append(f"{pdf_path.name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{pdf_path.name}: unexpected error — {exc}")

    # Persist parsed docs in context for downstream stages
    context["parsed_documents"] = parsed_documents

    return {
        "pdf_count": len(pdf_files),
        "parsed_count": len(parsed_documents),
        "errors": errors,
        "total_pages": sum(len(d.get("pages", [])) for d in parsed_documents),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 2 in the given registry with this implementation."""
    registry.remove_stage(2)
    registry.register_stage(
        stage_number=2,
        name="Text Extraction",
        block_id=2,
        estimated_duration=2.0,
        execute_fn=execute,
    )
