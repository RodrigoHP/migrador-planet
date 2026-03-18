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
- type: one of "spacing", "alignment", "font", "binding", "position"
- description: clear description of the problem in Portuguese
- element_id: the affected element id (from the document tree)
- current_value: the current problematic value (as string)
- suggested_value: the recommended fix value (as string)
- confidence: a number 0-100 indicating how confident you are in this fix

Focus on:
1. spacing: inconsistent padding, margin, or line-height values
2. alignment: elements not aligned to grid or each other
3. font: inconsistent font-family, font-size, or font-weight
4. binding: missing or broken {{binding}} expressions in text nodes
5. position: elements with overlapping positions or out-of-bounds coordinates

Template state:
{template_state}

Return ONLY a valid JSON array of fix suggestions. No explanation text."""


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AutoFixRequest(BaseModel):
    template_state: Dict[str, Any]
    analysis: Optional[Dict[str, Any]] = None


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

    prompt = AUTOFIX_PROMPT.format(
        max_suggestions=MAX_SUGGESTIONS,
        template_state=template_state_json,
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
    try:
        parsed = json.loads(raw_content)
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

    # Build and validate suggestions
    suggestions: List[FixSuggestion] = []
    for idx, item in enumerate(raw_suggestions[:MAX_SUGGESTIONS]):
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
            suggestions.append(suggestion)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping invalid suggestion %d: %s", idx, exc)

    return AutoFixResponse(suggestions=suggestions, total=len(suggestions))
