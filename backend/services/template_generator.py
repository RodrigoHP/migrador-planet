"""Template generator — Story 8.1.

Generates four output files from FieldMapping state:
  - index.html  : full document with KO bindings, ##TEMPLATE_DATA## placeholder
  - css/style.css : A4 dimensions, font styles, CSS Grid / absolute positioning, @media print
  - js/base.js  : ko.applyBindings(), BR format functions, pagination helpers, computed observables
  - js/exemplo.js : synthetic JSON data matching the XSD structure

All outputs are UTF-8 without BOM.
"""

from __future__ import annotations

import json
import re
from textwrap import dedent
from typing import Dict, List, Optional

from models.field_mapping import FieldMapping
from models.text_block import TextBlock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_js_identifier(name: str) -> str:
    """Convert an arbitrary string to a valid JS identifier.

    Replaces non-alphanumeric characters (except underscore) with underscore.
    Prefixes with underscore if name starts with a digit.
    """
    ident = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if ident and ident[0].isdigit():
        ident = "_" + ident
    return ident or "_field"


def _escape_js(value: str) -> str:
    """Minimal JS string escaping for double-quoted contexts."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _detect_root_key(fields: List[FieldMapping]) -> str:
    """Infer the root object key from the first segment of jsonPath fields."""
    counts: Dict[str, int] = {}
    for f in fields:
        if f.jsonPath:
            segment = f.jsonPath.split(".")[0].split("[")[0]
            if segment:
                counts[segment] = counts.get(segment, 0) + 1
    if not counts:
        return "dados"
    return max(counts, key=lambda k: counts[k])


def _build_xsd_json_structure(fields: List[FieldMapping]) -> dict:
    """Build a nested dict representing XSD paths with synthetic values."""
    root: dict = {}
    for f in fields:
        path = f.jsonPath
        if not path:
            continue
        # Remove array notation for structure building
        segments = re.sub(r"\[\d*\]", "", path).split(".")
        node = root
        for seg in segments[:-1]:
            if seg:
                node = node.setdefault(seg, {})
        leaf = segments[-1]
        if leaf:
            value = f.pdfText if f.pdfText else _synthetic_value(f)
            node[leaf] = value
    return root


def _synthetic_value(f: FieldMapping) -> str:
    """Return a plausible synthetic value for a field based on its type."""
    type_map = {
        "date": "01/01/2024",
        "currency": "1.234,56",
        "list": "Item 1",
        "composite": "Valor composto",
    }
    return type_map.get(f.type, f"exemplo_{_sanitize_js_identifier(f.jsonPath)}")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class TemplateGenerator:
    """Generate index.html, style.css, base.js and exemplo.js from field mappings."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        fields: List[FieldMapping],
        blocks: List[TextBlock],
    ) -> dict:
        """Return a dict with html, css, js, and exemplo keys.

        Keys mirror the four output files:
          html    -> index.html content
          css     -> css/style.css content
          js      -> js/base.js content
          exemplo -> js/exemplo.js content
        """
        root_key = _detect_root_key(fields)
        html = self._generate_index_html(fields, blocks, root_key)
        css = self._generate_css(blocks)
        js = self._generate_base_js(fields)
        exemplo = self._generate_exemplo_js(fields)
        return {"html": html, "css": css, "js": js, "exemplo": exemplo}

    # ------------------------------------------------------------------
    # index.html
    # ------------------------------------------------------------------

    def _generate_index_html(
        self,
        fields: List[FieldMapping],
        blocks: List[TextBlock],
        root_key: str,
    ) -> str:
        """Generate a complete standalone index.html document (UTF-8 no BOM)."""
        bindings_html = self._build_bindings_html(fields, blocks)
        return dedent(f"""\
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>Template Migrado</title>
              <link rel="stylesheet" href="../Bibliotecas/css/reset.css">
              <link rel="stylesheet" href="css/style.css">
            </head>
            <body data-bind="with: {root_key}">
              <!-- HEADER -->
              <div class="section section-header">
            {bindings_html}
              </div>
              <!-- FLOW -->
              <div class="section section-flow">
              </div>
              <!-- FOOTER -->
              <div class="section section-footer">
              </div>
              <!-- page break marker -->
              <div class="page-break"></div>

              <script src="../Bibliotecas/js/knockout-3.4.2.js"></script>
              <script src="js/base.js"></script>
              <script>
            var data = ##TEMPLATE_DATA##;
            ko.applyBindings(new ViewModel(data));
              </script>
            </body>
            </html>
        """)

    def _build_bindings_html(
        self,
        fields: List[FieldMapping],
        blocks: List[TextBlock],
    ) -> str:
        """Build inner HTML spans with KO data-bind attributes."""
        field_by_path = {f.jsonPath: f for f in fields}
        field_paths = set(field_by_path.keys())
        items: List[str] = []

        for b in blocks:
            text = b.text.strip()
            matched_field: Optional[FieldMapping] = None

            if text in field_paths:
                matched_field = field_by_path[text]
            else:
                for f in fields:
                    if f.jsonPath and f.jsonPath in text:
                        matched_field = f
                        break

            x_pct = f"{b.x * 100:.1f}"
            y_pct = f"{b.y * 100:.1f}"

            if matched_field is not None:
                js_id = _sanitize_js_identifier(matched_field.jsonPath)
                items.append(
                    f'    <span class="field" '
                    f'style="left:{x_pct}%;top:{y_pct}%;" '
                    f'data-bind="text: {js_id}"></span>'
                )
            else:
                safe_text = (
                    text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                items.append(
                    f'    <span class="label" '
                    f'style="left:{x_pct}%;top:{y_pct}%;">'
                    f"{safe_text}</span>"
                )

        # When there are no blocks, generate field spans directly from fields
        if not blocks:
            for f in fields:
                js_id = _sanitize_js_identifier(f.jsonPath)
                items.append(
                    f'    <span class="field" data-bind="text: {js_id}"></span>'
                )

        return "\n".join(items)

    # ------------------------------------------------------------------
    # css/style.css
    # ------------------------------------------------------------------

    def _generate_css(self, blocks: List[TextBlock]) -> str:
        """Generate A4 CSS with print media query."""
        return dedent("""\
            /* ============================================================
               style.css — gerado automaticamente pelo Migrador Planet
               Encoding: UTF-8
               ============================================================ */

            /* Reset */
            *, *::before, *::after {
              box-sizing: border-box;
              margin: 0;
              padding: 0;
            }

            /* A4 page container */
            .page,
            body {
              width: 8.27in;
              min-height: 11.69in;
              background: #ffffff;
              font-family: Arial, Helvetica, sans-serif;
              font-size: 12pt;
              color: #000000;
            }

            /* Structural sections */
            .section {
              position: relative;
              width: 100%;
            }

            .section-header {
              padding: 12pt 14pt 8pt 14pt;
              border-bottom: 1px solid #cccccc;
            }

            .section-flow {
              padding: 8pt 14pt;
            }

            .section-footer {
              padding: 8pt 14pt;
              border-top: 1px solid #cccccc;
              font-size: 9pt;
              color: #555555;
            }

            /* Field and label spans */
            #form-container {
              position: relative;
              width: 100%;
              min-height: 1123px;
            }

            .label {
              position: absolute;
              font-size: 10pt;
              color: #333333;
            }

            .field {
              position: absolute;
              font-size: 10pt;
              color: #000000;
              border-bottom: 1px solid #999999;
              min-width: 80px;
            }

            /* Page break */
            .page-break {
              page-break-before: always;
              break-before: page;
            }

            /* Print styles */
            @media print {
              html, body {
                width: 8.27in;
                height: 11.69in;
                margin: 0;
                padding: 0;
              }

              .page-break {
                page-break-before: always;
                break-before: page;
              }

              .section-header,
              .section-footer {
                position: running(header);
              }

              a {
                text-decoration: none;
                color: inherit;
              }
            }
        """)

    # ------------------------------------------------------------------
    # js/base.js
    # ------------------------------------------------------------------

    def _generate_base_js(self, fields: List[FieldMapping]) -> str:
        """Generate base.js with BR format functions, pagination helpers, ViewModel."""
        observables_lines = "\n".join(
            f"    self.{_sanitize_js_identifier(f.jsonPath)} = "
            f'ko.observable(data ? data["{_sanitize_js_identifier(f.jsonPath)}"] || "" : "");'
            for f in fields
        )

        computed_lines = "\n".join(
            self._make_computed(f) for f in fields if f.type in ("date", "currency")
        )

        return dedent(f"""\
            /* ============================================================
               base.js — gerado automaticamente pelo Migrador Planet
               Knockout.js 3.4.2  |  ../Bibliotecas/js/knockout-3.4.2.js
               Encoding: UTF-8
               ============================================================ */
            "use strict";

            /* ----------------------------------------------------------
               Funções de formatação BR
               ---------------------------------------------------------- */

            function formatCPF(value) {{
              var s = String(value || "").replace(/\\D/g, "");
              if (s.length !== 11) return value;
              return s.replace(/(\\d{{3}})(\\d{{3}})(\\d{{3}})(\\d{{2}})/, "$1.$2.$3-$4");
            }}

            function formatCNPJ(value) {{
              var s = String(value || "").replace(/\\D/g, "");
              if (s.length !== 14) return value;
              return s.replace(/(\\d{{2}})(\\d{{3}})(\\d{{3}})(\\d{{4}})(\\d{{2}})/, "$1.$2.$3/$4-$5");
            }}

            function formatDate(value) {{
              if (!value) return "";
              var d = new Date(value);
              if (isNaN(d.getTime())) return value;
              var day   = String(d.getDate()).padStart(2, "0");
              var month = String(d.getMonth() + 1).padStart(2, "0");
              var year  = d.getFullYear();
              return day + "/" + month + "/" + year;
            }}

            function formatCurrency(value) {{
              var n = parseFloat(String(value || "0").replace(",", "."));
              if (isNaN(n)) return value;
              return n.toLocaleString("pt-BR", {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            }}

            function formatPhone(value) {{
              var s = String(value || "").replace(/\\D/g, "");
              if (s.length === 11) {{
                return s.replace(/(\\d{{2}})(\\d{{5}})(\\d{{4}})/, "($1) $2-$3");
              }}
              if (s.length === 10) {{
                return s.replace(/(\\d{{2}})(\\d{{4}})(\\d{{4}})/, "($1) $2-$3");
              }}
              return value;
            }}

            /* ----------------------------------------------------------
               Funções de paginação
               ---------------------------------------------------------- */

            function criarNovaPagina(container) {{
              var pagina = document.createElement("div");
              pagina.className = "page";
              pagina.style.pageBreakBefore = "always";
              if (container) {{
                container.appendChild(pagina);
              }}
              return pagina;
            }}

            function quebrarTabelaEntrePaginas(tabelaEl, alturaMaxPagina) {{
              if (!tabelaEl) return;
              var linhas = tabelaEl.querySelectorAll("tr");
              var alturaAcumulada = 0;
              alturaMaxPagina = alturaMaxPagina || 900;
              for (var i = 0; i < linhas.length; i++) {{
                alturaAcumulada += linhas[i].offsetHeight || 24;
                if (alturaAcumulada > alturaMaxPagina) {{
                  linhas[i].style.pageBreakBefore = "always";
                  alturaAcumulada = 0;
                }}
              }}
            }}

            /* ----------------------------------------------------------
               ViewModel Knockout.js
               ---------------------------------------------------------- */

            var ViewModel = function(data) {{
              var self = this;
              data = data || {{}};

            {observables_lines}

            {computed_lines}
            }};
        """)

    def _make_computed(self, f: FieldMapping) -> str:
        js_id = _sanitize_js_identifier(f.jsonPath)
        if f.type == "date":
            return (
                f"    self.{js_id}_formatted = ko.computed(function() {{\n"
                f"      return formatDate(self.{js_id}());\n"
                f"    }});"
            )
        if f.type == "currency":
            return (
                f"    self.{js_id}_formatted = ko.computed(function() {{\n"
                f"      return formatCurrency(self.{js_id}());\n"
                f"    }});"
            )
        return ""

    # ------------------------------------------------------------------
    # js/exemplo.js
    # ------------------------------------------------------------------

    def _generate_exemplo_js(self, fields: List[FieldMapping]) -> str:
        """Generate exemplo.js with synthetic JSON data and ko.applyBindings call."""
        structure = _build_xsd_json_structure(fields)
        json_str = json.dumps(structure, ensure_ascii=False, indent=2)

        # Also build flat object for legacy ViewModel usage
        flat_pairs: List[str] = []
        for f in fields:
            if f.jsonPath:
                js_id = _sanitize_js_identifier(f.jsonPath)
                value = _escape_js(f.pdfText if f.pdfText else _synthetic_value(f))
                flat_pairs.append(f'  "{js_id}": "{value}"')
        flat_obj = "{\n" + ",\n".join(flat_pairs) + "\n}" if flat_pairs else "{}"

        return dedent(f"""\
            /* ============================================================
               exemplo.js — gerado automaticamente pelo Migrador Planet
               Dados sintéticos para renderização standalone de index.html
               Encoding: UTF-8
               ============================================================ */

            /* Estrutura XSD aninhada */
            var exemploData = {json_str};

            /* Objeto plano compatível com ViewModel */
            var data = {flat_obj};

            /* Inicializa KO com dados de exemplo */
            if (typeof ko !== "undefined" && typeof ViewModel !== "undefined") {{
              ko.applyBindings(new ViewModel(data));
            }}
        """)
