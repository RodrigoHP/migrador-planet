"""Stage 2 — Media Extraction sub-module.

Responsibilities:
  - Image extraction from PDF pages (2.4)
  - Page screenshot generation (2.5)

Story 41.3 — extracted from stage2_deep_extraction.py
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from models.pipeline_context import ImageInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 2.4 — Image Extraction
# ---------------------------------------------------------------------------

# Minimum image dimensions to avoid masks/artifacts
_MIN_IMG_DIMENSION = 10  # pixels


async def _extract_images(
    page: fitz.Page,
    doc: fitz.Document,
    page_index: int,
    pdf_id: str,
    storage: Any,
    job_id: str,
) -> list[ImageInfo]:
    """Extract embedded images from a page, filter masks, validate bbox."""
    image_list = page.get_images(full=True)
    images: list[ImageInfo] = []

    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            img_data = doc.extract_image(xref)
        except Exception:
            continue

        ext = img_data.get("ext", "png")
        img_bytes = img_data.get("image", b"")
        width = img_data.get("width", 0)
        height = img_data.get("height", 0)

        if not img_bytes:
            continue

        # Filter masks (tiny images)
        if width < _MIN_IMG_DIMENSION or height < _MIN_IMG_DIMENSION:
            continue

        # Collect ALL placements of this xref on the page.
        # PDFs reuse the same image xref in multiple positions (e.g. the Bradesco
        # logo appears twice on a boleto: once in "Recibo do Sacado" and once in
        # "Ficha de Compensação"). Breaking after the first rect caused the second
        # placement to be silently dropped — that logo never appeared in the template.
        #
        # Clamp each placement to the page boundary. Some PDFs place images with a
        # transformation matrix that positions them slightly outside the page (bleed
        # area, rounding). A negative y0 produces top:-Xpx in CSS, which gets
        # clipped by .page{overflow:hidden} — logo appears cropped at the top.
        page_w = float(page.rect.width)
        page_h = float(page.rect.height)
        placements: list[list[float]] = []
        try:
            for rect in page.get_image_rects(xref):
                x0 = max(0.0, float(rect.x0))
                y0 = max(0.0, float(rect.y0))
                x1 = min(page_w, float(rect.x1))
                y1 = min(page_h, float(rect.y1))
                placements.append([x0, y0, x1, y1])
        except Exception:
            pass

        # Fallback: zero bbox (will be marked invalid below)
        if not placements:
            placements = [[0.0, 0.0, 0.0, 0.0]]

        # Upload image bytes once; share the data-URI across all placements.
        filename = f"img_{pdf_id}_{page_index}_{img_index}.{ext}"
        try:
            asset_url = await storage.upload_asset(job_id, filename, img_bytes)
        except Exception as exc:
            logger.warning("Failed to upload image %s: %s", filename, exc)
            asset_url = filename  # fallback to filename

        for placement_bbox in placements:
            bbox_valid = not (
                placement_bbox[0] == 0.0
                and placement_bbox[1] == 0.0
                and placement_bbox[2] == 0.0
                and placement_bbox[3] == 0.0
            )
            images.append(
                ImageInfo(
                    path=asset_url,
                    bbox=placement_bbox,
                    width=float(width),
                    height=float(height),
                    # Extra fields stored via extra="allow"
                    bbox_valid=bbox_valid,
                    format=ext,
                )
            )

    return images


# ---------------------------------------------------------------------------
# 2.5 — Screenshot (ONLY representatives)
# ---------------------------------------------------------------------------

_SCREENSHOT_DPI = 150


async def _take_screenshot(
    page: fitz.Page,
    page_index: int,
    pdf_id: str,
    storage: Any,
    job_id: str,
) -> str | None:
    """Render page at 150 DPI, save locally AND upload via storage.

    Always returns a local filesystem path so that Stage 3's
    load_image_as_base64() can open the file with open(path, 'rb'),
    regardless of STORAGE_MODE.  Opção A (Story 15.15).
    """
    try:
        matrix = fitz.Matrix(_SCREENSHOT_DPI / 72, _SCREENSHOT_DPI / 72)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")

        page_key = f"page_{pdf_id}_{page_index}"

        # Save PNG locally so Stage 3 can open it (works for any storage mode)
        local_dir = Path("/tmp/jobs") / job_id / "screenshots"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / f"{page_key}.png"
        local_path.write_bytes(png_bytes)

        # Also upload to remote storage (Supabase or local gateway)
        try:
            await storage.upload_screenshot(job_id, page_key, png_bytes)
        except Exception as upload_exc:
            logger.warning(
                "Storage upload failed for screenshot %s:%d (local copy retained): %s",
                pdf_id,
                page_index,
                upload_exc,
            )

        return str(local_path)
    except Exception as exc:
        logger.warning("Failed to take screenshot for page %s:%d: %s", pdf_id, page_index, exc)
        return None
