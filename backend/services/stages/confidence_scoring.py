"""Stage 25 — Confidence Scoring.

Computes a multi-factor confidence score for the overall field mapping quality.

5 factors (each 0.0–1.0):
    layout_stability   — from context["intelligence"].layout_stability or 0.5 default
    anchor_detection   — % of field_mappings that have a non-empty label_text
    grid_quality       — grid_info.columns > 1 → 0.8, else 0.5
    field_variability  — from context["intelligence"].field_variability or 0.5 default
    vision_agreement   — mean consistency_score from context["visual_analysis"]

If OPENROUTER_API_KEY is set (or context["openrouter_client"] provided), uses Claude
Sonnet to produce an analysed global score. Otherwise computes a weighted average.

Thresholds:
    >= 0.95  → "approved"
    0.80–0.95 → "review_recommended"
    < 0.80   → "human_review_required"

Reads:
    context["field_mappings"]    — List[Dict] from Stage 23/24
    context["parsed_documents"]  — for grid_info
    context["intelligence"]      — optional Dict with layout_stability, field_variability
    context["visual_analysis"]   — optional Dict[page_key, {"consistency_score": float}]

Writes:
    context["confidence_scores"] — Dict with factors + global score + status

Registers itself as Stage 25 (Block 8).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CLAUDE_SONNET_MODEL = "anthropic/claude-sonnet-4-20250514"

WEIGHTS = {
    "layout_stability": 0.25,
    "anchor_detection": 0.25,
    "grid_quality": 0.20,
    "field_variability": 0.15,
    "vision_agreement": 0.15,
}

THRESHOLD_APPROVED = 0.95
THRESHOLD_REVIEW = 0.80


# ---------------------------------------------------------------------------
# Factor extraction helpers
# ---------------------------------------------------------------------------


def _get_layout_stability(context: Dict[str, Any]) -> float:
    intelligence = context.get("intelligence") or {}
    val = intelligence.get("layout_stability")
    if val is not None:
        try:
            return max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            pass
    return 0.5


def _get_anchor_detection(field_mappings: List[Dict[str, Any]]) -> float:
    if not field_mappings:
        return 0.5
    with_label = sum(1 for m in field_mappings if m.get("label_text"))
    return round(with_label / len(field_mappings), 4)


def _get_grid_quality(context: Dict[str, Any]) -> float:
    """Inspect all pages' grid_info; return 0.8 if any page has columns > 1."""
    for doc in context.get("parsed_documents", []):
        for page in doc.get("pages", []):
            gi = page.get("grid_info")
            if gi and gi.get("columns", 1) > 1:
                return 0.8
    return 0.5


def _get_field_variability(context: Dict[str, Any]) -> float:
    intelligence = context.get("intelligence") or {}
    val = intelligence.get("field_variability")
    if val is not None:
        try:
            return max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            pass
    return 0.5


def _get_vision_agreement(context: Dict[str, Any]) -> float:
    visual_analysis: Dict[str, Any] = context.get("visual_analysis") or {}
    if not visual_analysis:
        return 0.5
    scores = []
    for page_data in visual_analysis.values():
        if isinstance(page_data, dict):
            cs = page_data.get("consistency_score")
            if cs is not None:
                try:
                    scores.append(max(0.0, min(1.0, float(cs))))
                except (TypeError, ValueError):
                    pass
    if not scores:
        return 0.5
    return round(sum(scores) / len(scores), 4)


def _weighted_average(factors: Dict[str, float]) -> float:
    total = sum(WEIGHTS[k] * factors[k] for k in WEIGHTS)
    return round(total, 4)


def _status_from_score(score: float) -> str:
    if score >= THRESHOLD_APPROVED:
        return "approved"
    if score >= THRESHOLD_REVIEW:
        return "review_recommended"
    return "human_review_required"


# ---------------------------------------------------------------------------
# LLM confidence analysis
# ---------------------------------------------------------------------------


async def _llm_confidence(
    factors: Dict[str, float],
    local_score: float,
    openrouter_client: Any,
) -> float:
    """Ask Claude Sonnet for a nuanced global score given the 5 factors."""
    prompt = (
        "You are a document field-mapping quality evaluator.\n"
        "Given the following 5 quality factors (each 0.0-1.0), return a single JSON object "
        "with key 'global_score' (float 0-1) representing overall mapping confidence.\n"
        "Consider that low anchor_detection usually implies high uncertainty.\n\n"
        f"Factors: {json.dumps(factors)}\n"
        f"Preliminary weighted average: {local_score}\n\n"
        "Return only valid JSON, e.g. {\"global_score\": 0.87}"
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        from services.openrouter_client import _call_with_retry

        completion = await _call_with_retry(
            openrouter_client,
            messages=messages,
            model=CLAUDE_SONNET_MODEL,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or "{}"
        data = json.loads(raw)
        score = float(data.get("global_score", local_score))
        return max(0.0, min(1.0, score))
    except Exception as exc:
        logger.warning("LLM confidence scoring failed (%s); using local average.", exc)
        return local_score


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 25 executor — Confidence Scoring."""
    emit = context.get("emit_progress")

    field_mappings: List[Dict[str, Any]] = context.get("field_mappings", [])

    factors: Dict[str, float] = {
        "layout_stability": _get_layout_stability(context),
        "anchor_detection": _get_anchor_detection(field_mappings),
        "grid_quality": _get_grid_quality(context),
        "field_variability": _get_field_variability(context),
        "vision_agreement": _get_vision_agreement(context),
    }

    local_score = _weighted_average(factors)

    # Optionally use LLM
    api_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_client: Any = context.get("openrouter_client")
    use_llm = bool(api_key or openrouter_client)

    if use_llm and openrouter_client is None:
        try:
            from services.openrouter_client import get_client

            openrouter_client = get_client(api_key=api_key)
        except Exception as exc:
            logger.warning("Cannot create OpenRouter client: %s. Using local score.", exc)
            use_llm = False

    if use_llm:
        global_score = await _llm_confidence(factors, local_score, openrouter_client)
        score_method = "llm"
    else:
        global_score = local_score
        score_method = "weighted_average"

    status = _status_from_score(global_score)

    confidence_scores: Dict[str, Any] = {
        "factors": factors,
        "global_score": global_score,
        "local_weighted_average": local_score,
        "score_method": score_method,
        "status": status,
        "thresholds": {
            "approved": THRESHOLD_APPROVED,
            "review_recommended": THRESHOLD_REVIEW,
        },
    }

    context["confidence_scores"] = confidence_scores

    summary = {
        "global_score": global_score,
        "status": status,
        "factors": factors,
        "score_method": score_method,
    }

    if emit:
        try:
            emit(
                {
                    "stage": 25,
                    "stage_name": "Confidence Scoring",
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
    """Replace stub Stage 25 with this implementation."""
    registry.remove_stage(25)
    registry.register_stage(
        stage_number=25,
        name="Confidence Scoring",
        block_id=8,
        estimated_duration=1.0,
        execute_fn=execute,
    )
