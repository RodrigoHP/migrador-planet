"""C3 precision measurement — formatter inference against ground truth.

Spike: spike/ast-validation — C3 gate: ≥70% precision on annotated field corpus.

Ground truth: docs/reports/spike-ast/formatter-ground-truth.yaml
100 fields (50 BoletoIndividual + 50 PosicaoConsolidada) annotated with
expected_kind and expected_pattern from XSD domain knowledge.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BACKEND = str(Path(__file__).resolve().parents[3])
_REPO = str(Path(__file__).resolve().parents[5])
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest
import yaml

from services.stages.stage3_structural.formatter_inference import infer_formatter

pytestmark = pytest.mark.unit

_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[4] / "docs" / "reports" / "spike-ast" / "formatter-ground-truth.yaml"
)

C3_PRECISION_GATE = 0.70  # ≥70% required for Go/No-Go


def _load_ground_truth() -> list[dict[str, Any]]:
    with open(_GROUND_TRUTH_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    fields: list[dict[str, Any]] = []
    for doc_type, entries in data.items():
        if isinstance(entries, list):
            for entry in entries:
                entry["_doc_type"] = doc_type
                fields.append(entry)
    return fields


class TestC3FormatterPrecision:
    """C3 gate: ≥70% of dynamic fields correctly inferred by formatter_inference."""

    def test_ground_truth_loaded(self):
        fields = _load_ground_truth()
        assert len(fields) >= 90, f"Ground truth too small: {len(fields)} entries"

    def test_c3_precision_gate(self):
        """C3 gate: precision ≥ 70% across all annotated fields."""
        fields = _load_ground_truth()
        correct = 0
        incorrect = []

        for f in fields:
            sample = f["sample"]
            expected_kind = f["expected_kind"]
            result = infer_formatter([sample])
            if result.kind == expected_kind:
                correct += 1
            else:
                incorrect.append(
                    {
                        "field": f["field"],
                        "sample": sample,
                        "expected": expected_kind,
                        "got": result.kind,
                        "doc_type": f.get("_doc_type", "?"),
                    }
                )

        precision = correct / len(fields)
        report_lines = [
            "\nC3 Formatter Precision Report",
            f"Total fields: {len(fields)}",
            f"Correct: {correct}",
            f"Incorrect: {len(incorrect)}",
            f"Precision: {precision:.1%}",
            f"Gate: >={C3_PRECISION_GATE:.0%}",
            "",
        ]
        if incorrect:
            report_lines.append("Misclassified fields:")
            for item in incorrect:
                report_lines.append(
                    f"  [{item['doc_type']}] {item['field']}: "
                    f"sample={item['sample']!r} "
                    f"expected={item['expected']} got={item['got']}"
                )

        report = "\n".join(report_lines)
        assert precision >= C3_PRECISION_GATE, f"C3 FAIL: precision {precision:.1%} < {C3_PRECISION_GATE:.0%}\n{report}"

    def test_c3_currency_precision(self):
        """Currency fields (R$) must have near-perfect precision."""
        fields = _load_ground_truth()
        currency_fields = [f for f in fields if f["expected_kind"] == "currency"]
        if not currency_fields:
            pytest.skip("No currency fields in ground truth")

        correct = sum(1 for f in currency_fields if infer_formatter([f["sample"]]).kind == "currency")
        precision = correct / len(currency_fields)
        assert precision >= 0.90, f"Currency precision {precision:.1%} < 90% (got {correct}/{len(currency_fields)})"

    def test_c3_date_precision(self):
        """Date fields (dd/MM/yyyy) must have ≥85% precision."""
        fields = _load_ground_truth()
        date_fields = [f for f in fields if f["expected_kind"] == "date"]
        if not date_fields:
            pytest.skip("No date fields in ground truth")

        correct = sum(1 for f in date_fields if infer_formatter([f["sample"]]).kind == "date")
        precision = correct / len(date_fields)
        assert precision >= 0.85, f"Date precision {precision:.1%} < 85% (got {correct}/{len(date_fields)})"

    def test_c3_percent_precision(self):
        """Percent fields must have ≥85% precision."""
        fields = _load_ground_truth()
        percent_fields = [f for f in fields if f["expected_kind"] == "percent"]
        if not percent_fields:
            pytest.skip("No percent fields in ground truth")

        correct = sum(1 for f in percent_fields if infer_formatter([f["sample"]]).kind == "percent")
        precision = correct / len(percent_fields)
        assert precision >= 0.85, f"Percent precision {precision:.1%} < 85% (got {correct}/{len(percent_fields)})"

    def test_c3_raw_precision(self):
        """Raw/string fields should not be mis-classified as typed formatters."""
        fields = _load_ground_truth()
        raw_fields = [f for f in fields if f["expected_kind"] == "raw"]
        if not raw_fields:
            pytest.skip("No raw fields in ground truth")

        correct = sum(1 for f in raw_fields if infer_formatter([f["sample"]]).kind == "raw")
        precision = correct / len(raw_fields)
        # Raw fields can be harder (e.g. "341" looks like a number) — gate at 60%
        assert precision >= 0.60, f"Raw precision {precision:.1%} < 60% (got {correct}/{len(raw_fields)})"

    def test_c3_boleto_vs_posicao_breakdown(self):
        """Breakdown by document type to confirm both pass individually."""
        fields = _load_ground_truth()
        for doc_type in ("boleto_individual", "posicao_consolidada"):
            doc_fields = [f for f in fields if f.get("_doc_type") == doc_type]
            if not doc_fields:
                continue
            correct = sum(1 for f in doc_fields if infer_formatter([f["sample"]]).kind == f["expected_kind"])
            precision = correct / len(doc_fields)
            assert precision >= C3_PRECISION_GATE, (
                f"{doc_type}: precision {precision:.1%} < {C3_PRECISION_GATE:.0%} ({correct}/{len(doc_fields)})"
            )
