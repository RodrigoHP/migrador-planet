"""Font identification router — uses OpenRouter to suggest Google Font alternatives."""

import os
import json

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-3-haiku"


class FontIdentifyRequest(BaseModel):
    font_name: str


class FontSuggestion(BaseModel):
    name: str
    similarity: float
    source: str


class FontIdentifyResponse(BaseModel):
    original: str
    suggestions: list[FontSuggestion]


@router.post("/font-identify", response_model=FontIdentifyResponse)
async def identify_font(request: FontIdentifyRequest) -> FontIdentifyResponse:
    """
    Receive a font name and return suggestions for public alternatives.
    Uses OpenRouter (Claude or GPT-4o) to identify the closest Google Font or
    system font alternative.
    """
    font_name = request.font_name.strip()

    if not font_name:
        return FontIdentifyResponse(original=font_name, suggestions=[])

    suggestions = await _get_ai_suggestions(font_name)
    return FontIdentifyResponse(original=font_name, suggestions=suggestions)


async def _get_ai_suggestions(font_name: str) -> list[FontSuggestion]:
    """Call OpenRouter to get font alternative suggestions."""
    if not OPENROUTER_API_KEY:
        return _fallback_suggestions(font_name)

    prompt = (
        f"You are a typography expert. The user has a document that uses the font '{font_name}', "
        f"which is not available. Suggest up to 3 public alternatives (Google Fonts or common "
        f"system fonts) that closely match '{font_name}' in style and metrics. "
        f"Respond ONLY with valid JSON in this exact format: "
        f'[{{"name": "FontName", "similarity": 0.95, "source": "Google Fonts"}}, ...]'
        f"No explanation, no markdown, just the JSON array."
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            from services.openrouter_client import strip_markdown_fences

            content = data["choices"][0]["message"]["content"]
            raw = json.loads(strip_markdown_fences(content))
            return [
                FontSuggestion(
                    name=item.get("name", "Unknown"),
                    similarity=float(item.get("similarity", 0.5)),
                    source=item.get("source", "Unknown"),
                )
                for item in raw
                if isinstance(item, dict)
            ]
    except Exception:
        return _fallback_suggestions(font_name)


def _fallback_suggestions(font_name: str) -> list[FontSuggestion]:
    """Provide rule-based fallback suggestions when AI is unavailable."""
    name_lower = font_name.lower()

    # Serif fonts
    if any(k in name_lower for k in ["garamond", "palatino", "georgia", "times", "book antiqua"]):
        return [
            FontSuggestion(name="Georgia", similarity=0.85, source="System"),
            FontSuggestion(name="Merriweather", similarity=0.80, source="Google Fonts"),
            FontSuggestion(name="Lora", similarity=0.75, source="Google Fonts"),
        ]

    # Monospace fonts
    if any(k in name_lower for k in ["courier", "mono", "consolas", "menlo", "inconsolata"]):
        return [
            FontSuggestion(name="Courier New", similarity=0.90, source="System"),
            FontSuggestion(name="Roboto Mono", similarity=0.80, source="Google Fonts"),
            FontSuggestion(name="Source Code Pro", similarity=0.75, source="Google Fonts"),
        ]

    # Default: sans-serif alternatives
    return [
        FontSuggestion(name="Arial", similarity=0.80, source="System"),
        FontSuggestion(name="Roboto", similarity=0.75, source="Google Fonts"),
        FontSuggestion(name="Open Sans", similarity=0.70, source="Google Fonts"),
    ]
