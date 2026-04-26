"""Stage 4 — Shared constants for field mapping sub-modules.

Story 41.3 — extracted from stage4_field_mapping.py
"""

from __future__ import annotations

GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"
AMBIGUITY_THRESHOLD = 0.1
HIGH_CONFIDENCE_THRESHOLD = 0.7
# Dead code: scores from Gemini are bimodal (0.0 = abstained, 0.5-0.9 = match).
# Threshold 0.4 never filters in practice, but kept as a safety floor.
MINIMUM_MATCH_THRESHOLD = 0.4
# RC-H: raised from 0.3 to 0.65 — count_score with weight 0.3 was causing spurious
# matches when section child count happened to equal XSD node child count (e.g.
# "Seção Dados do cliente" [4 fields] → DadosParcelasAVencer [4 children], score=0.55).
# At 0.65, only sections whose names strongly resemble an XSD node will scope to that
# node; all others fall back to flat_paths where the LLM can find the right match.
SECTION_MATCH_MIN_SCORE = 0.65

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

MAPPING RULES:
- Data fields (names, dates, addresses, phone numbers, emails, monetary values, IDs, certificate numbers) \
SHOULD be mapped to semantically compatible XSD fields — use score 0.5-0.9.
- Fields with explicit labels (e.g. "TELEFONE:", "E-MAIL:", "CPF:", "Apólice", "Certificado/") \
are strong mapping candidates even if confidence is partial — use score 0.4-0.7.
- For plausible but uncertain matches, use partial score (0.3-0.5) rather than 0.0.
- Set score 0.0 ONLY for: continuous letter body text, greeting/closing paragraphs, \
generic instructions, and legal boilerplate with no structured data value.
- A labeled field containing a number, date, name, or address is NOT static text.
- `ClienteCpf`: ONLY for Brazilian CPF format values (###.###.###-## or 11-digit numbers). \
Never use for subscription IDs, registration numbers, or other non-CPF identifiers.
- `ValorIOF`: ONLY for IOF tax amounts (small percentage of insurance premium, typically < 5% of premium). \
Never use for reserve balances, contribution amounts, or benefit values.

Pairs:
{pairs_json}

Available XSD fields (scoped to this section):
{xsd_paths}

Return a JSON object with key 'mappings': a list of objects, each with:
- 'pair_index' (int): index of the pair (0-based)
- 'candidates': list of up to 3 objects with 'path' (XSD field, or null if no match) and 'score' (float 0-1)
Return only valid JSON.
"""
