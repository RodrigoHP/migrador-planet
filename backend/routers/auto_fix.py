"""Router for POST /api/auto-fix — AI-powered template fix suggestions via Claude Sonnet."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

AUTOFIX_MODEL = "anthropic/claude-sonnet-4-5"
MAX_SUGGESTIONS = 20

AUTOFIX_PROMPT = """You are an expert template engineer reviewing an HTML template for document generation.

Analyze the following template state and identify issues that can be automatically fixed.
Return a JSON array of fix suggestions (maximum {max_suggestions}).

For each suggestion, provide:
- id: unique string (e.g., "fix-001")
- type: one of "spacing", "alignment", "font", "binding", "position", "border-refine", "background-refine", "text-align", "z-order"
- description: clear description of the problem in Portuguese
- element_id: the affected element id (from the document tree)
- current_value: the current problematic value (as string)
- suggested_value: the recommended fix value (as string)
- confidence: a number 0-100 indicating how confident you are in this fix

Focus on:
1. spacing: inconsistent padding, margin, or line-height values
2. alignment: elements not aligned to grid or each other
3. font: inconsistent font-family, font-size, or font-weight
4. binding: missing or broken {{{{binding}}}} expressions in text nodes
5. position: elements with overlapping positions or out-of-bounds coordinates
6. border-refine: drawn_elements (lines/rectangles) in PDF without matching CSS border, or with wrong width/color/style
7. background-refine: filled rectangles in PDF without matching background-color CSS, or with different color
8. text-align: text position in PDF suggests right/center alignment but CSS has text-align:left (tolerance 5px)
9. z-order: overlapping elements without explicit z-index, causing incorrect render order

Template state:
{template_state}

{pdf_context}

