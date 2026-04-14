"""Tests for Story 48.5 — Stage 4: List Binding.

Covers:
- AC1: repeated_section → ListBinding (não FieldMappingEntry individuais)
- AC2: ListBinding com xsd_list_path, xsd_max_occurs, item_fields
- AC3: XSD nodes com is_array=True são detectados pelo _collect_array_nodes
- AC5: list_bindings adicionados ao context separadamente dos field_mappings escalares
"""

from __future__ import annotations

from typing import Any

import pytest

from models.pipeline_context import ListBinding
from services.stages.stage4_mapping.list_binding import (
    _build_list_binding,
    _collect_array_nodes,
    _extract_repeated_sections_from_trees,
    _fuzzy_match_array_node,
    run_list_binding,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures: field_tree de exemplo com nó array
# ---------------------------------------------------------------------------


def _make_field_tree_with_array() -> dict[str, Any]:
    """Field tree com Segurado como nó array."""
    return {
        "root_nodes": [
            {
                "name": "SubGrupo",
                "type": "complex",
                "is_array": False,
                "children": [
                    {
                        "name": "Segurados",
                        "type": "complex",
                        "is_array": False,
                        "children": [
                            {
                                "name": "Segurado",
                                "type": "complex",
                                "is_array": True,
                                "max_occurs": "unbounded",
                                "children": [
                                    {"name": "Nome", "type": "string", "is_array": False, "children": []},
                                    {"name": "CPF", "type": "string", "is_array": False, "children": []},
                                    {"name": "Plano", "type": "string", "is_array": False, "children": []},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _make_repeated_section_dict(
    section_id: str = "segurado_row",
    n: int = 5,
    cluster_id: str = "A",
) -> dict[str, Any]:
    """RepeatedSection como dict (resultado do model_dump())."""
    return {
        "section_id": section_id,
        "list_item_count": n,
        "instances": [
            {"bbox": [50, 100 + i * 30, 300, 120 + i * 30], "texts": [f"Item {i}"], "block_ids": [f"b{i}"]}
            for i in range(n)
        ],
        "item_template": {"fields": [{"name": "text_field", "field_type": "dynamic", "value": None}]},
        "page_index": 0,
        "bbox_envelope": [50, 100, 300, 250],
        "_cluster_id": cluster_id,
    }


# ---------------------------------------------------------------------------
# AC3 — _collect_array_nodes detecta nós is_array=True
# ---------------------------------------------------------------------------


def test_collect_array_nodes_finds_segurado():
    """Segurado (is_array=True) deve aparecer no resultado."""
    field_tree = _make_field_tree_with_array()
    array_nodes = _collect_array_nodes(field_tree)

    assert len(array_nodes) == 1
    assert array_nodes[0]["name"] == "Segurado"
    assert array_nodes[0]["_path"] == "SubGrupo.Segurados.Segurado"


def test_collect_array_nodes_empty_tree():
    """Field tree vazia → lista vazia."""
    assert _collect_array_nodes(None) == []
    assert _collect_array_nodes({}) == []


def test_collect_array_nodes_no_arrays():
    """Tree sem is_array=True → lista vazia."""
    field_tree = {
        "root_nodes": [
            {
                "name": "Root",
                "type": "complex",
                "is_array": False,
                "children": [{"name": "Field", "type": "string", "is_array": False, "children": []}],
            }
        ]
    }
    assert _collect_array_nodes(field_tree) == []


# ---------------------------------------------------------------------------
# Fuzzy match
# ---------------------------------------------------------------------------


def test_fuzzy_match_finds_segurado():
    """section_id='segurado_row' deve fazer match com 'Segurado'."""
    field_tree = _make_field_tree_with_array()
    array_nodes = _collect_array_nodes(field_tree)

    matched = _fuzzy_match_array_node("segurado_row", array_nodes)
    assert matched is not None
    assert matched["name"] == "Segurado"


def test_fuzzy_match_empty_nodes():
    """Sem nós array → retorna None."""
    result = _fuzzy_match_array_node("qualquer", [])
    assert result is None


# ---------------------------------------------------------------------------
# AC1, AC2 — _build_list_binding gera ListBinding correto
# ---------------------------------------------------------------------------


def test_build_list_binding_with_xsd():
    """Com XSD disponível: ListBinding com xsd_list_path e item_fields."""
    rs = _make_repeated_section_dict(section_id="Segurado", n=3)
    field_tree = _make_field_tree_with_array()
    array_nodes = _collect_array_nodes(field_tree)

    lb = _build_list_binding(rs, field_tree, array_nodes)

    assert isinstance(lb, ListBinding)
    assert lb.section_id == "Segurado"
    assert lb.xsd_list_path == "SubGrupo.Segurados.Segurado"
    assert lb.xsd_max_occurs == "unbounded"
    assert lb.list_item_count == 3
    assert lb.binding_type == "list"
    # item_fields deve conter Nome, CPF, Plano
    field_names = {f.name for f in lb.item_fields}
    assert "Nome" in field_names
    assert "CPF" in field_names
    assert "Plano" in field_names


def test_build_list_binding_without_xsd():
    """Sem XSD: ListBinding com xsd_list_path vazio e confidence baixa."""
    rs = _make_repeated_section_dict(n=5)
    lb = _build_list_binding(rs, None, [])

    assert isinstance(lb, ListBinding)
    assert lb.xsd_list_path == ""
    assert lb.confidence < 0.5
    assert lb.list_item_count == 5
    assert lb.binding_type == "list"


# ---------------------------------------------------------------------------
# _extract_repeated_sections_from_trees
# ---------------------------------------------------------------------------


def test_extract_from_document_trees_with_repeated_sections_key():
    """document_trees com 'repeated_sections' key → extrai corretamente."""
    rs1 = _make_repeated_section_dict("rs-001", n=3, cluster_id="A")
    rs2 = _make_repeated_section_dict("rs-002", n=5, cluster_id="A")
    document_trees = {
        "A": {
            "cluster_id": "A",
            "repeated_sections": [rs1, rs2],
            "tree": {},
        }
    }

    result = _extract_repeated_sections_from_trees(document_trees)
    section_ids = {r["section_id"] for r in result}
    assert "rs-001" in section_ids
    assert "rs-002" in section_ids


def test_extract_from_empty_trees():
    """Trees sem repeated_sections → lista vazia."""
    document_trees = {"A": {"cluster_id": "A", "tree": {}}}
    result = _extract_repeated_sections_from_trees(document_trees)
    assert result == []


# ---------------------------------------------------------------------------
# AC5 — run_list_binding integração
# ---------------------------------------------------------------------------


def test_run_list_binding_returns_list_bindings():
    """run_list_binding deve retornar list[ListBinding]."""
    rs = _make_repeated_section_dict("Segurado", n=4)
    document_trees = {"A": {"cluster_id": "A", "repeated_sections": [rs], "tree": {}}}
    field_tree = _make_field_tree_with_array()

    bindings = run_list_binding(document_trees, field_tree)

    assert len(bindings) == 1
    assert isinstance(bindings[0], ListBinding)
    assert bindings[0].list_item_count == 4


def test_run_list_binding_empty_trees():
    """Trees sem repeated_sections → lista vazia."""
    result = run_list_binding({}, None)
    assert result == []


def test_run_list_binding_no_xsd():
    """Sem XSD: retorna ListBinding com xsd_list_path vazio."""
    rs = _make_repeated_section_dict("items", n=2)
    document_trees = {"A": {"repeated_sections": [rs], "tree": {}}}

    bindings = run_list_binding(document_trees, None)
    assert len(bindings) == 1
    assert bindings[0].xsd_list_path == ""


def test_list_binding_model_dump_has_binding_type():
    """model_dump() do ListBinding deve incluir binding_type='list' para o frontend."""
    lb = ListBinding(
        section_id="test",
        xsd_list_path="Root.Items.Item",
        xsd_max_occurs="unbounded",
        list_item_count=3,
    )
    dumped = lb.model_dump()
    assert dumped["binding_type"] == "list"
    assert dumped["xsd_list_path"] == "Root.Items.Item"
    assert dumped["list_item_count"] == 3
