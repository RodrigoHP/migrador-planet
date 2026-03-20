"""Stage 23 — Field Matching.

For each TextBlock with semantic_label == 'value', finds the adjacent label block
(same page, similar y, smaller x) and uses Gemini 2.0 Flash via OpenRouter to map
the label→value pair to an XSD field path. When multiple candidates score within
0.1 of each other, the result is flagged as ambiguous.

Fallback: if OPENROUTER_API_KEY is not set, uses difflib string similarity.

Reads:
    context["parsed_documents"]  — List[Dict] (ParsedDocument serialised, with semantic_label)
    context["field_tree"]        — FieldTree.to_dict() or None

Writes:
    context["field_mappings"]    — List[FieldMappingResult] as dicts
    context["ambiguous_fields"]  — List[str] of ambiguous xsd candidate paths

Registers itself as Stage 23 (Block 7).
"""

from __future__ import annotations

import difflib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"
AMBIGUITY_THRESHOLD = 0.1  # if top-2 scores differ less than this → ambiguous
ADJACENT_Y_TOLERANCE = 20.0  # points; blocks within this y-distance are "same row"
ADJACENT_X_MAX_DIFF = 250.0  # label must be to the left of value

# Structural labels that should NOT produce field mappings.
# Any block NOT in this set is a candidate (includes "value", "field", "" etc.)
_STRUCTURAL_LABELS = frozenset({
    "header",
    "footer_text",
    "page_number",
    "title",
    "table_header",
    "table_cell",
    "label",        # static field identifiers — they pair with "value" blocks
    "image",
})


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


def _make_mapping(
    pdf_text: str,
    label_text: str,
    xsd_field_path: str,
    confidence: float,
    is_ambiguous: bool,
    candidates: List[Dict[str, Any]],
    page_number: int,
    pdf_index: int,
    bbox: Optional[Tuple] = None,
) -> Dict[str, Any]:
    # Derive frontend-compatible status
    if is_ambiguous:
        fe_status = "ambiguous"
    elif xsd_field_path:
        fe_status = "mapped"
    else:
        fe_status = "unmapped"

    result: Dict[str, Any] = {
        # Backend keys (used by pipeline_result.py and other stages)
        "pdf_text": pdf_text,
        "label_text": label_text,
        "xsd_field_path": xsd_field_path,
        "confidence": confidence,
        "is_ambiguous": is_ambiguous,
        "candidates": candidates,
        "page_number": page_number,
        "pdf_index": pdf_index,
        # Frontend-compatible aliases (used by mappingStore.loadPipelineFields)
        "name": label_text or pdf_text,
        "path": xsd_field_path,
        "type": "text",
        "status": fe_status,
        "isOptional": False,
    }
    if bbox and len(bbox) >= 2:
        result["bbox"] = list(bbox)  # [x0, y0, x1, y1] in PDF points
    return result


# ---------------------------------------------------------------------------
# Adjacency detection
# ---------------------------------------------------------------------------


def _find_adjacent_label(
    value_block: Dict[str, Any],
    all_blocks: List[Dict[str, Any]],
) -> Optional[str]:
    """Return the text of the nearest label block to the left of value_block."""
    value_bbox = value_block.get("bbox", [0, 0, 0, 0])
    if not value_bbox or len(value_bbox) < 4:
        return None
    vx0, vy0, vx1, vy1 = value_bbox
    vy_mid = (vy0 + vy1) / 2.0

    best_label: Optional[str] = None
    best_x_dist = float("inf")

    for blk in all_blocks:
        if blk is value_block:
            continue
        if blk.get("semantic_label") != "label":
            continue
        if blk.get("page_number") != value_block.get("page_number"):
            continue
        if blk.get("pdf_index") != value_block.get("pdf_index"):
            continue

        blk_bbox = blk.get("bbox", [0, 0, 0, 0])
        if not blk_bbox or len(blk_bbox) < 4:
            continue
        bx0, by0, bx1, by1 = blk_bbox
        by_mid = (by0 + by1) / 2.0

        # Must be vertically aligned (same row)
        if abs(vy_mid - by_mid) > ADJACENT_Y_TOLERANCE:
            continue

        # Label must be to the left of value
        x_dist = vx0 - bx1
        if x_dist < 0 or x_dist > ADJACENT_X_MAX_DIFF:
            continue

        if x_dist < best_x_dist:
            best_x_dist = x_dist
            best_label = blk.get("text", "").strip().rstrip(":")

    return best_label


# ---------------------------------------------------------------------------
# Fuzzy fallback (no API key)
# ---------------------------------------------------------------------------


def _fuzzy_match(
    label_text: str,
    value_text: str,
    flat_paths: List[str],
) -> List[Dict[str, Any]]:
    """Score all XSD paths via difflib similarity against label_text."""
    if not flat_paths:
        return []

    # Use the last component of the path as the comparison target
    def _last(path: str) -> str:
        return path.split(".")[-1]

    query = label_text.lower().replace(" ", "").replace("_", "")
    scored: List[Tuple[float, str]] = []
    for path in flat_paths:
        cand = _last(path).lower().replace("_", "")
        ratio = difflib.SequenceMatcher(None, query, cand).ratio()
        scored.append((ratio, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"path": p, "score": round(s, 4)} for s, p in scored[:5]]


# ---------------------------------------------------------------------------
# LLM matching via OpenRouter
# ---------------------------------------------------------------------------


