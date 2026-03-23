"""Stage 5 — Image Extraction.

Extracts embedded images from each PDF page and uploads them via
StorageGateway.

Story 13.2: Uses StorageGateway (injected via context["_storage"]) instead
of writing directly to /tmp.  Falls back to local disk when no gateway is
present (backward compat during migration).

Registers itself in the default_registry as Stage 5 (Block 2).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from models.parsed_document import ParsedDocument, ParsedImage, ParsedPage


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _extract_images_from_pdf(
    pdf_path: Path,
    job_id: str,
    pdf_index: int,
    assets_dir: Path,
) -> Dict[int, List[ParsedImage]]:
    """Extract all embedded images from a PDF; returns mapping page->images.

    Legacy sync API — writes directly to disk.  Kept for backward compat.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF (fitz) is required. Install it with: pip install PyMuPDF"
        ) from exc

    assets_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))

    page_images: Dict[int, List[ParsedImage]] = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = doc.get_page_images(page_num, full=True)  # type: ignore[attr-defined]
        images: List[ParsedImage] = []

        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                img_data = doc.extract_image(xref)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                continue

            ext = img_data.get("ext", "png")
            img_bytes = img_data.get("image", b"")
            if not img_bytes:
                continue

            filename = f"img_{pdf_index}_{page_num}_{img_index}.{ext}"
            file_path = assets_dir / filename
            file_path.write_bytes(img_bytes)

            # Try to get the image placement bbox from the page
            bbox = (0.0, 0.0, 0.0, 0.0)
            try:
                for item in page.get_image_rects(xref):  # type: ignore[attr-defined]
                    rect = item
                    bbox = (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
                    break
            except Exception:  # noqa: BLE001
                pass

            images.append(
                ParsedImage(
                    path=str(file_path),
                    format=ext,
                    bbox=bbox,
                    page_number=page_num,
                    pdf_index=pdf_index,
                )
            )

        if images:
            page_images[page_num] = images

    doc.close()
    return page_images


async def _extract_images_via_storage(
    pdf_path: Path,
    job_id: str,
    pdf_index: int,
    storage: Any,
) -> Dict[int, List[ParsedImage]]:
    """Extract images from PDF and upload via StorageGateway; return page->images."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF (fitz) is required. Install it with: pip install PyMuPDF"
        ) from exc

    doc = fitz.open(str(pdf_path))
    page_images: Dict[int, List[ParsedImage]] = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = doc.get_page_images(page_num, full=True)  # type: ignore[attr-defined]
        images: List[ParsedImage] = []

        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                img_data = doc.extract_image(xref)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                continue

            ext = img_data.get("ext", "png")
            img_bytes = img_data.get("image", b"")
            if not img_bytes:
                continue

            filename = f"img_{pdf_index}_{page_num}_{img_index}.{ext}"

            # Upload via storage gateway — returns URL or local path
            asset_url = await storage.upload_asset(job_id, filename, img_bytes)

            # Try to get the image placement bbox from the page
            bbox = (0.0, 0.0, 0.0, 0.0)
            try:
                for item in page.get_image_rects(xref):  # type: ignore[attr-defined]
                    rect = item
                    bbox = (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
                    break
            except Exception:  # noqa: BLE001
                pass

            images.append(
                ParsedImage(
                    path=asset_url,
                    format=ext,
                    bbox=bbox,
                    page_number=page_num,
                    pdf_index=pdf_index,
                )
            )

        if images:
            page_images[page_num] = images

    doc.close()
    return page_images


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 5 executor — Image Extraction."""
    job_id: str = context.get("job_id", "")
    tmp_base = Path(context.get("tmp_base", "/tmp/jobs"))
    job_dir = tmp_base / job_id
    storage = context.get("_storage")

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    pdf_files: List[Path] = sorted(job_dir.glob("*.pdf"))

    total_images = 0
    updated_docs: List[Dict[str, Any]] = []

    for doc_dict in parsed_documents:
        pdf_index = doc_dict.get("pdf_index", 0)
        pdf_name = doc_dict.get("pdf_name", "")

        pdf_path = job_dir / pdf_name
        if not pdf_path.exists():
            # Try finding by index
            if pdf_index < len(pdf_files):
                pdf_path = pdf_files[pdf_index]
            else:
                updated_docs.append(doc_dict)
                continue

        try:
            if storage is not None:
                page_images = await _extract_images_via_storage(
                    pdf_path=pdf_path,
                    job_id=job_id,
                    pdf_index=pdf_index,
                    storage=storage,
                )
            else:
                # Legacy fallback
                assets_dir = Path("/tmp") / job_id / "assets"
                page_images = _extract_images_from_pdf(
                    pdf_path=pdf_path,
                    job_id=job_id,
                    pdf_index=pdf_index,
                    assets_dir=assets_dir,
                )
        except Exception:  # noqa: BLE001
            updated_docs.append(doc_dict)
            continue

        parsed = ParsedDocument(**doc_dict)
        new_pages: List[ParsedPage] = []

        for page in parsed.pages:
            imgs = page_images.get(page.page_number, [])
            total_images += len(imgs)
            new_pages.append(
                ParsedPage(
                    page_number=page.page_number,
                    text_blocks=page.text_blocks,
                    images=imgs,
                    fonts=page.fonts,
                    grid_info=page.grid_info,
                    screenshot_path=page.screenshot_path,
                )
            )

        parsed.pages = new_pages
        updated_docs.append(parsed.to_context_dict())

    context["parsed_documents"] = updated_docs

    return {
        "total_images_extracted": total_images,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 5 in the given registry with this implementation."""
    registry.remove_stage(5)
    registry.register_stage(
        stage_number=5,
        name="Image Extraction",
        block_id=2,
        estimated_duration=2.0,
        execute_fn=execute,
    )