Return ONLY a valid JSON array of fix suggestions. No explanation text."""


# ---------------------------------------------------------------------------
# Rule-based detection helpers (Story 14.10 — deterministic, no LLM)
# ---------------------------------------------------------------------------


def _run_rule_based_detection(
    template_state: Dict[str, Any],
    pdf_extraction: Optional[Dict[str, Any]],
) -> List["FixSuggestion"]:
    """Run all rule-based detectors and return suggestions."""
    if not pdf_extraction:
        return []

    suggestions: List[FixSuggestion] = []
    nodes = _flatten_nodes(template_state.get("documentTree", {}))
    counter = 0

    counter = _detect_border_issues(
        pdf_extraction.get("drawn_elements", []),
        nodes,
        suggestions,
        counter,
    )
    counter = _detect_background_issues(
        pdf_extraction.get("filled_rects", []),
        nodes,
        suggestions,
        counter,
    )
    counter = _detect_text_align_issues(
        pdf_extraction.get("text_positions", []),
        nodes,
        suggestions,
        counter,
    )
    _detect_zorder_issues(nodes, suggestions, counter)

    return suggestions


def _flatten_nodes(tree: Any) -> List[Dict[str, Any]]:
    """Flatten document tree into a list of nodes with properties."""
    result: List[Dict[str, Any]] = []
    if not isinstance(tree, dict):
        return result
    if tree.get("id"):
        result.append(tree)
    for child in tree.get("children", []):
        result.extend(_flatten_nodes(child))
    return result


def _detect_border_issues(
    drawn_elements: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    suggestions: List["FixSuggestion"],
    counter: int,
) -> int:
    """Detect border mismatches between PDF drawn elements and CSS borders."""
    for elem in drawn_elements:
        elem_type = elem.get("type", "")
        if elem_type not in ("line", "rect"):
            continue
        bbox = elem.get("bbox", [0, 0, 0, 0])
        color = elem.get("color", "#000000")
        width = elem.get("width", 1)

        # Find nearest node by bbox overlap
        target = _find_overlapping_node(bbox, nodes)
        if not target:
            continue

        props = target.get("properties", {})
        has_border = any(
            props.get(f"border_{side}_width", 0) > 0
            for side in ("top", "right", "bottom", "left")
        )
        if not has_border:
            counter += 1
            suggestions.append(FixSuggestion(
                id=f"rule-border-{counter:03d}",
                type="border-refine",
                description=f"Elemento sem borda CSS, mas PDF contém linha/retângulo de borda ({color}, {width}px)",
                element_id=target.get("id", ""),
                current_value="none",
                suggested_value=f"{width}px solid {color}",
                confidence=85,
            ))
    return counter


def _detect_background_issues(
    filled_rects: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    suggestions: List["FixSuggestion"],
    counter: int,
) -> int:
    """Detect background color mismatches between PDF filled rects and CSS."""
    for rect in filled_rects:
        fill_color = rect.get("fill_color", "")
        if not fill_color:
            continue
        bbox = rect.get("bbox", [0, 0, 0, 0])

        target = _find_overlapping_node(bbox, nodes)
        if not target:
            continue

        props = target.get("properties", {})
        css_bg = props.get("background_color", "")
        if not css_bg or not _colors_match(css_bg, fill_color, tolerance=10):
            counter += 1
            suggestions.append(FixSuggestion(
                id=f"rule-bg-{counter:03d}",
                type="background-refine",
                description=f"Background ausente ou diferente — PDF: {fill_color}, CSS: {css_bg or 'none'}",
                element_id=target.get("id", ""),
                current_value=css_bg or "none",
                suggested_value=fill_color,
                confidence=80,
            ))
    return counter


def _detect_text_align_issues(
    text_positions: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    suggestions: List["FixSuggestion"],
    counter: int,
    tolerance: float = 5.0,
) -> int:
    """Detect text alignment mismatches based on PDF text position vs container."""
    for pos in text_positions:
        element_id = pos.get("element_id", "")
        x = pos.get("x", 0)
        container_width = pos.get("container_width", 0)
        text_width = pos.get("text_width", 0)

        if container_width <= 0:
            continue

        target = next((n for n in nodes if n.get("id") == element_id), None)
        if not target:
            continue

        props = target.get("properties", {})
        css_align = props.get("text_align", "left")

        # Determine actual alignment from PDF position
        x_end = x + text_width
        right_margin = container_width - x_end
        center_offset = abs((x + x_end) / 2 - container_width / 2)

        if right_margin < tolerance and x > tolerance:
            detected = "right"
        elif center_offset < tolerance:
            detected = "center"
        else:
            detected = "left"

        if detected != css_align:
            counter += 1
            suggestions.append(FixSuggestion(
                id=f"rule-align-{counter:03d}",
                type="text-align",
                description=f"Texto alinhado '{detected}' no PDF mas CSS tem '{css_align}'",
                element_id=element_id,
                current_value=css_align,
                suggested_value=detected,
                confidence=75,
            ))
    return counter


def _detect_zorder_issues(
    nodes: List[Dict[str, Any]],
    suggestions: List["FixSuggestion"],
    counter: int,
) -> int:
    """Detect overlapping elements without explicit z-index."""
    positioned = [
        n for n in nodes
        if n.get("properties", {}).get("x") is not None
        and n.get("properties", {}).get("y") is not None
    ]

    for i, a in enumerate(positioned):
        for b in positioned[i + 1:]:
            a_props = a.get("properties", {})
            b_props = b.get("properties", {})

            if a_props.get("zIndex") is not None and b_props.get("zIndex") is not None:
                continue

            if _bboxes_overlap(a_props, b_props):
                counter += 1
                suggestions.append(FixSuggestion(
                    id=f"rule-zorder-{counter:03d}",
                    type="z-order",
                    description=f"Elementos '{a.get('id')}' e '{b.get('id')}' se sobrepõem sem z-index",
                    element_id=a.get("id", ""),
                    current_value="auto",
                    suggested_value=str(i + 1),
                    confidence=70,
                ))
                if b_props.get("zIndex") is None:
                    counter += 1
                    suggestions.append(FixSuggestion(
                        id=f"rule-zorder-{counter:03d}",
                        type="z-order",
                        description=f"Elemento '{b.get('id')}' sobreposto sem z-index",
                        element_id=b.get("id", ""),
                        current_value="auto",
                        suggested_value=str(i + 2),
                        confidence=70,
                    ))
    return counter


# ---------------------------------------------------------------------------
# Geometry / color helpers
# ---------------------------------------------------------------------------


def _find_overlapping_node(
    bbox: List[float], nodes: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Find the node whose position/dimensions best overlap the given bbox."""
    best = None
    best_overlap = 0.0
    bx1, by1, bx2, by2 = (bbox + [0, 0, 0, 0])[:4]

    for node in nodes:
        props = node.get("properties", {})
        nx = props.get("x", 0) or 0
        ny = props.get("y", 0) or 0
        nw = props.get("width", 0) or 0
        nh = props.get("height", 0) or 0
        if nw <= 0 or nh <= 0:
            continue

        ox = max(0, min(nx + nw, bx2) - max(nx, bx1))
        oy = max(0, min(ny + nh, by2) - max(ny, by1))
        overlap = ox * oy
        if overlap > best_overlap:
            best_overlap = overlap
            best = node
    return best


