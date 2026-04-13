"""Tests for Stage 3 — _smart_classify and _DYNAMIC_PATTERNS.

Story 43.1 — Fix Stage 3 Semantic Misclassification: VALUE Blocks Treated as Labels.
Covers AC4: verify that street_address and pure_number patterns correctly classify
blocks that were previously misclassified as labels.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# _COMPILED_DYNAMIC_PATTERNS — direct pattern tests
# ---------------------------------------------------------------------------


class TestDynamicPatterns:
    """Verify _COMPILED_DYNAMIC_PATTERNS includes new patterns (AC1)."""

    def test_street_address_pattern_registered(self):
        from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

        names = [name for _, name, _ in _COMPILED_DYNAMIC_PATTERNS]
        assert "street_address" in names, "street_address pattern must be in _DYNAMIC_PATTERNS"

    def test_pure_number_pattern_registered(self):
        from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

        names = [name for _, name, _ in _COMPILED_DYNAMIC_PATTERNS]
        assert "pure_number" in names, "pure_number pattern must be in _DYNAMIC_PATTERNS"

    def test_street_address_weight(self):
        from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

        weight = next(w for _, name, w in _COMPILED_DYNAMIC_PATTERNS if name == "street_address")
        assert weight == 0.85

    def test_pure_number_weight(self):
        from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

        weight = next(w for _, name, w in _COMPILED_DYNAMIC_PATTERNS if name == "pure_number")
        assert weight == 0.65


# ---------------------------------------------------------------------------
# _smart_classify — behavioral tests (AC4)
# ---------------------------------------------------------------------------


class TestSmartClassifyStreetAddress:
    """Endereços com prefixo de logradouro devem ser is_likely_dynamic=True."""

    def _classify(self, text: str):
        from services.stages.stage3_structural.multi_example_analysis import _smart_classify

        return _smart_classify(text)

    def test_rua_paraibuna(self):
        """AC4: 'RUA PARAIBUNA 456' → is_likely_dynamic=True (was misclassified as label)."""
        is_dynamic, score, signals = self._classify("RUA PARAIBUNA 456")
        assert is_dynamic is True, f"Expected True, got {is_dynamic} (score={score})"
        assert score >= 0.7

    def test_avenida_paulista(self):
        """AC4: 'AV. PAULISTA 1000' → is_likely_dynamic=True."""
        is_dynamic, score, signals = self._classify("AV. PAULISTA 1000")
        assert is_dynamic is True, f"Expected True, got {is_dynamic} (score={score})"

    def test_avenida_full(self):
        is_dynamic, score, _ = self._classify("AVENIDA BRASIL 500")
        assert is_dynamic is True

    def test_travessa(self):
        is_dynamic, score, _ = self._classify("TRAVESSA DAS FLORES 12")
        assert is_dynamic is True

    def test_rodovia(self):
        is_dynamic, score, _ = self._classify("RODOVIA BR-101 KM 5")
        assert is_dynamic is True

    def test_alameda(self):
        is_dynamic, score, _ = self._classify("ALAMEDA SANTOS 100")
        assert is_dynamic is True

    def test_estrada(self):
        is_dynamic, score, _ = self._classify("ESTRADA DAS PEDRAS 77")
        assert is_dynamic is True


class TestSmartClassifyPureNumber:
    """Códigos numéricos puros (2+ dígitos) devem ser is_likely_dynamic=True."""

    def _classify(self, text: str):
        from services.stages.stage3_structural.multi_example_analysis import _smart_classify

        return _smart_classify(text)

    def test_237(self):
        """AC4: '237' → is_likely_dynamic=True (bank code, was misclassified)."""
        is_dynamic, score, _ = self._classify("237")
        assert is_dynamic is True, f"Expected True, got {is_dynamic} (score={score})"

    def test_005(self):
        """AC4: '005' → is_likely_dynamic=True."""
        is_dynamic, score, _ = self._classify("005")
        assert is_dynamic is True

    def test_8600(self):
        """AC4: '8600' → is_likely_dynamic=True."""
        is_dynamic, score, _ = self._classify("8600")
        assert is_dynamic is True

    def test_000(self):
        """AC4: '000' → is_likely_dynamic=True."""
        is_dynamic, score, _ = self._classify("000")
        assert is_dynamic is True

    def test_single_digit_not_affected(self):
        """Single digit '1' or '2' should NOT be forced to dynamic (section headers)."""
        # pure_number requires 2+ digits — single digits return uncertain (None) not True
        from services.stages.stage3_structural.multi_example_analysis import _smart_classify

        is_dynamic, score, _ = _smart_classify("1")
        # Acceptable: None (uncertain) or False — NOT True
        assert is_dynamic is not True, "Single digit '1' should not be classified as dynamic (could be section header)"


class TestSmartClassifyLabelsNotAffected:
    """Labels legítimos não devem ser afetados pelos novos patterns (AC4)."""

    def _classify(self, text: str):
        from services.stages.stage3_structural.multi_example_analysis import _smart_classify

        return _smart_classify(text)

    def test_beneficiario_label(self):
        """AC4: 'Beneficiário:' → is_likely_dynamic=False (legitimate label)."""
        is_dynamic, score, _ = self._classify("Beneficiário:")
        assert is_dynamic is False, f"Expected False (label), got {is_dynamic}"

    def test_nosso_numero_label(self):
        """AC4: 'Nosso Número' → not classified as dynamic (short label, no digits)."""
        is_dynamic, score, _ = self._classify("Nosso Número")
        assert is_dynamic is not True, f"'Nosso Número' should be label, got is_dynamic={is_dynamic}"

    def test_vencimento_label(self):
        is_dynamic, score, _ = self._classify("Vencimento:")
        assert is_dynamic is False

    def test_sacado_label(self):
        is_dynamic, score, _ = self._classify("Sacado")
        assert is_dynamic is not True

    def test_cedente_label(self):
        is_dynamic, score, _ = self._classify("Cedente:")
        assert is_dynamic is False


# ---------------------------------------------------------------------------
# _COMPILED_DYNAMIC_PATTERNS — direct regex match tests
# ---------------------------------------------------------------------------


class TestPatternRegexDirectly:
    """Test regex patterns match expected inputs directly."""

    def _get_pattern(self, name: str):
        from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

        return next(p for p, n, _ in _COMPILED_DYNAMIC_PATTERNS if n == name)

    def test_street_address_matches_rua(self):
        p = self._get_pattern("street_address")
        assert p.search("RUA PARAIBUNA 456")

    def test_street_address_matches_av_dot(self):
        p = self._get_pattern("street_address")
        assert p.search("AV. PAULISTA 1000")

    def test_street_address_no_match_plain_text(self):
        p = self._get_pattern("street_address")
        assert not p.search("SAO JOSE DOS CAMPOS - SP")

    def test_street_address_no_match_label(self):
        p = self._get_pattern("street_address")
        assert not p.search("Endereço:")

    def test_pure_number_matches_237(self):
        p = self._get_pattern("pure_number")
        assert p.search("237")

    def test_pure_number_matches_000(self):
        p = self._get_pattern("pure_number")
        assert p.search("000")

    def test_pure_number_no_match_decimal(self):
        p = self._get_pattern("pure_number")
        assert not p.search("4.978,54")  # decimal — handled by decimal/currency pattern

    def test_pure_number_no_match_single_digit(self):
        p = self._get_pattern("pure_number")
        assert not p.search("1")  # single digit excluded

    def test_pure_number_no_match_with_text(self):
        p = self._get_pattern("pure_number")
        assert not p.search("237 BANCO")  # has text after
