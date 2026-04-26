"""Unit tests for _is_body_text_pair (RC-G, story 48.19).

Root cause: body text pairs (stage_4_solo, empty label, prose) were reaching the LLM
matcher and incorrectly stealing XSD paths (ClienteTelefone/ClienteEmail/CEP) from
structured fields like TELEFONE, E-MAIL, and INSCRIÇÃO.

Fix: _is_body_text_pair() filters them before _group_pairs_by_section().
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _get_mod():
    import services.stages.stage4_mapping.section_matching as mod

    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pair(label: str, value: str, detected_format: str | None = None) -> dict[str, Any]:
    return {
        "label_text": label,
        "value_text": value,
        "value_block_id": "blk-x",
        "detected_format": detected_format,
    }


# ---------------------------------------------------------------------------
# Body text cases (should return True)
# ---------------------------------------------------------------------------


def test_body_text_no_label_long_prose_returns_true():
    mod = _get_mod()
    pair = _pair("", "pessoais e planos contratados com a MAG")
    assert mod._is_body_text_pair(pair) is True


def test_body_text_phone_context_prose_returns_true():
    pair = _pair("", "(demais localidades) e 0800 77 15 000")
    mod = _get_mod()
    assert mod._is_body_text_pair(pair) is True


def test_body_text_contact_site_prose_returns_true():
    pair = _pair("", "de contato disponíveis no site www.mag.com.br")
    mod = _get_mod()
    assert mod._is_body_text_pair(pair) is True


def test_body_text_greeting_closing_returns_true():
    pair = _pair("", "Conforme seu pedido, apresentamos abaixo a posição")
    mod = _get_mod()
    assert mod._is_body_text_pair(pair) is True


# ---------------------------------------------------------------------------
# Structured field cases (should return False)
# ---------------------------------------------------------------------------


def test_labeled_pair_with_phone_returns_false():
    mod = _get_mod()
    pair = _pair("TELEFONE", "(19) 98189-4732", detected_format="phone")
    assert mod._is_body_text_pair(pair) is False


def test_labeled_pair_without_format_returns_false():
    mod = _get_mod()
    pair = _pair("INSCRIÇÃO", "1124669542800")
    assert mod._is_body_text_pair(pair) is False


def test_unlabeled_with_format_returns_false():
    mod = _get_mod()
    pair = _pair("", "13271-608", detected_format="cep")
    assert mod._is_body_text_pair(pair) is False


def test_unlabeled_short_value_returns_false():
    mod = _get_mod()
    pair = _pair("", "CARTÃO DE CRÉDITO")
    assert mod._is_body_text_pair(pair) is False


def test_unlabeled_three_words_returns_false():
    """Exactly 3 words — below threshold of 4."""
    mod = _get_mod()
    pair = _pair("", "três palavras aqui")
    assert mod._is_body_text_pair(pair) is False


def test_empty_value_returns_false():
    mod = _get_mod()
    pair = _pair("", "")
    assert mod._is_body_text_pair(pair) is False


def test_labeled_long_prose_returns_false():
    """Even long prose with a label should NOT be filtered — it has a label."""
    mod = _get_mod()
    pair = _pair("Dados dos seguros:", "E-MAIL: TELMATSANCHES@GMAIL.COM")
    assert mod._is_body_text_pair(pair) is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_label_whitespace_only_treated_as_empty():
    """A label of only spaces should be treated as empty label."""
    mod = _get_mod()
    pair = _pair("   ", "pessoais e planos contratados com a MAG")
    assert mod._is_body_text_pair(pair) is True


def test_none_label_treated_as_empty():
    mod = _get_mod()
    pair = {
        "label_text": None,
        "value_text": "pessoais e planos contratados com a MAG",
        "value_block_id": "blk-x",
        "detected_format": None,
    }
    assert mod._is_body_text_pair(pair) is True
