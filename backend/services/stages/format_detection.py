"""Stage 24 — Format Detection.

Detects data formats in PDF text blocks via regex and generates JavaScript
formatting functions. No LLM is used — pure regex heuristics.

Supported formats:
    currency_brl  — "R$ 1.234,56", "R$1234,56"
    date_numeric  — "01/02/2025"
    date_extenso  — "15 de Janeiro de 2025"
    cpf           — "123.456.789-01"
    cnpj          — "12.345.678/0001-99"
    phone         — "(11) 98765-4321", "(11) 3456-7890"
    percentage    — "12,5%", "100%"

Reads:
    context["field_mappings"]   — List[Dict] from Stage 23 (enriches in place)

Writes:
    context["format_functions"] — Dict[format_name, js_function_string]
    context["field_mappings"]   — updated with "detected_format" key

Registers itself as Stage 24 (Block 7).
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("currency_brl", re.compile(r"^R\$\s?[\d.,]+$")),
    ("date_numeric", re.compile(r"^\d{2}/\d{2}/\d{4}$")),
    (
        "date_extenso",
        re.compile(
            r"^\d{1,2}\s+de\s+"
            r"(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
            r"\s+de\s+\d{4}$",
            re.IGNORECASE,
        ),
    ),
    ("cpf", re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")),
    ("cnpj", re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")),
    ("phone", re.compile(r"^\(\d{2}\)\s?\d{4,5}-\d{4}$")),
    ("percentage", re.compile(r"^[\d.,]+\s?%$")),
]

# ---------------------------------------------------------------------------
# JavaScript function templates
# ---------------------------------------------------------------------------

_JS_FUNCTIONS: dict[str, str] = {
    "currency_brl": (
        "function formatCurrency(v) { "
        "var n = parseFloat(String(v).replace(/R\\$\\s?/, '').replace(/\\./g, '').replace(',', '.')); "
        "return 'R$ ' + n.toFixed(2).replace('.', ',').replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.'); "
        "}"
    ),
    "date_numeric": (
        "function formatDate(v) { "
        "var p = String(v).split('/'); "
        "if (p.length === 3) return p[0] + '/' + p[1] + '/' + p[2]; "
        "return v; "
        "}"
    ),
    "date_extenso": (
        "function formatDateExtenso(v) { "
        "var months = {janeiro:'01',fevereiro:'02','março':'03',abril:'04',maio:'05',junho:'06',"
        "julho:'07',agosto:'08',setembro:'09',outubro:'10',novembro:'11',dezembro:'12'}; "
        "var m = String(v).toLowerCase().match(/(\\d{1,2})\\s+de\\s+(\\w+)\\s+de\\s+(\\d{4})/); "
        "if (m) return ('0'+m[1]).slice(-2) + '/' + (months[m[2]]||'??') + '/' + m[3]; "
        "return v; "
        "}"
    ),
    "cpf": (
        "function formatCPF(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "return d.replace(/(\\d{3})(\\d{3})(\\d{3})(\\d{2})/, '$1.$2.$3-$4'); "
        "}"
    ),
    "cnpj": (
        "function formatCNPJ(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "return d.replace(/(\\d{2})(\\d{3})(\\d{3})(\\d{4})(\\d{2})/, '$1.$2.$3/$4-$5'); "
        "}"
    ),
    "phone": (
        "function formatPhone(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "if (d.length === 11) return '(' + d.slice(0,2) + ') ' + d.slice(2,7) + '-' + d.slice(7); "
        "if (d.length === 10) return '(' + d.slice(0,2) + ') ' + d.slice(2,6) + '-' + d.slice(6); "
        "return v; "
        "}"
    ),
    "percentage": ("function formatPercent(v) { return String(v).trim().replace(/\\s?%$/, '') + '%'; }"),
}


# ---------------------------------------------------------------------------
# Detection helper
# ---------------------------------------------------------------------------


def detect_format(text: str) -> str | None:
    """Return the format name for *text*, or None if unrecognised."""
    cleaned = text.strip()
    for name, pattern in _PATTERNS:
        if pattern.match(cleaned):
            return name
    return None


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: dict[str, Any]) -> dict[str, Any]:
    """Stage 24 executor — Format Detection."""
    emit = context.get("emit_progress")

    field_mappings: list[dict[str, Any]] = context.get("field_mappings", [])

    detected_format_names: set[str] = set()
    formats_detected = 0

    for mapping in field_mappings:
        pdf_text = mapping.get("pdf_text", "").strip()
        fmt = detect_format(pdf_text)
        mapping["detected_format"] = fmt
        if fmt:
            detected_format_names.add(fmt)
            formats_detected += 1

    # Build format_functions dict — only include functions for actually detected formats
    format_functions: dict[str, str] = {}
    for fmt_name in detected_format_names:
        if fmt_name in _JS_FUNCTIONS:
            format_functions[fmt_name] = _JS_FUNCTIONS[fmt_name]

    context["format_functions"] = format_functions
    context["field_mappings"] = field_mappings

    summary = {
        "formats_detected": formats_detected,
        "format_types": sorted(detected_format_names),
        "js_functions_generated": len(format_functions),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 24,
                    "stage_name": "Format Detection",
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


def register(registry: Any) -> None:
    """Replace stub Stage 24 with this implementation."""
    registry.remove_stage(24)
    registry.register_stage(
        stage_number=24,
        name="Format Detection",
        block_id=7,
        estimated_duration=1.0,
        execute_fn=execute,
    )