async def _llm_match(
    label_text: str,
    value_text: str,
    flat_paths: List[str],
    openrouter_client: Any,
) -> List[Dict[str, Any]]:
    """Call Gemini 2.0 Flash to rank XSD field candidates."""
    paths_str = "\n".join(f"- {p}" for p in flat_paths[:80])
    prompt = (
        f"You are an XSD field mapper for document extraction.\n"
        f"Label: '{label_text}'\n"
        f"Value example: '{value_text}'\n"
        f"Available XSD fields:\n{paths_str}\n\n"
        f"Return a JSON object with key 'candidates': a list of up to 5 objects, "
        f"each with 'path' (XSD field path) and 'score' (float 0-1). "
        f"Highest score = best match. Return only valid JSON."
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        from services.openrouter_client import _call_with_retry

        completion = await _call_with_retry(
            openrouter_client,
            messages=messages,
            model=GEMINI_FLASH_MODEL,
            response_format={"type": "json_object"},
        )
        from services.openrouter_client import strip_markdown_fences

        raw = completion.choices[0].message.content or "{}"
        data = json.loads(strip_markdown_fences(raw))
        candidates = data.get("candidates", [])
        # Normalise
        result = []
        for c in candidates:
            if isinstance(c, dict) and "path" in c and "score" in c:
                result.append({"path": str(c["path"]), "score": float(c["score"])})
        return result
    except Exception as exc:
        logger.warning("LLM match failed (%s); using fuzzy fallback.", exc)
        return _fuzzy_match(label_text, value_text, flat_paths)


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 23 executor — Field Matching."""
    emit = context.get("emit_progress")

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    field_tree_dict: Optional[Dict[str, Any]] = context.get("field_tree")
    flat_paths: List[str] = []
    if field_tree_dict:
        flat_paths = field_tree_dict.get("flat_paths", [])

    # Determine whether to use LLM
    api_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_client: Any = context.get("openrouter_client")
    use_llm = bool(api_key or openrouter_client)
    if use_llm and openrouter_client is None:
        try:
            from services.openrouter_client import get_client

            openrouter_client = get_client(api_key=api_key)
        except Exception as exc:
            logger.warning("Cannot create OpenRouter client: %s. Using fuzzy fallback.", exc)
            use_llm = False

    field_mappings: List[Dict[str, Any]] = []
    ambiguous_fields: List[str] = []

    for doc in parsed_documents:
        for page in doc.get("pages", []):
            all_blocks = page.get("text_blocks", [])
            for blk in all_blocks:
                # Accept "value", "field", "" (unlabelled — Stage 19 may have failed)
                # and any future non-structural label.
                if blk.get("semantic_label", "") in _STRUCTURAL_LABELS:
                    continue

                value_text = blk.get("text", "").strip()
                if not value_text:
                    continue

                label_text = _find_adjacent_label(blk, all_blocks) or ""

                if not flat_paths:
                    # No XSD info — store a minimal mapping
                    field_mappings.append(
                        _make_mapping(
                            pdf_text=value_text,
                            label_text=label_text,
                            xsd_field_path="",
                            confidence=0.0,
                            is_ambiguous=False,
                            candidates=[],
                            page_number=blk.get("page_number", 0),
                            pdf_index=blk.get("pdf_index", 0),
                            bbox=blk.get("bbox"),
                        )
                    )
                    continue

                # Get ranked candidates
                if use_llm:
                    candidates = await _llm_match(
                        label_text or value_text,
                        value_text,
                        flat_paths,
                        openrouter_client,
                    )
                else:
                    candidates = _fuzzy_match(
                        label_text or value_text,
                        value_text,
                        flat_paths,
                    )

                if not candidates:
                    field_mappings.append(
                        _make_mapping(
                            pdf_text=value_text,
                            label_text=label_text,
                            xsd_field_path="",
                            confidence=0.0,
                            is_ambiguous=False,
                            candidates=[],
                            page_number=blk.get("page_number", 0),
                            pdf_index=blk.get("pdf_index", 0),
                            bbox=blk.get("bbox"),
                        )
                    )
                    continue

                best = candidates[0]
                is_ambiguous = False
                if len(candidates) >= 2:
                    diff = best["score"] - candidates[1]["score"]
                    if diff < AMBIGUITY_THRESHOLD:
                        is_ambiguous = True
                        ambiguous_fields.append(best["path"])

                field_mappings.append(
                    _make_mapping(
                        pdf_text=value_text,
                        label_text=label_text,
                        xsd_field_path=best["path"],
                        confidence=round(best["score"], 4),
                        is_ambiguous=is_ambiguous,
                        candidates=candidates,
                        page_number=blk.get("page_number", 0),
                        pdf_index=blk.get("pdf_index", 0),
                        bbox=blk.get("bbox"),
                    )
                )

    context["field_mappings"] = field_mappings
    # Preserve existing ambiguous_fields if any (e.g., from prior stages)
    existing = context.get("ambiguous_fields", [])
    context["ambiguous_fields"] = existing + ambiguous_fields

    summary = {
        "total_values_processed": len(field_mappings),
        "ambiguous_count": len(ambiguous_fields),
        "with_label": sum(1 for m in field_mappings if m["label_text"]),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 23,
                    "stage_name": "Field Matching",
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
    """Replace stub Stage 23 with this implementation."""
    registry.remove_stage(23)
    registry.register_stage(
        stage_number=23,
        name="Field Matching",
        block_id=7,
        estimated_duration=1.5,
        execute_fn=execute,
    )
