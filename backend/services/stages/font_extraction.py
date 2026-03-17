"""Stage 4 — Font Extraction → CSS.

Derives CSSFont objects from the font metadata present in TextBlocks,
applying the canonical FONT_MAP normalisation table.

Registers itself in the default_registry as Stage 4 (Block 2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from models.parsed_document import CSSFont, ParsedDocument, ParsedPage

# ---------------------------------------------------------------------------
# Normalisation map  (PDF font name → CSS font-family)
# ---------------------------------------------------------------------------

FONT_MAP: Dict[str, str] = {
    "Helvetica": "Arial",
    "Helvetica-Bold": "Arial",
    "Helvetica-Oblique": "Arial",
    "Helvetica-BoldOblique": "Arial",
    "Times-Roman": "Times New Roman",
    "Times-Bold": "Times New Roman",
    "Times-Italic": "Times New Roman",
    "Times-BoldItalic": "Times New Roman",
    "Courier": "Courier New",
    "Courier-Bold": "Courier New",
    "Courier-Oblique": "Courier New",
    "Courier-BoldOblique": "Courier New",
    "Symbol": "Symbol",
    "ZapfDingbats": "ZapfDingbats",
}


def _is_bold(font_name: str) -> bool:
    lower = font_name.lower()
    return "bold" in lower or "-bd" in lower or ",bold" in lower


def _is_italic(font_name: str) -> bool:
    lower = font_name.lower()
    return "italic" in lower or "oblique" in lower or "-it" in lower


def normalise_font(font_name: str, font_size: float) -> CSSFont:
    """Convert a raw PDF font name + size into a CSSFont."""
    # Direct lookup first
    css_family = FONT_MAP.get(font_name)

    if css_family is None:
        # Partial match: check prefix (e.g. "ABCDEF+Helvetica-Bold")
        stripped = font_name.split("+")[-1]  # remove embedded subset prefix
        css_family = FONT_MAP.get(stripped)

        if css_family is None:
            # Fallback: use the stripped name as-is (preserve document intent)
            css_family = stripped or font_name

    weight = "bold" if _is_bold(font_name) else "normal"
    style = "italic" if _is_italic(font_name) else "normal"

    return CSSFont(
        font_family=css_family,
        font_size=round(font_size, 2),
        font_weight=weight,
        font_style=style,
    )


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 4 executor — Font Extraction → CSS."""
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])

    updated_docs: List[Dict[str, Any]] = []
    unique_fonts: Set[str] = set()

    for doc_dict in parsed_documents:
        parsed = ParsedDocument(**doc_dict)
        new_pages: List[ParsedPage] = []

        for page in parsed.pages:
            seen_on_page: Dict[str, CSSFont] = {}

            for block in page.text_blocks:
                key = f"{block.font_name}|{block.font_size}"
                if key not in seen_on_page:
                    css_font = normalise_font(block.font_name, block.font_size)
                    seen_on_page[key] = css_font
                    unique_fonts.add(css_font.font_family)

            new_pages.append(
                ParsedPage(
                    page_number=page.page_number,
                    text_blocks=page.text_blocks,
                    images=page.images,
                    fonts=list(seen_on_page.values()),
                    grid_info=page.grid_info,
                    screenshot_path=page.screenshot_path,
                )
            )

        parsed.pages = new_pages
        updated_docs.append(parsed.to_context_dict())

    context["parsed_documents"] = updated_docs

    return {
        "unique_css_families": sorted(unique_fonts),
        "total_font_entries": sum(
            sum(len(p.get("fonts", [])) for p in d.get("pages", []))
            for d in updated_docs
        ),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 4 in the given registry with this implementation."""
    registry.remove_stage(4)
    registry.register_stage(
        stage_number=4,
        name="Font Extraction → CSS",
        block_id=2,
        estimated_duration=1.0,
        execute_fn=execute,
    )
