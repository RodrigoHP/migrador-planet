import re
from typing import List

from models.field_mapping import FieldMapping
from models.text_block import TextBlock


def _sanitize_js_identifier(name: str) -> str:
    """Convert an arbitrary string to a valid JS identifier.

    Replaces non-alphanumeric characters (except underscore) with underscore.
    Prefixes with underscore if name starts with a digit.
    """
    ident = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if ident and ident[0].isdigit():
        ident = "_" + ident
    return ident or "_field"


class TemplateGenerator:
    """Generate HTML content + CSS + JS (Knockout.js) + example data from field mappings."""

    def generate(
        self,
        fields: List[FieldMapping],
        blocks: List[TextBlock],
    ) -> dict:
        """Return a dict with html (inner content only), css, js, and exemplo keys."""
        html_content = self._generate_content(fields, blocks)
        css = self._generate_css(blocks)
        js = self._generate_js(fields)
        exemplo = self._generate_exemplo(fields)
        return {"html": html_content, "css": css, "js": js, "exemplo": exemplo}

    # ------------------------------------------------------------------
    # Private generators
    # ------------------------------------------------------------------

    def _generate_content(self, fields: List[FieldMapping], blocks: List[TextBlock]) -> str:
        """Generate only the inner HTML spans — NOT a full document.

        The preview endpoint assembles the full HTML by injecting this content
        into base_template.html via the {content} placeholder.
        """
        field_by_path = {f.jsonPath: f for f in fields}
        field_paths = set(field_by_path.keys())

        items: List[str] = []
        for b in blocks:
            text = b.text.strip()
            matched_field: FieldMapping | None = None

            if text in field_paths:
                matched_field = field_by_path[text]
            else:
                for f in fields:
                    if f.jsonPath in text:
                        matched_field = f
                        break

            x_pct = f"{b.x * 100:.1f}"
            y_pct = f"{b.y * 100:.1f}"

            if matched_field is not None:
                js_id = _sanitize_js_identifier(matched_field.jsonPath)
                items.append(
                    f'<span class="field" '
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
                    f'<span class="label" '
                    f'style="left:{x_pct}%;top:{y_pct}%;">'
                    f'{safe_text}</span>'
                )

        return "\n".join(items)

    def _generate_css(self, blocks: List[TextBlock]) -> str:
        """Generate CSS with absolute positioning rules for the form container."""
        rules: List[str] = [
            "#form-container { position: relative; width: 100%; min-height: 1123px; }",
            ".label { position: absolute; font-size: 12px; color: #333; }",
            ".field { position: absolute; font-size: 12px; color: #000; "
            "border-bottom: 1px solid #999; min-width: 80px; }",
        ]
        return "\n".join(rules)

    def _generate_js(self, fields: List[FieldMapping]) -> str:
        """Generate Knockout.js ViewModel with ko.observable per field."""
        observables = "\n".join(
            f"  {_sanitize_js_identifier(f.jsonPath)}: ko.observable('{self._escape_js(f.pdfText)}'),"
            for f in fields
        )
        return (
            "var ViewModel = function() {\n"
            f"{observables}\n"
            "};\n"
            "ko.applyBindings(new ViewModel());"
        )

    def _generate_exemplo(self, fields: List[FieldMapping]) -> str:
        """Generate a JavaScript object with example data from pdfText values."""
        pairs = ", ".join(
            f'"{_sanitize_js_identifier(f.jsonPath)}": "{self._escape_js(f.pdfText)}"'
            for f in fields
        )
        return f"var exampleData = {{{pairs}}};"

    @staticmethod
    def _escape_js(value: str) -> str:
        """Minimal JS string escaping for single-quoted and double-quoted contexts."""
        return (
            value.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