def _bboxes_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Check if two nodes' bounding boxes overlap significantly (>10% of smaller)."""
    ax, ay = a.get("x", 0) or 0, a.get("y", 0) or 0
    aw, ah = a.get("width", 0) or 0, a.get("height", 0) or 0
    bx, by = b.get("x", 0) or 0, b.get("y", 0) or 0
    bw, bh = b.get("width", 0) or 0, b.get("height", 0) or 0

    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return False

    ox = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    oy = max(0, min(ay + ah, by + bh) - max(ay, by))
    overlap = ox * oy
    smaller = min(aw * ah, bw * bh)
    return overlap > 0.1 * smaller


def _colors_match(c1: str, c2: str, tolerance: int = 10) -> bool:
    """Check if two hex colors match within RGB tolerance per channel."""
    try:
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        return abs(r1 - r2) <= tolerance and abs(g1 - g2) <= tolerance and abs(b1 - b2) <= tolerance
    except (ValueError, IndexError):
        return c1.lower() == c2.lower()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AutoFixRequest(BaseModel):
    template_state: Dict[str, Any]
    analysis: Optional[Dict[str, Any]] = None
    pdf_extraction: Optional[Dict[str, Any]] = None


class FixSuggestion(BaseModel):
    id: str
    type: str  # spacing | alignment | font | binding | position
    description: str
    element_id: str
    current_value: str
    suggested_value: str
    confidence: int


class AutoFixResponse(BaseModel):
    suggestions: List[FixSuggestion]
    total: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/auto-fix", response_model=AutoFixResponse)
async def run_auto_fix(body: AutoFixRequest) -> AutoFixResponse:
    """Analyze the template state with Claude Sonnet and return fix suggestions.

    Accepts the serialized templateStore state and optional pipeline analysis.
    Returns up to 20 FixSuggestion objects.
    """
    try:
        from services.openrouter_client import get_client
        client = get_client()
    except ValueError as exc:
        logger.error("OpenRouter client unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable. OPENROUTER_API_KEY not configured.",
        ) from exc

    # Serialize the template state for the prompt (limit size)
    template_state_json = json.dumps(body.template_state, ensure_ascii=False, indent=2)
    # Truncate if very large to avoid token limits
    if len(template_state_json) > 8000:
        template_state_json = template_state_json[:8000] + "\n... (truncated)"

    # Build PDF context section if available
    pdf_context = ""
    if body.pdf_extraction:
        pdf_json = json.dumps(body.pdf_extraction, ensure_ascii=False, indent=2)
        if len(pdf_json) > 4000:
            pdf_json = pdf_json[:4000] + "\n... (truncated)"
        pdf_context = f"PDF extraction data (drawn_elements, filled_rects, text_positions):\n{pdf_json}"

    # Generate rule-based suggestions first (deterministic, no LLM needed)
    rule_suggestions = _run_rule_based_detection(body.template_state, body.pdf_extraction)

    prompt = AUTOFIX_PROMPT.format(
        max_suggestions=MAX_SUGGESTIONS - len(rule_suggestions),
        template_state=template_state_json,
        pdf_context=pdf_context,
    )

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    try:
        from openai import AsyncOpenAI
        response = await client.chat.completions.create(
            model=AUTOFIX_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or "[]"
    except Exception as exc:
        logger.error("Auto-fix AI call failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"AI call failed: {exc!s}",
        ) from exc

    # Parse response
    from services.openrouter_client import strip_markdown_fences

    try:
        parsed = json.loads(strip_markdown_fences(raw_content))
        # Handle both array and object with "suggestions" key
        if isinstance(parsed, list):
            raw_suggestions = parsed
        elif isinstance(parsed, dict):
            raw_suggestions = parsed.get("suggestions", [])
        else:
            raw_suggestions = []
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON response, returning empty suggestions")
        raw_suggestions = []

    # Build and validate LLM suggestions
    llm_suggestions: List[FixSuggestion] = []
    for idx, item in enumerate(raw_suggestions[:MAX_SUGGESTIONS - len(rule_suggestions)]):
        try:
            suggestion = FixSuggestion(
                id=str(item.get("id", f"fix-{idx + 1:03d}")),
                type=str(item.get("type", "spacing")),
                description=str(item.get("description", "Correção sugerida")),
                element_id=str(item.get("element_id", "")),
                current_value=str(item.get("current_value", "")),
                suggested_value=str(item.get("suggested_value", "")),
                confidence=int(item.get("confidence", 80)),
            )
            llm_suggestions.append(suggestion)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping invalid suggestion %d: %s", idx, exc)

    # Merge: rule-based first (deterministic), then LLM
    all_suggestions = rule_suggestions + llm_suggestions
    return AutoFixResponse(suggestions=all_suggestions, total=len(all_suggestions))
