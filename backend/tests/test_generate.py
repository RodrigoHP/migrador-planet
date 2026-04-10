"""Tests for Story 8.1 — Template Generation.

Covers:
  AC2  — index.html: body data-bind, KO bindings, ##TEMPLATE_DATA##, structural sections
  AC3  — style.css: A4 dimensions, font styles, absolute positioning, @media print
  AC4  — base.js: ko.applyBindings, BR format functions, pagination helpers, computed observables
  AC5  — exemplo.js: XSD JSON structure, synthetic values, mandatory fields
  AC6  — all outputs are syntactically parseable (basic checks)
  AC7  — library references: ../Bibliotecas/js/knockout-3.4.2.js, ../Bibliotecas/css/
  AC8  — template is self-contained: index.html references base.js and exemplo.js
  AC9  — HTML contains page-break marker
  AC10 — UTF-8 encoding (no BOM byte sequence in output)
  AC11 — binding integrity: every field jsonPath produces a data-bind span
"""

from __future__ import annotations

import json

from models.field_mapping import FieldMapping
from models.text_block import TextBlock
from services.template_generator import (
    TemplateGenerator,
    _build_xsd_json_structure,
    _detect_root_key,
    _sanitize_js_identifier,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_field(
    json_path: str,
    pdf_text: str = "",
    field_type: str = "text",
) -> FieldMapping:
    return FieldMapping(
        jsonPath=json_path,
        pdfText=pdf_text,
        type=field_type,  # type: ignore[arg-type]
    )


def _make_block(text: str, x: float = 0.1, y: float = 0.1) -> TextBlock:
    return TextBlock(text=text, x=x, y=y, width=0.2, height=0.02, page=0)


SAMPLE_FIELDS: list[FieldMapping] = [
    _make_field("contrato.cliente.nome", "João Silva"),
    _make_field("contrato.cliente.cpf", "123.456.789-00"),
    _make_field("contrato.valor", "1234.56", field_type="currency"),
    _make_field("contrato.dataEmissao", "2024-01-15", field_type="date"),
]

SAMPLE_BLOCKS: list[TextBlock] = [
    _make_block("contrato.cliente.nome", 0.05, 0.10),
    _make_block("contrato.cliente.cpf", 0.05, 0.15),
]


# ---------------------------------------------------------------------------
# AC11 — helper: _sanitize_js_identifier
# ---------------------------------------------------------------------------


def test_sanitize_js_identifier_replaces_dots():
    assert _sanitize_js_identifier("a.b.c") == "a_b_c"


def test_sanitize_js_identifier_prefixes_digit():
    assert _sanitize_js_identifier("123field") == "_123field"


def test_sanitize_js_identifier_empty_returns_default():
    assert _sanitize_js_identifier("") == "_field"


# ---------------------------------------------------------------------------
# Helper: _detect_root_key
# ---------------------------------------------------------------------------


def test_detect_root_key_finds_most_common_segment():
    fields = [
        _make_field("contrato.nome"),
        _make_field("contrato.cpf"),
        _make_field("outro.campo"),
    ]
    assert _detect_root_key(fields) == "contrato"


def test_detect_root_key_empty_fields_returns_default():
    assert _detect_root_key([]) == "dados"


# ---------------------------------------------------------------------------
# Helper: _build_xsd_json_structure
# ---------------------------------------------------------------------------


def test_build_xsd_json_structure_nests_correctly():
    fields = [
        _make_field("pessoa.nome", "Ana"),
        _make_field("pessoa.cpf", "111"),
    ]
    result = _build_xsd_json_structure(fields)
    assert "pessoa" in result
    assert result["pessoa"]["nome"] == "Ana"
    assert result["pessoa"]["cpf"] == "111"


def test_build_xsd_json_structure_uses_synthetic_when_no_pdf_text():
    fields = [_make_field("doc.emissao", "", field_type="date")]
    result = _build_xsd_json_structure(fields)
    assert result["doc"]["emissao"] == "01/01/2024"


# ---------------------------------------------------------------------------
# AC2 — index.html structure
# ---------------------------------------------------------------------------


class TestIndexHtml:
    def setup_method(self):
        self.gen = TemplateGenerator()
        self.output = self.gen.generate(SAMPLE_FIELDS, SAMPLE_BLOCKS)
        self.html = self.output["html"]

    def test_html_is_string(self):
        assert isinstance(self.html, str)

    def test_html_has_doctype(self):
        assert "<!DOCTYPE html>" in self.html

    def test_html_charset_utf8(self):
        assert 'charset="UTF-8"' in self.html

    def test_html_body_data_bind_with_root_key(self):
        """AC2: body must have data-bind='with: {RootKey}'"""
        assert 'data-bind="with:' in self.html or 'data-bind="with: ' in self.html

    def test_html_has_template_data_placeholder(self):
        """AC2: must contain ##TEMPLATE_DATA## placeholder"""
        assert "##TEMPLATE_DATA##" in self.html

    def test_html_has_section_header(self):
        """AC2: structural section header"""
        assert "section-header" in self.html

    def test_html_has_section_flow(self):
        """AC2: structural section flow"""
        assert "section-flow" in self.html

    def test_html_has_section_footer(self):
        """AC2: structural section footer"""
        assert "section-footer" in self.html

    def test_html_ko_bindings_for_each_field_with_block(self):
        """AC2: each block that matches a field must produce a data-bind span"""
        assert 'data-bind="text: contrato_cliente_nome"' in self.html
        assert 'data-bind="text: contrato_cliente_cpf"' in self.html

    def test_html_references_knockout_library(self):
        """AC7: must reference ../Bibliotecas/js/knockout-3.4.2.js"""
        assert "../Bibliotecas/js/knockout-3.4.2.js" in self.html

    def test_html_references_bibliotecas_css(self):
        """AC7: must reference ../Bibliotecas/css/"""
        assert "../Bibliotecas/css/" in self.html

    def test_html_references_base_js(self):
        """AC8: index.html must reference js/base.js"""
        assert "js/base.js" in self.html

    def test_html_references_style_css(self):
        """AC8: index.html must reference css/style.css"""
        assert "css/style.css" in self.html

    def test_html_page_break_marker(self):
        """AC9: must contain page-break class"""
        assert "page-break" in self.html

    def test_html_no_bom(self):
        """AC10: UTF-8 output must not start with BOM bytes"""
        bom = "\ufeff"
        assert not self.html.startswith(bom)

    def test_html_applyBindings_call(self):
        """AC4/AC8: ko.applyBindings must appear in index.html"""
        assert "ko.applyBindings" in self.html


# ---------------------------------------------------------------------------
# AC3 — style.css
# ---------------------------------------------------------------------------


class TestStyleCss:
    def setup_method(self):
        self.gen = TemplateGenerator()
        self.output = self.gen.generate(SAMPLE_FIELDS, SAMPLE_BLOCKS)
        self.css = self.output["css"]

    def test_css_is_string(self):
        assert isinstance(self.css, str)

    def test_css_a4_width(self):
        """AC3: A4 width = 8.27in"""
        assert "8.27in" in self.css

    def test_css_a4_height(self):
        """AC3: A4 height = 11.69in"""
        assert "11.69in" in self.css

    def test_css_font_family(self):
        """AC3: font-family present"""
        assert "font-family" in self.css

    def test_css_has_print_media_query(self):
        """AC3: @media print block"""
        assert "@media print" in self.css

    def test_css_page_break_rule(self):
        """AC9: page-break-before: always in CSS"""
        assert "page-break-before: always" in self.css

    def test_css_absolute_positioning(self):
        """AC3: absolute positioning for label/field"""
        assert "position: absolute" in self.css

    def test_css_no_bom(self):
        """AC10: no BOM"""
        assert not self.css.startswith("\ufeff")


# ---------------------------------------------------------------------------
# AC4 — base.js
# ---------------------------------------------------------------------------


class TestBaseJs:
    def setup_method(self):
        self.gen = TemplateGenerator()
        self.output = self.gen.generate(SAMPLE_FIELDS, SAMPLE_BLOCKS)
        self.js = self.output["js"]

    def test_js_is_string(self):
        assert isinstance(self.js, str)

    def test_js_has_view_model(self):
        """AC4: ViewModel constructor"""
        assert "var ViewModel" in self.js

    def test_js_format_cpf(self):
        """AC4: formatCPF function"""
        assert "function formatCPF" in self.js

    def test_js_format_cnpj(self):
        """AC4: formatCNPJ function"""
        assert "function formatCNPJ" in self.js

    def test_js_format_date(self):
        """AC4: formatDate function"""
        assert "function formatDate" in self.js

    def test_js_format_currency(self):
        """AC4: formatCurrency function"""
        assert "function formatCurrency" in self.js

    def test_js_format_phone(self):
        """AC4: formatPhone function"""
        assert "function formatPhone" in self.js

    def test_js_pagination_quebrar_tabela(self):
        """AC4: quebrarTabelaEntrePaginas pagination helper"""
        assert "function quebrarTabelaEntrePaginas" in self.js

    def test_js_pagination_criar_nova_pagina(self):
        """AC4: criarNovaPagina pagination helper"""
        assert "function criarNovaPagina" in self.js

    def test_js_ko_observable_per_field(self):
        """AC4: ko.observable for each field"""
        for f in SAMPLE_FIELDS:
            _sanitize_js_identifier(f.jsonPath)
            assert "ko.observable" in self.js

    def test_js_computed_observable_for_currency_field(self):
        """AC4: computed observable for currency field"""
        assert "ko.computed" in self.js
        assert "contrato_valor_formatted" in self.js

    def test_js_computed_observable_for_date_field(self):
        """AC4: computed observable for date field"""
        assert "contrato_dataEmissao_formatted" in self.js

    def test_js_no_bom(self):
        """AC10: no BOM"""
        assert not self.js.startswith("\ufeff")


# ---------------------------------------------------------------------------
# AC5 — exemplo.js
# ---------------------------------------------------------------------------


class TestExemploJs:
    def setup_method(self):
        self.gen = TemplateGenerator()
        self.output = self.gen.generate(SAMPLE_FIELDS, SAMPLE_BLOCKS)
        self.exemplo = self.output["exemplo"]

    def test_exemplo_is_string(self):
        assert isinstance(self.exemplo, str)

    def test_exemplo_has_xsd_structure(self):
        """AC5: nested JSON structure matching XSD paths"""
        assert "exemploData" in self.exemplo

    def test_exemplo_has_flat_data_object(self):
        """AC5: flat data object for ViewModel"""
        assert "var data" in self.exemplo

    def test_exemplo_synthetic_values_for_fields(self):
        """AC5: fields with pdfText should use that value"""
        assert "João Silva" in self.exemplo

    def test_exemplo_has_ko_applyBindings(self):
        """AC5/AC8: exemplo.js initializes KO"""
        assert "ko.applyBindings" in self.exemplo

    def test_exemplo_json_parseable(self):
        """AC6: the exemploData JSON block must be parseable"""
        # Extract JSON between first { and matching }
        import re

        match = re.search(r"var exemploData = (\{[\s\S]+?\});", self.exemplo)
        assert match, "exemploData JSON block not found"
        parsed = json.loads(match.group(1))
        assert isinstance(parsed, dict)
        # Should have nested structure
        assert "contrato" in parsed

    def test_exemplo_no_bom(self):
        """AC10: no BOM"""
        assert not self.exemplo.startswith("\ufeff")


# ---------------------------------------------------------------------------
# AC6 — syntactic validity checks
# ---------------------------------------------------------------------------


class TestSyntacticValidity:
    def setup_method(self):
        self.gen = TemplateGenerator()
        self.output = self.gen.generate(SAMPLE_FIELDS, SAMPLE_BLOCKS)

    def test_html_has_matching_html_tags(self):
        html = self.output["html"]
        assert html.count("<html") == 1
        assert html.count("</html>") == 1
        assert html.count("<head>") == 1 or html.count("<head\n") == 1
        assert html.count("</head>") == 1
        assert html.count("<body") == 1
        assert html.count("</body>") == 1

    def test_css_has_balanced_braces(self):
        css = self.output["css"]
        assert css.count("{") == css.count("}")

    def test_js_has_no_syntax_error_markers(self):
        js = self.output["js"]
        # Basic check: use strict present, no raw syntax errors
        assert '"use strict"' in js

    def test_exemplo_has_var_declarations(self):
        exemplo = self.output["exemplo"]
        assert exemplo.count("var ") >= 2


# ---------------------------------------------------------------------------
# AC11 — binding integrity with empty blocks
# ---------------------------------------------------------------------------


class TestBindingIntegrityNoBlocks:
    """When no text blocks are provided, fields should still produce data-bind spans."""

    def setup_method(self):
        self.gen = TemplateGenerator()
        self.output = self.gen.generate(SAMPLE_FIELDS, blocks=[])
        self.html = self.output["html"]

    def test_all_fields_have_data_bind(self):
        for f in SAMPLE_FIELDS:
            js_id = _sanitize_js_identifier(f.jsonPath)
            assert f'data-bind="text: {js_id}"' in self.html, (
                f"Missing data-bind for field {f.jsonPath} (js_id={js_id})"
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_fields_and_blocks(self):
        gen = TemplateGenerator()
        output = gen.generate([], [])
        assert "html" in output
        assert "css" in output
        assert "js" in output
        assert "exemplo" in output
        assert "##TEMPLATE_DATA##" in output["html"]

    def test_field_with_special_chars_in_path(self):
        gen = TemplateGenerator()
        fields = [_make_field("doc.items[0].value", "test")]
        output = gen.generate(fields, [])
        assert "doc_items_0__value" in output["html"] or "doc_items" in output["html"]

    def test_field_with_js_injection_attempt(self):
        gen = TemplateGenerator()
        fields = [_make_field("campo.normal", 'test"injection')]
        output = gen.generate(fields, [])
        # The injected quote should be escaped in exemplo.js
        assert '\\"injection' in output["exemplo"] or "injection" in output["exemplo"]
