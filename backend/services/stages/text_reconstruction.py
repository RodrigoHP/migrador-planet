"""Stage 3 — Text Reconstruction.

Merges fragmented text spans (e.g. "Cl"+"iente" → "Cliente") within each
page using proximity on the Y axis (same line), X ordering, and font
similarity checks.

Registers itself in the default_registry as Stage 3 (Block 2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from models.parsed_document import ParsedDocument, ParsedPage, TextBlock

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

Y_THRESHOLD = 3.0   # px — spans within this vertical distance share a line
X_SPACING_FACTOR = 1.2  # merge if gap < avg_char_width * factor


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------


def _avg_char_width(block: TextBlock) -> float:
    """Approximate average character width from the block's bounding box."""
    text_len = max(len(block.text), 1)
    return (block.bbox[2] - block.bbox[0]) / text_len


def _same_font(a: TextBlock, b: TextBlock) -> bool:
    """Return True when two blocks share the same font family (base name)."""
    # Compare only the base font name (ignore style suffixes like -Bold)
    def _base(name: str) -> str:
        return name.split("-")[0].lower()

    return _base(a.font_name) == _base(b.font_name)


def _reconstruct_page_blocks(blocks: List[TextBlock]) -> List[TextBlock]:
    """Merge fragmented spans on a page into coherent TextBlocks."""
    if not blocks:
        return []

    # Sort: primary Y (top of bbox), secondary X (left of bbox)
    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

    # Group into lines by Y proximity
    lines: List[List[TextBlock]] = []
    current_line: List[TextBlock] = [sorted_blocks[0]]

    for block in sorted_blocks[1:]:
        prev = current_line[-1]
        if abs(block.bbox[1] - prev.bbox[1]) <= Y_THRESHOLD:
            current_line.append(block)
        else:
            lines.append(current_line)
            current_line = [block]
    lines.append(current_line)

    merged: List[TextBlock] = []

    for line in lines:
        # Sort line by X
        line.sort(key=lambda b: b.bbox[0])

        if not line:
            continue

        # Merge candidates within the line
        acc = line[0]
        for nxt in line[1:]:
            x_gap = nxt.bbox[0] - acc.bbox[2]  # gap between right of acc and left of nxt
            avg_w = (_avg_char_width(acc) + _avg_char_width(nxt)) / 2
            font_match = _same_font(acc, nxt)

            if font_match and x_gap < avg_w * X_SPACING_FACTOR:
                # Merge: extend bounding box, concatenate text
                space = " " if x_gap > avg_w * 0.3 else ""
                new_text = acc.text + space + nxt.text
                new_bbox = (
                    acc.bbox[0],
                    min(acc.bbox[1], nxt.bbox[1]),
                    nxt.bbox[2],
                    max(acc.bbox[3], nxt.bbox[3]),
                )
                acc = TextBlock(
                    text=new_text,
                    bbox=new_bbox,
                    font_name=acc.font_name,
                    font_size=acc.font_size,
                    page_number=acc.page_number,
                    pdf_index=acc.pdf_index,
                )
            else:
                merged.append(acc)
                acc = nxt

        merged.append(acc)

    return merged


def reconstruct_document(doc_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Reconstruct text blocks for all pages of a serialised ParsedDocument."""
    parsed = ParsedDocument(**doc_dict)
    new_pages: List[ParsedPage] = []

    for page in parsed.pages:
        reconstructed = _reconstruct_page_blocks(page.text_blocks)
        new_pages.append(
            ParsedPage(
                page_number=page.page_number,
                text_blocks=reconstructed,
                images=page.images,
                fonts=page.fonts,
                grid_info=page.grid_info,
                screenshot_path=page.screenshot_path,
            )
        )

    parsed.pages = new_pages
    return parsed.to_context_dict()


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 3 executor — Text Reconstruction."""
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])

    reconstructed: List[Dict[str, Any]] = []
    total_before = 0
    total_after = 0

    for doc_dict in parsed_documents:
        before = sum(len(p.get("text_blocks", [])) for p in doc_dict.get("pages", []))
        rebuilt = reconstruct_document(doc_dict)
        after = sum(len(p.get("text_blocks", [])) for p in rebuilt.get("pages", []))
        total_before += before
        total_after += after
        reconstructed.append(rebuilt)

    # Update context in-place for downstream stages
    context["parsed_documents"] = reconstructed

    return {
        "blocks_before": total_before,
        "blocks_after": total_after,
        "merged": total_before - total_after,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 3 in the given registry with this implementation."""
    registry.remove_stage(3)
    registry.register_stage(
        stage_number=3,
        name="Text Reconstruction",
        block_id=2,
        estimated_duration=1.5,
        execute_fn=execute,
    )
