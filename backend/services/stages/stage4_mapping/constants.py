"""Stage 4 — Shared constants for field mapping sub-modules.

Story 41.3 — extracted from stage4_field_mapping.py
"""

from __future__ import annotations

GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"
AMBIGUITY_THRESHOLD = 0.1
HIGH_CONFIDENCE_THRESHOLD = 0.7
MINIMUM_MATCH_THRESHOLD = 0.4
SECTION_MATCH_MIN_SCORE = 0.3

WEIGHTS = {
    "layout_stability": 0.25,
    "anchor_detection": 0.15,
    "grid_quality": 0.20,
    "field_variability": 0.25,
    "vision_agreement": 0.15,
}

THRESHOLD_APPROVED = 0.95
THRESHOLD_REVIEW = 0.80

_TYPE_FORMAT_COMPAT: dict[str, set] = {
    "date": {"date_numeric", "date_extenso"},
    "decimal": {"currency_brl", "percentage"},
    "integer": {"percentage"},
    "string": {"cpf", "cnpj", "phone", "currency_brl", "date_numeric", "date_extenso", "percentage", "cep", "email"},
    "boolean": set(),
}

_BATCH_MATCH_PROMPT = """\
You are an XSD field mapper for document extraction.

Below are label-value pairs extracted from a document section.
{section_context}

Map each pair to the best matching XSD field path from the candidates below.

IMPORTANT RULES:
- Only map a pair when you are confident there is a semantically meaningful match.
- If no XSD field is a good match for a pair, set score to 0.0 and path to null for that pair.
- Do NOT invent or force a mapping when none exists — unmapped is better than wrong.
- Static header/footer text, instructions, or body paragraphs should receive score 0.0.

Pairs:
{pairs_json}

Available XSD fields (scoped to this section):
{xsd_paths}

Return a JSON object with key 'mappings': a list of objects, each with:
- 'pair_index' (int): index of the pair (0-based)
- 'candidates': list of up to 3 objects with 'path' (XSD field, or null if no match) and 'score' (float 0-1)
Return only valid JSON.
"""
