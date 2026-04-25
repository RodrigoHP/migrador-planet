"""Tests for Stage 3 — Body-text filter (Story 48.14 — RC-A).

Verifies that letter-prose fields are downgraded to static_body_text before
reaching Stage 4, while structured field values remain as likely_dynamic/dynamic.

All tests are @pytest.mark.unit (no I/O, no PDFs, spaCy unavailable).
When spaCy is unavailable (Python 3.14 / test env), Layer 2 (NER LOC detection)
is skipped gracefully — Layer 1 (embedded stopword ratio) still covers cases 1-5.
Case 3 (JARDIM PAIQUERE) requires spaCy LOC detection — tested separately with mock.

Design note on test helpers:
  _classify_varying — different text per PDF → statistical = 'dynamic' or 'semi_dynamic'
  _classify_same    — same text across PDFs → statistical = 'label' + smart_override path
The E2E false positives arise because letter text varies slightly per client, so
we use _classify_varying for AC2 tests to mirror the real pipeline path.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cluster(cluster_id: str, pdf_ids: list[str]) -> dict:
    return {
        "cluster_id": cluster_id,
        "pages": [{"pdf_id": pid, "page_index": 0} for pid in pdf_ids],
    }


def _make_raw_blocks_varying(pdf_ids: list[str], texts: list[str]) -> dict:
    """Different text per PDF → statistical = 'dynamic' or 'semi_dynamic'.

    All blocks share the same position so they form one position_map entry.
    """
    blocks = {}
    for i, pid in enumerate(pdf_ids):
        key = f"{pid}:0"
        blocks[key] = [
            {
                "text": texts[i % len(texts)],
                "x_center": 50.0,
                "y_center": 50.0,
                "bbox_norm": [0.0, 0.4, 1.0, 0.6],
            }
        ]
    return blocks


def _make_raw_blocks_same(pdf_ids: list[str], text: str) -> dict:
    """Same text across all PDFs → statistical = 'label'."""
    return _make_raw_blocks_varying(pdf_ids, [text])


def _classify_varying(base_text: str, variant_text: str | None = None) -> dict:
    """Classify text that varies across 3 PDFs → triggers statistical dynamic path.

    Uses base_text + (variant_text or base_text + ' v2') across PDFs so that
    unique_texts > 1 and statistical classification becomes 'dynamic' or
    'semi_dynamic', mirroring the E2E false positive scenario.
    """
    from services.stages.stage3_structural.multi_example_analysis import _run_3_1

    pdf_ids = ["pdf_a", "pdf_b", "pdf_c"]
    cluster_id = "cl_test"
    clusters = [_make_cluster(cluster_id, pdf_ids)]
    v2 = variant_text or (base_text + " (cliente 2)")
    v3 = variant_text or (base_text + " (cliente 3)")
    blocks = _make_raw_blocks_varying(pdf_ids, [base_text, v2, v3])
    result = _run_3_1(clusters, blocks)
    return result[cluster_id]["classifications"][0]


def _classify_same(text: str) -> dict:
    """Classify text identical across 2 PDFs → statistical = 'label', smart_override runs."""
    from services.stages.stage3_structural.multi_example_analysis import _run_3_1

    pdf_ids = ["pdf_a", "pdf_b"]
    cluster_id = "cl_test"
    clusters = [_make_cluster(cluster_id, pdf_ids)]
    raw_blocks = _make_raw_blocks_same(pdf_ids, text)
    result = _run_3_1(clusters, raw_blocks)
    return result[cluster_id]["classifications"][0]


# ---------------------------------------------------------------------------
# AC2 — False positives: must be classified as static_body_text
# These are letter-prose fields confirmed in E2E run 2026-04-25.
# In E2E they arrive as dynamic/semi_dynamic because text varies per client.
# ---------------------------------------------------------------------------


class TestBodyTextFalsePositivesFiltered:
    """AC2: confirmed false positives must be reclassified as static_body_text."""

    def test_pedimos_que_voce(self):
        """'Pedimos que você verifique seus dados' → static_body_text (stopword ratio ≈ 50%)."""
        cl = _classify_varying("Pedimos que você verifique seus dados")
        assert cl["classification"] == "static_body_text", f"Expected 'static_body_text', got '{cl['classification']}'"
        assert cl["method"] == "body_text_filter"

    def test_pessoais_e_planos(self):
        """'pessoais e planos contratados' → static_body_text (stopword 'e' present)."""
        cl = _classify_varying("pessoais e planos contratados")
        assert cl["classification"] == "static_body_text", f"Expected 'static_body_text', got '{cl['classification']}'"

    def test_conforme_seu_pedido(self):
        """'Conforme seu pedido, apresentamos' → static_body_text."""
        cl = _classify_varying("Conforme seu pedido, apresentamos")
        assert cl["classification"] == "static_body_text", f"Expected 'static_body_text', got '{cl['classification']}'"

    def test_de_contato_disponiveis(self):
        """'de contato disponíveis no site' → static_body_text (stopword ratio ≈ 50%)."""
        cl = _classify_varying("de contato disponíveis no site")
        assert cl["classification"] == "static_body_text", f"Expected 'static_body_text', got '{cl['classification']}'"

    def test_smart_signals_contain_marker(self):
        """static_body_text fields must have 'body_text_filtered' in smart_signals."""
        cl = _classify_varying("de contato disponíveis no site")
        assert "body_text_filtered" in (cl.get("smart_signals") or [])


# ---------------------------------------------------------------------------
# AC3 — Structured fields: must NOT be filtered
# ---------------------------------------------------------------------------


class TestStructuredFieldsNotFiltered:
    """AC3: structured fields must reach Stage 4 — not filtered by body-text heuristic."""

    def test_telefone_inline(self):
        """'TELEFONE: (19) 98189-4732' → NOT static_body_text (phone pattern matches)."""
        cl = _classify_varying("TELEFONE: (19) 98189-4732")
        assert cl["classification"] != "static_body_text", (
            f"Phone field must NOT be filtered. Got '{cl['classification']}'"
        )

    def test_email_uppercase(self):
        """'TELMATSANCHES@GMAIL.COM' → NOT static_body_text (email pattern matches)."""
        cl = _classify_varying("TELMATSANCHES@GMAIL.COM")
        assert cl["classification"] != "static_body_text", (
            f"Email field must NOT be filtered. Got '{cl['classification']}'"
        )

    def test_cep(self):
        """'13271-608' → NOT static_body_text (CEP + short text)."""
        cl = _classify_varying("13271-608")
        assert cl["classification"] != "static_body_text", (
            f"CEP field must NOT be filtered. Got '{cl['classification']}'"
        )

    def test_valor_monetario(self):
        """'591,70' → NOT static_body_text (short decimal, < 4 words)."""
        cl = _classify_varying("591,70")
        assert cl["classification"] != "static_body_text", (
            f"Currency value must NOT be filtered. Got '{cl['classification']}'"
        )

    def test_numero_certificado(self):
        """'1124669542800' → NOT static_body_text (certificate number pattern)."""
        cl = _classify_varying("1124669542800")
        assert cl["classification"] != "static_body_text", (
            f"Certificate number must NOT be filtered. Got '{cl['classification']}'"
        )


# ---------------------------------------------------------------------------
# AC1/AC5 — Unit tests for helper functions (no _run_3_1 overhead)
# ---------------------------------------------------------------------------


class TestIsBodyText:
    """Direct tests for _is_body_text helper (Layer 1 — embedded stopwords).

    AC5: ratio computed by embedded PT stopword list, threshold documented in source.
    """

    def _is_body(self, text: str) -> bool:
        from services.stages.stage3_structural.multi_example_analysis import _is_body_text

        return _is_body_text(text, nlp=None)  # no spaCy (unit test environment)

    # --- Cases that SHOULD be body text ---

    def test_pedimos_que_detected(self):
        assert self._is_body("Pedimos que você verifique seus dados") is True

    def test_conforme_seu_detected(self):
        assert self._is_body("Conforme seu pedido, apresentamos") is True

    def test_de_contato_disponiveis_detected(self):
        assert self._is_body("de contato disponíveis no site") is True

    def test_pessoais_e_planos_detected(self):
        assert self._is_body("pessoais e planos contratados") is True

    # --- Edge cases: too short → never body text ---

    def test_short_text_cep_label(self):
        """Single token < 4 words → never body-text."""
        assert self._is_body("CEP:") is False

    def test_short_text_vencimento(self):
        assert self._is_body("Vencimento") is False

    def test_short_text_decimal(self):
        assert self._is_body("591,70") is False

    def test_three_words_boundary(self):
        """3 words is below minimum threshold (< 4)."""
        assert self._is_body("de contato disponíveis") is False

    # --- Structured values that should not be body text ---

    def test_email_not_body(self):
        """Email address has no stopwords → not body text."""
        assert self._is_body("TELMATSANCHES@GMAIL.COM") is False

    def test_pure_number_not_body(self):
        """Pure numeric certificate number → not body text."""
        assert self._is_body("1124669542800") is False

    def test_cep_not_body(self):
        """CEP string has 1 token → not body text."""
        assert self._is_body("13271-608") is False

    # --- Threshold boundary ---

    def test_stopword_threshold_documented(self):
        """The threshold constant must be present and set to expected value."""
        from services.stages.stage3_structural.multi_example_analysis import (
            _BODY_TEXT_STOPWORD_THRESHOLD,
        )

        assert 0.20 <= _BODY_TEXT_STOPWORD_THRESHOLD <= 0.40, (
            f"Threshold {_BODY_TEXT_STOPWORD_THRESHOLD} outside expected range [0.20, 0.40]"
        )


class TestMatchesStructuredExempt:
    """Direct tests for _matches_structured_exempt helper."""

    def _exempt(self, text: str) -> bool:
        from services.stages.stage3_structural.multi_example_analysis import _matches_structured_exempt

        return _matches_structured_exempt(text)

    def test_phone_is_exempt(self):
        assert self._exempt("(19) 98189-4732") is True

    def test_inline_phone_is_exempt(self):
        """'TELEFONE: (19) 98189-4732' contains phone → exempt."""
        assert self._exempt("TELEFONE: (19) 98189-4732") is True

    def test_email_is_exempt(self):
        assert self._exempt("TELMATSANCHES@GMAIL.COM") is True

    def test_cep_is_exempt(self):
        assert self._exempt("13271-608") is True

    def test_currency_is_exempt(self):
        assert self._exempt("R$ 591,70") is True

    def test_certificate_number_is_exempt(self):
        assert self._exempt("1124669542800") is True

    def test_decimal_is_exempt(self):
        assert self._exempt("591,70") is True

    def test_cpf_is_exempt(self):
        assert self._exempt("123.456.789-00") is True

    def test_prose_not_exempt(self):
        assert self._exempt("Pedimos que você verifique seus dados") is False

    def test_city_state_not_exempt(self):
        """'JARDIM PAIQUERE, VALINHOS, SP' has no phone/email/CEP/currency → not exempt."""
        assert self._exempt("JARDIM PAIQUERE, VALINHOS, SP") is False

    def test_short_label_not_exempt(self):
        assert self._exempt("Beneficiário:") is False


# ---------------------------------------------------------------------------
# Edge case: body text filter with spaCy mock (LOC detection — case 3)
# ---------------------------------------------------------------------------


class TestBodyTextWithSpacyMock:
    """Test Layer 2 (spaCy LOC/GPE) for all-caps location strings with 0 stopwords."""

    def test_jardim_paiquere_filtered_with_spacy_loc(self):
        """'JARDIM PAIQUERE, VALINHOS, SP' → body_text when spaCy returns LOC entity."""
        from services.stages.stage3_structural.multi_example_analysis import _is_body_text

        mock_ent = MagicMock()
        mock_ent.label_ = "LOC"
        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc

        result = _is_body_text("JARDIM PAIQUERE, VALINHOS, SP", nlp=mock_nlp)
        assert result is True, "LOC entity should trigger body-text classification"

    def test_jardim_paiquere_not_filtered_without_spacy(self):
        """Without spaCy (nlp=None), 'JARDIM PAIQUERE, VALINHOS, SP' has 0 stopwords.

        Conservative behaviour: without spaCy, the filter does NOT fire for this case.
        The field passes through (false negative preferable to filtering a real value).
        """
        from services.stages.stage3_structural.multi_example_analysis import _is_body_text

        result = _is_body_text("JARDIM PAIQUERE, VALINHOS, SP", nlp=None)
        assert result is False

    def test_run_3_1_jardim_paiquere_with_mocked_spacy(self):
        """Integration: _run_3_1 filters 'JARDIM PAIQUERE' when spaCy mock returns LOC."""
        import services.stages.stage3_structural.multi_example_analysis as mod

        mock_ent = MagicMock()
        mock_ent.label_ = "LOC"
        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent]
        mock_nlp = MagicMock()
        mock_nlp.return_value = mock_doc

        original_nlp = mod._nlp
        try:
            mod._nlp = mock_nlp
            cl = _classify_varying("JARDIM PAIQUERE, VALINHOS, SP")
            assert cl["classification"] == "static_body_text", (
                f"Expected 'static_body_text' with spaCy LOC mock, got '{cl['classification']}'"
            )
        finally:
            mod._nlp = original_nlp


# ---------------------------------------------------------------------------
# AC4 — Boleto regression: boleto fields must remain dynamic/label
# ---------------------------------------------------------------------------


class TestBoletoRegressionNotFiltered:
    """AC4: boleto-specific fields must NOT be downgraded by body-text filter."""

    def test_boleto_cedente_label(self):
        """'Beneficiário:' (ends with colon) → label — not touched by body-text filter."""
        cl = _classify_same("Beneficiário:")
        assert cl["classification"] != "static_body_text"

    def test_boleto_nosso_numero(self):
        """'Nosso Número' (short label) → not body text (< 4 words)."""
        cl = _classify_same("Nosso Número")
        assert cl["classification"] != "static_body_text"

    def test_boleto_bank_code_is_body_false(self):
        """'237' (bank code) — < 4 words → _is_body_text returns False."""
        from services.stages.stage3_structural.multi_example_analysis import _is_body_text

        result = _is_body_text("237", nlp=None)
        assert result is False

    def test_boleto_valor_documento(self):
        """'R$ 4.978,54' → exempt (currency pattern)."""
        from services.stages.stage3_structural.multi_example_analysis import _matches_structured_exempt

        assert _matches_structured_exempt("R$ 4.978,54") is True

    def test_boleto_data_vencimento(self):
        """'15/04/2026' → exempt (date pattern)."""
        from services.stages.stage3_structural.multi_example_analysis import _matches_structured_exempt

        assert _matches_structured_exempt("15/04/2026") is True

    def test_boleto_cpf(self):
        """'123.456.789-00' → exempt (CPF pattern)."""
        from services.stages.stage3_structural.multi_example_analysis import _matches_structured_exempt

        assert _matches_structured_exempt("123.456.789-00") is True
