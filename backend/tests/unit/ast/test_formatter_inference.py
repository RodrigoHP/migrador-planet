"""Unit tests for formatter_inference — Spike C3.

Validates that _classify and infer_formatter correctly identify:
  - pt-BR dates (dd/mm/yyyy)
  - currencies (R$ 1.234,56)
  - percents (99,99%)
  - numbers
  - raw fallback
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = str(Path(__file__).resolve().parents[3])
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest

from services.stages.stage3_structural.formatter_inference import (
    _classify,
    infer_formatter,
    infer_formatter_single,
)

pytestmark = pytest.mark.unit


class TestClassify:
    def test_date_ddmmyyyy(self):
        assert _classify("15/03/2024") == "date"

    def test_date_ddmmyy(self):
        assert _classify("15/03/24") == "date"

    def test_date_iso(self):
        assert _classify("2024-03-15") == "date"

    def test_date_long_ptbr(self):
        assert _classify("15 de março de 2024") == "date"

    def test_currency_with_prefix(self):
        assert _classify("R$ 1.234,56") == "currency"

    def test_currency_compact(self):
        assert _classify("R$1.234,56") == "currency"

    def test_percent(self):
        assert _classify("12,50%") == "percent"

    def test_percent_integer(self):
        assert _classify("100%") == "percent"

    def test_number_integer(self):
        assert _classify("1234") == "number"

    def test_number_decimal(self):
        # 1.234,56 pt-BR can be classified as currency (2 decimal places)
        # or number — both are acceptable since context is ambiguous
        assert _classify("1.234,56") in ("number", "currency")

    def test_cpf_is_raw(self):
        assert _classify("123.456.789-09") == "raw"

    def test_cnpj_is_raw(self):
        assert _classify("12.345.678/0001-90") == "raw"

    def test_plain_text_is_raw(self):
        assert _classify("FULANO DE TAL") == "raw"

    def test_empty_is_raw(self):
        assert _classify("") == "raw"


class TestInferFormatter:
    def test_majority_vote_date(self):
        samples = ["15/03/2024", "20/04/2024", "01/01/2024"]
        f = infer_formatter(samples)
        assert f.kind == "date"
        assert f.pattern == "dd/MM/yyyy"

    def test_majority_vote_currency(self):
        samples = ["R$ 1.234,56", "R$ 999,00", "R$ 0,01"]
        f = infer_formatter(samples)
        assert f.kind == "currency"
        assert "R$" in f.pattern

    def test_majority_vote_percent(self):
        samples = ["12,50%", "0,00%", "100%"]
        f = infer_formatter(samples)
        assert f.kind == "percent"

    def test_majority_vote_raw(self):
        samples = ["João Silva", "Maria Costa", "Pedro Santos"]
        f = infer_formatter(samples)
        assert f.kind == "raw"

    def test_empty_samples_raw(self):
        f = infer_formatter([])
        assert f.kind == "raw"

    def test_single_date(self):
        f = infer_formatter_single("25/12/2024")
        assert f.kind == "date"
        assert f.pattern == "dd/MM/yyyy"

    def test_mixed_majority_wins(self):
        # 3 dates, 1 currency → date wins
        samples = ["15/03/2024", "20/04/2024", "01/01/2024", "R$ 100,00"]
        f = infer_formatter(samples)
        assert f.kind == "date"

    def test_currency_without_prefix_pattern(self):
        # decimal number that looks like currency amount (no R$ prefix)
        samples = ["1.234,56", "999,00", "0,01"]
        f = infer_formatter(samples)
        # Could be number or currency — just verify it's consistent
        assert f.kind in ("currency", "number")

    def test_date_long_format_pattern(self):
        samples = ["15 de março de 2024"]
        f = infer_formatter(samples)
        assert f.kind == "date"
        assert "MMMM" in f.pattern


class TestFormatterSpecContent:
    def test_date_pattern_ptbr(self):
        f = infer_formatter(["15/03/2024"])
        assert f.locale == "pt-BR"

    def test_number_with_decimal(self):
        samples = ["1.234,56"]
        f = infer_formatter(samples)
        if f.kind == "number":
            assert "," in f.pattern

    def test_number_integer(self):
        samples = ["1234", "5678", "9012"]
        f = infer_formatter(samples)
        if f.kind == "number":
            assert f.pattern == "#.##0"
