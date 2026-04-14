"""Unit tests for Story 48.6 — Stage 5: Loop Rendering.

Covers:
- AC1: ListBinding → <repeat data-list="..." data-count="N">
- AC2: Campos dinâmicos como {{NomeCampo}}
- AC3: Campos estáticos como <span class="static">
- AC4: CSS inclui repeat e .repeat-item
- AC5: coverage_score inclui list_binding_count
"""

from __future__ import annotations

from typing import Any

import pytest

from models.pipeline_context import LayoutTypeInfo
from services.stages.stage5_template.html_helpers import _BASE_CSS_RESET
from services.stages.stage5_template.html_tree import _render_repeat_element

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_layout() -> LayoutTypeInfo:
    return LayoutTypeInfo(
        id="A",
        cluster_id="A",
        name="Test Layout",
        page_width_pts=595.0,
        page_height_pts=842.0,
    )


def _make_repeated_section_node(
    section_id: str = "repeated_abc",
    n: int = 3,
    text: str = "JOAO DA SILVA",
    bbox: list[float] | None = None,
) -> dict[str, Any]:
    """Simula um nó repeated_section do document tree."""
    children = [
        {
            "type": "list_item",
            "bbox": [50, 100 + i * 30, 300, 120 + i * 30],
            "text": f"{text} {i + 1}",
        }
        for i in range(n)
    ]
    return {
        "id": section_id,
        "type": "repeated_section",
        "name": f"list_{n}_items",
        "bbox": bbox or [50.0, 100.0, 300.0, 200.0],
        "children": children,
    }


# ---------------------------------------------------------------------------
# AC1 — <repeat> com data-list e data-count
# ---------------------------------------------------------------------------


def test_render_repeat_has_repeat_tag():
    """Resultado deve conter a tag <repeat>."""
    node = _make_repeated_section_node(n=4)
    html = _render_repeat_element(node, {}, None, _make_layout())
    assert "<repeat" in html
    assert "</repeat>" in html


def test_render_repeat_has_data_count():
    """data-count deve refletir o número de instâncias."""
    node = _make_repeated_section_node(n=5)
    html = _render_repeat_element(node, {}, None, _make_layout())
    assert 'data-count="5"' in html


def test_render_repeat_has_data_list_attr():
    """data-list deve estar presente (mesmo que vazio quando sem XSD path)."""
    node = _make_repeated_section_node()
    html = _render_repeat_element(node, {}, None, _make_layout())
    assert "data-list=" in html


def test_render_repeat_has_section_id():
    """data-section-id deve identificar a seção."""
    node = _make_repeated_section_node(section_id="segurado_row")
    html = _render_repeat_element(node, {}, None, _make_layout())
    assert 'data-section-id="segurado_row"' in html


# ---------------------------------------------------------------------------
# AC2 — Campos dinâmicos como {{NomeCampo}}
# ---------------------------------------------------------------------------


def test_render_repeat_has_mustache_field():
    """Item deve conter placeholder {{...}} para campo dinâmico."""
    node = _make_repeated_section_node(text="JOAO DA SILVA")
    html = _render_repeat_element(node, {}, None, _make_layout())
    # Deve ter alguma forma de placeholder de campo
    assert "{{" in html or 'class="dynamic"' in html


# ---------------------------------------------------------------------------
# AC3 — Campos estáticos como <span class="static">
# ---------------------------------------------------------------------------


def test_render_repeat_item_div():
    """Deve ter div com class='repeat-item' dentro do <repeat>."""
    node = _make_repeated_section_node(n=3)
    html = _render_repeat_element(node, {}, None, _make_layout())
    assert 'class="repeat-item"' in html


# ---------------------------------------------------------------------------
# AC4 — CSS inclui repeat e .repeat-item
# ---------------------------------------------------------------------------


def test_base_css_has_repeat_styles():
    """_BASE_CSS_RESET deve incluir regras para 'repeat' e '.repeat-item'."""
    assert "repeat {" in _BASE_CSS_RESET or "repeat{" in _BASE_CSS_RESET
    assert ".repeat-item {" in _BASE_CSS_RESET or ".repeat-item{" in _BASE_CSS_RESET


# ---------------------------------------------------------------------------
# AC5 — coverage_score com list_binding_count
# ---------------------------------------------------------------------------


def test_coverage_with_list_bindings():
    """_step_5_3_coverage com list_bindings deve incluir 'lists' no resultado."""
    from services.stages.stage5_template.coverage_overlay import _step_5_3_coverage

    layout = _make_layout()
    tree_with_repeated = {
        "id": "root-A",
        "type": "document",
        "children": [
            {
                "type": "page",
                "children": [
                    {
                        "type": "repeated_section",
                        "children": [],
                    }
                ],
            }
        ],
    }
    document_trees = {"A": {"tree": tree_with_repeated}}
    list_bindings = [{"layout_type_id": "A", "section_id": "rs-1", "xsd_list_path": "Root.Items.Item"}]

    coverage = _step_5_3_coverage(
        field_mappings=[],
        field_tree=None,
        document_trees=document_trees,
        layout_types=[layout],
        list_bindings=list_bindings,
    )

    assert "A" in coverage
    assert "lists" in coverage["A"]
    assert coverage["A"]["lists"]["list_binding_count"] == 1


def test_coverage_without_list_bindings():
    """Sem repeated_sections → lists.total=0, percentagem normal."""
    from services.stages.stage5_template.coverage_overlay import _step_5_3_coverage

    layout = _make_layout()
    coverage = _step_5_3_coverage(
        field_mappings=[],
        field_tree=None,
        document_trees={},
        layout_types=[layout],
        list_bindings=[],
    )

    assert "A" in coverage
    # Deve ainda ter a chave 'lists'
    assert "lists" in coverage["A"]
    assert coverage["A"]["lists"]["total"] == 0


def test_coverage_percentage_capped_at_100():
    """coverage percentage nunca deve ultrapassar 100."""
    from services.stages.stage5_template.coverage_overlay import _step_5_3_coverage

    layout = _make_layout()
    # Muitos list_bindings para um template que não tem campos escalares
    list_bindings = [{"layout_type_id": "A", "section_id": f"rs-{i}", "xsd_list_path": "Foo"} for i in range(100)]

    coverage = _step_5_3_coverage(
        field_mappings=[],
        field_tree=None,
        document_trees={},
        layout_types=[layout],
        list_bindings=list_bindings,
    )
    assert coverage["A"]["percentage"] <= 100
