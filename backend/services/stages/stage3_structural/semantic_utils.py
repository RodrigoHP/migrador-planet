"""Stage 3 — Semantic Name & XSD Binding Utilities.

Responsibilities:
  - Text normalization for comparison
  - Levenshtein similarity via SequenceMatcher
  - XSD binding suggestion by fuzzy name match
  - Semantic name extraction from text blocks
  - Section name inference from label blocks
  - Section/block variant resolution

Story 41.3 — split from section_utils.py to keep files under 500 LOC.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Story 34.7 — Normalize text: lowercase, remove accents, remove punctuation."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = "".join(c for c in stripped if c.isalnum() or c == " ")
    return cleaned.strip()


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Story 34.7 — Compute similarity ratio (0.0-1.0) using stdlib SequenceMatcher."""
    from difflib import SequenceMatcher

    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1, s2).ratio()


def _suggest_xsd_binding(
    node_name: str,
    flat_paths: list[str],
    threshold: float = 0.7,
) -> str | None:
    """Story 34.7 — Find best XSD path match for a semantic name."""
    if not node_name or not flat_paths:
        return None

    norm_name = _normalize_text(node_name)
    if not norm_name:
        return None

    best_path: str | None = None
    best_score = 0.0

    for path in flat_paths:
        segments = path.split(".")
        leaf = _normalize_text(segments[-1]) if segments else ""
        if not leaf:
            continue

        score = _levenshtein_similarity(norm_name, leaf)
        if score > best_score:
            best_score = score
            best_path = path

        full_norm = _normalize_text(path.replace(".", " "))
        full_score = _levenshtein_similarity(norm_name, full_norm)
        if full_score > best_score:
            best_score = full_score
            best_path = path

    if best_score >= threshold and best_path:
        return best_path
    return None


def _apply_suggested_bindings(
    tree: dict[str, Any],
    flat_paths: list[str],
) -> int:
    """Story 34.7 — Walk tree and add suggested_binding to nodes with semantic names."""
    count = 0

    def _walk(node: dict[str, Any]):
        nonlocal count
        name = node.get("name", "")
        if name and node.get("type") in ("field", "value", "likely_dynamic", "dynamic"):
            suggestion = _suggest_xsd_binding(name, flat_paths)
            if suggestion:
                node["suggested_binding"] = suggestion
                count += 1
        for child in node.get("children", []):
            _walk(child)

    _walk(tree)
    return count


def _extract_semantic_name(block: dict[str, Any]) -> str:
    """Extract human-readable name from a block's text content.

    Story 29.4 — AC1/AC2: Returns cleaned text suitable for use as node.name.
    """
    text = block.get("text", "").strip()
    if not text:
        return ""
    cleaned = text.rstrip(":;").strip()
    return cleaned[:50]


def _infer_section_name(
    section_blocks: list[dict[str, Any]],
    block_classifications: dict[str, dict[str, Any]],
) -> str:
    """Infer a descriptive name for a section based on its first label child.

    Story 29.4 — AC3.
    """
    for block in section_blocks:
        bid = block.get("id", "")
        bc = block_classifications.get(bid, {})
        if bc.get("semantic") == "label":
            label_text = _extract_semantic_name(block)
            if label_text:
                return f"Seção {label_text}"
    return ""


def _section_variant(
    blocks: list[dict[str, Any]],
    block_classifications: dict[str, dict[str, Any]],
) -> str:
    """Determine section variant from child block variants."""
    variants = [block_classifications.get(b.get("id", ""), {}).get("variant", "required") for b in blocks]
    if not variants:
        return "required"
    if all(v == "conditional" for v in variants):
        return "conditional"
    elif any(v in ("optional", "conditional") for v in variants):
        return "optional"
    return "required"


def _get_conditional_pdfs(
    blocks: list[dict[str, Any]],
    block_classifications: dict[str, dict[str, Any]],
) -> list[str]:
    """Get sorted list of pdf_ids where conditional blocks are present."""
    pdf_ids: set[str] = set()
    for b in blocks:
        bc = block_classifications.get(b.get("id", ""), {})
        if bc.get("variant") == "conditional" and bc.get("present_in_pdfs"):
            pdf_ids.update(bc["present_in_pdfs"])
    return sorted(pdf_ids)
