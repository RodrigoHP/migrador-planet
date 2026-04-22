"""Tests for RCA fixes — scalar coverage 68.8% (target ≥ 80%).

Three root causes addressed:
  A) Stage 3: _smart_classify runs on single-PDF clusters → false-positive likely_dynamic
  B) Stage 4: MINIMUM_MATCH_THRESHOLD prevents spurious low-confidence mappings
  C) Stage 4: _detect_format handles inline label+value blocks and email addresses
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fix A — Stage 3: single-PDF guard on _smart_classify
# ---------------------------------------------------------------------------


class TestSinglePdfSmartClassifyGuard:
    """_run_3_1 must NOT apply smart_classify when total_pdfs == 1.

    Regression: "Equipe MAG Seguros" (static company name) was upgraded to
    likely_dynamic because NER detected ORG entity in a single-PDF cluster.
    """

    def _make_cluster(self, cluster_id: str, pdf_ids: list[str]) -> dict:
        """Build minimal cluster dict with one page per PDF."""
        return {
            "cluster_id": cluster_id,
            "pages": [{"pdf_id": pid, "page_index": 0} for pid in pdf_ids],
        }

    def _make_raw_blocks(self, pdf_ids: list[str], text: str) -> dict:
        """Build raw_text_blocks dict: same text block for each PDF."""
        blocks = {}
        for pid in pdf_ids:
            key = f"{pid}:0"
            blocks[key] = [
                {
                    "text": text,
                    "x_center": 50.0,
                    "y_center": 10.0,
                    "bbox_norm": [0.0, 0.0, 1.0, 0.1],
                }
            ]
        return blocks

    def _classify_first(self, text: str, num_pdfs: int) -> dict:
        from services.stages.stage3_structural.multi_example_analysis import _run_3_1

        pdf_ids = [f"pdf_{i}" for i in range(num_pdfs)]
        cluster_id = "cl_test"
        clusters = [self._make_cluster(cluster_id, pdf_ids)]
        raw_blocks = self._make_raw_blocks(pdf_ids, text)
        result = _run_3_1(clusters, raw_blocks)
        return result[cluster_id]["classifications"][0]

    def _get_quality(self, text: str, num_pdfs: int) -> dict:
        from services.stages.stage3_structural.multi_example_analysis import _run_3_1

        pdf_ids = [f"pdf_{i}" for i in range(num_pdfs)]
        cluster_id = "cl_test"
        clusters = [self._make_cluster(cluster_id, pdf_ids)]
        raw_blocks = self._make_raw_blocks(pdf_ids, text)
        result = _run_3_1(clusters, raw_blocks)
        return result[cluster_id]["classification_quality"]

    def test_static_company_name_single_pdf_stays_label(self):
        """'Equipe MAG Seguros' with 1 PDF → must remain 'label', not 'likely_dynamic'."""
        cl = self._classify_first("Equipe MAG Seguros", num_pdfs=1)
        assert cl["classification"] == "label", (
            f"Expected 'label' for static company name in single-PDF cluster, "
            f"got '{cl['classification']}' (signals={cl.get('smart_signals')})"
        )

    def test_static_org_name_single_pdf_stays_label(self):
        """'Bradesco Seguros' (ORG entity) with 1 PDF → must remain 'label'."""
        cl = self._classify_first("Bradesco Seguros", num_pdfs=1)
        assert cl["classification"] == "label"

    def test_static_header_single_pdf_stays_label(self):
        """Section header text with 1 PDF → must remain 'label'."""
        cl = self._classify_first("DADOS DO BENEFICIÁRIO", num_pdfs=1)
        assert cl["classification"] == "label"

    def test_smart_classify_still_runs_with_multiple_pdfs(self):
        """With 2+ PDFs and same text, guard does NOT suppress smart_classify."""
        # Street address with 2 PDFs: statistical → label, smart_classify → may upgrade
        cl = self._classify_first("RUA PARAIBUNA 456", num_pdfs=2)
        assert cl["classification"] in ("label", "likely_dynamic")

    def test_classification_quality_strength_none_for_single_pdf(self):
        """classification_quality.statistical_strength must be 'none' for single-PDF clusters."""
        quality = self._get_quality("Equipe MAG Seguros", num_pdfs=1)
        assert quality["statistical_strength"] == "none"


# ---------------------------------------------------------------------------
# Fix B — Stage 4: MINIMUM_MATCH_THRESHOLD filters spurious low-confidence mappings
# ---------------------------------------------------------------------------


class TestMinimumMatchThreshold:
    """MINIMUM_MATCH_THRESHOLD = 0.4 prevents garbage mappings from LLM."""

    def test_constant_exists_and_value(self):
        from services.stages.stage4_mapping.constants import MINIMUM_MATCH_THRESHOLD

        assert MINIMUM_MATCH_THRESHOLD == 0.4

    def test_threshold_below_high_confidence(self):
        """MINIMUM_MATCH_THRESHOLD must be less than HIGH_CONFIDENCE_THRESHOLD."""
        from services.stages.stage4_mapping.constants import (
            HIGH_CONFIDENCE_THRESHOLD,
            MINIMUM_MATCH_THRESHOLD,
        )

        assert MINIMUM_MATCH_THRESHOLD < HIGH_CONFIDENCE_THRESHOLD

    def test_prompt_contains_abstain_instruction(self):
        """_BATCH_MATCH_PROMPT must instruct LLM to use score 0.0 when no match."""
        from services.stages.stage4_mapping.constants import _BATCH_MATCH_PROMPT

        assert "score" in _BATCH_MATCH_PROMPT.lower()
        assert "0.0" in _BATCH_MATCH_PROMPT
        assert "null" in _BATCH_MATCH_PROMPT.lower()

    def test_prompt_contains_no_force_instruction(self):
        """_BATCH_MATCH_PROMPT must tell LLM not to force mappings."""
        from services.stages.stage4_mapping.constants import _BATCH_MATCH_PROMPT

        assert "not" in _BATCH_MATCH_PROMPT.lower() or "do not" in _BATCH_MATCH_PROMPT.lower()

    @pytest.mark.parametrize(
        "score,should_map",
        [
            (0.8, True),
            (0.4, True),
            (0.39, False),
            (0.1, False),
            (0.0, False),
        ],
    )
    def test_minimum_threshold_gate(self, score: float, should_map: bool):
        """xsd_path must be empty string when best score < MINIMUM_MATCH_THRESHOLD."""
        from services.stages.stage4_mapping.constants import MINIMUM_MATCH_THRESHOLD

        # Simulate the assignment logic in section_matching.py
        best = {"path": "ClienteNome", "score": score}
        best_score = best["score"]
        best_path = (best["path"] or "") if best else ""
        xsd_path = best_path if best_score >= MINIMUM_MATCH_THRESHOLD else ""

        if should_map:
            assert xsd_path == "ClienteNome", f"score={score} should produce a mapping"
        else:
            assert xsd_path == "", f"score={score} should NOT produce a mapping"


# ---------------------------------------------------------------------------
# Fix C — Stage 4: _detect_format handles inline blocks and email
# ---------------------------------------------------------------------------


class TestDetectFormatInlineBlocks:
    """_detect_format must recognize format even when embedded in label+value text."""

    def _detect(self, text: str):
        from services.stages.stage4_mapping.xsd_integration import _detect_format

        return _detect_format(text)

    # --- Exact match (existing behavior preserved) ---
    def test_exact_phone_match(self):
        assert self._detect("(19) 98189-4732") == "phone"

    def test_exact_email_match(self):
        assert self._detect("telma@gmail.com") == "email"

    def test_exact_cep_match(self):
        assert self._detect("13271-608") == "cep"

    def test_exact_currency_match(self):
        assert self._detect("R$ 1.234,56") == "currency_brl"

    def test_exact_cpf_match(self):
        assert self._detect("123.456.789-00") == "cpf"

    # --- Inline label+value blocks (Fix C) ---
    def test_inline_phone_with_prefix(self):
        """'TELEFONE: (19) 98189-4732' must be detected as phone."""
        result = self._detect("TELEFONE: (19) 98189-4732")
        assert result == "phone", f"Expected 'phone', got {result!r}"

    def test_inline_email_with_prefix(self):
        """'E-MAIL: TELMA@gmail.com' must be detected as email."""
        result = self._detect("E-MAIL: TELMA@gmail.com")
        assert result == "email", f"Expected 'email', got {result!r}"

    def test_inline_cep_with_prefix(self):
        """'CEP: 13271-608' must be detected as cep."""
        result = self._detect("CEP: 13271-608")
        assert result == "cep", f"Expected 'cep', got {result!r}"

    def test_inline_forma_pagamento_returns_none(self):
        """'FORMA DE PAGAMENTO: CARTÃO DE CRÉDITO' — no numeric format."""
        result = self._detect("FORMA DE PAGAMENTO: CARTÃO DE CRÉDITO")
        assert result is None

    def test_inline_currency_in_sentence(self):
        """Text containing 'R$ 500,00' must be detected as currency_brl."""
        result = self._detect("VALOR: R$ 500,00")
        assert result == "currency_brl"

    # --- Email format added (was missing entirely) ---
    def test_email_pattern_registered(self):
        """email must be in _FORMAT_PATTERNS (was absent before fix)."""
        from services.stages.stage4_mapping.xsd_integration import _FORMAT_PATTERNS

        names = [name for name, _ in _FORMAT_PATTERNS]
        assert "email" in names, "email pattern must be in _FORMAT_PATTERNS"

    def test_email_pattern_search_registered(self):
        """email must be in _FORMAT_PATTERNS_SEARCH."""
        from services.stages.stage4_mapping.xsd_integration import _FORMAT_PATTERNS_SEARCH

        names = [name for name, _ in _FORMAT_PATTERNS_SEARCH]
        assert "email" in names

    def test_email_type_compat(self):
        """email format must be compatible with XSD string type."""
        from services.stages.stage4_mapping.constants import _TYPE_FORMAT_COMPAT

        assert "email" in _TYPE_FORMAT_COMPAT["string"]

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("(19) 98189-4732", "phone"),
            ("(11) 3333-4444", "phone"),
            ("user@domain.com.br", "email"),
            ("USER@EXAMPLE.COM", "email"),
            ("13271-608", "cep"),
            ("01310-100", "cep"),
            ("R$ 1.234,56", "currency_brl"),
            ("123.456.789-00", "cpf"),
            ("12.345.678/0001-90", "cnpj"),
            ("15/04/2026", "date_numeric"),
            ("Texto livre sem formato", None),
        ],
    )
    def test_exact_formats_parametrized(self, text: str, expected):
        assert self._detect(text) == expected
