"""Formatter inference — infers FormatterSpec from field text samples.

Spike C3: validates that ≥70% of dynamic fields can have their formatter
inferred automatically from sample values, reducing manual annotation in the editor.

Approach: regex pattern matching on sample text values extracted by Stage 2.
Handles pt-BR conventions (dd/mm/yyyy, R$ 1.234,56, 99,99%).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from models.ast.nodes import FormatterSpec

# ---------------------------------------------------------------------------
# Compiled regex patterns (ordered by specificity, most specific first)
# ---------------------------------------------------------------------------

# Currency: R$ 1.234,56 | R$1234,56 | 1.234,56 (without R$) not matched here
_RE_CURRENCY = re.compile(
    r"^R\$\s*[\d\.,]+$|^[\d\.]+,\d{2}$",
    re.IGNORECASE,
)

# Date patterns (pt-BR primary, ISO secondary)
_RE_DATE_DDMMYYYY = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_RE_DATE_DDMMYY = re.compile(r"^\d{2}/\d{2}/\d{2}$")
_RE_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_DATE_LONG = re.compile(
    r"^\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$",
    re.IGNORECASE,
)  # "15 de março de 2024"

# Percent: 99,99% | 99.99% | 99%
_RE_PERCENT = re.compile(r"^\d+[,.]?\d*\s*%$")

# Number (integer or decimal, pt-BR separators)
_RE_NUMBER = re.compile(r"^\d{1,3}(\.\d{3})*(,\d+)?$|^\d+(,\d+)?$")

# CPF/CNPJ (structural — treated as raw, no formatting needed)
_RE_CPF = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")
_RE_CNPJ = re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")


def infer_formatter(samples: Sequence[str]) -> FormatterSpec:
    """Infer FormatterSpec from one or more sample text values.

    Majority vote across samples. Falls back to 'raw' when no pattern wins.

    Args:
        samples: List of observed text values for this field across PDF instances.

    Returns:
        FormatterSpec with inferred kind and pattern.
    """
    if not samples:
        return FormatterSpec(kind="raw")

    votes: dict[str, int] = {}
    for s in samples:
        kind = _classify(s.strip())
        votes[kind] = votes.get(kind, 0) + 1

    winner = max(votes, key=lambda k: votes[k])
    return _kind_to_spec(winner, samples)


def infer_formatter_single(text: str) -> FormatterSpec:
    """Infer FormatterSpec from a single text sample."""
    return infer_formatter([text])


def _classify(text: str) -> str:
    """Return kind string for a single text value."""
    if not text:
        return "raw"
    if _RE_PERCENT.match(text):
        return "percent"
    if _RE_CURRENCY.match(text) or (text.startswith("R$")):
        return "currency"
    if (
        _RE_DATE_DDMMYYYY.match(text)
        or _RE_DATE_DDMMYY.match(text)
        or _RE_DATE_ISO.match(text)
        or _RE_DATE_LONG.match(text)
    ):
        return "date"
    if _RE_CPF.match(text) or _RE_CNPJ.match(text):
        return "raw"  # structured IDs kept as-is
    if _RE_NUMBER.match(text) and len(text) > 1:
        return "number"
    return "raw"


def _kind_to_spec(kind: str, samples: Sequence[str]) -> FormatterSpec:
    """Build FormatterSpec for a winning kind, inferring pattern from samples."""
    if kind == "currency":
        # Detect if R$ prefix is present in samples
        has_prefix = any(s.strip().startswith("R$") for s in samples)
        pattern = "R$ #.##0,00" if has_prefix else "#.##0,00"
        return FormatterSpec(kind="currency", pattern=pattern)

    if kind == "date":
        # Detect date format from first matching sample
        for s in samples:
            s = s.strip()
            if _RE_DATE_DDMMYYYY.match(s):
                return FormatterSpec(kind="date", pattern="dd/MM/yyyy")
            if _RE_DATE_DDMMYY.match(s):
                return FormatterSpec(kind="date", pattern="dd/MM/yy")
            if _RE_DATE_ISO.match(s):
                return FormatterSpec(kind="date", pattern="yyyy-MM-dd")
            if _RE_DATE_LONG.match(s):
                return FormatterSpec(kind="date", pattern="d 'de' MMMM 'de' yyyy")
        return FormatterSpec(kind="date", pattern="dd/MM/yyyy")  # pt-BR default

    if kind == "percent":
        return FormatterSpec(kind="percent", pattern="#.##0,00%")

    if kind == "number":
        # Check if samples have decimal places
        has_decimal = any("," in s for s in samples)
        pattern = "#.##0,00" if has_decimal else "#.##0"
        return FormatterSpec(kind="number", pattern=pattern)

    return FormatterSpec(kind="raw")
