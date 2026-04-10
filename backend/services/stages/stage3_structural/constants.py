"""Stage 3 — Shared constants.

Story 41.3 — extracted from stage3_structural_analysis.py
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Dynamic pattern definitions (used by 3.1 and 3.3)
# ---------------------------------------------------------------------------

_DYNAMIC_PATTERNS: list[tuple[str, str, float]] = [
    (r"\d{2}[/.\-]\d{2}[/.\-]\d{4}", "date", 0.8),
    (r"R\$\s*[\d.,]+", "currency", 0.9),
    (r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "cnpj", 0.95),
    (r"\d{3}\.\d{3}\.\d{3}-\d{2}", "cpf", 0.95),
    (r"\d{5}-?\d{3}", "cep", 0.85),
    (r"\(\d{2}\)\s*\d{4,5}-\d{4}", "phone", 0.9),
    (r"\d+[.,]\d{2}$", "decimal", 0.7),
]

_COMPILED_DYNAMIC_PATTERNS = [(re.compile(p), name, w) for p, name, w in _DYNAMIC_PATTERNS]
