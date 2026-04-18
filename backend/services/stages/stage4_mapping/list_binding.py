"""Stage 4 — List Binding sub-module (Story 48.5).

Processa nós `repeated_section` do document tree e gera ListBinding:
seção repetida → XSD nó com maxOccurs > 1.

Fluxo:
  1. Extrair repeated_sections dos document_trees
  2. Para cada repeated_section, localizar nó XSD com is_array=True
     via fuzzy match do section_id / field names
  3. Criar ListBinding com xsd_list_path e item_fields

Sem XSD: ListBinding criado com xsd_list_path vazio (fallback manual).
"""

from __future__ import annotations

import difflib
import logging
from typing import Any

from models.pipeline_context import FieldMappingEntry, ListBinding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: navegação do field_tree
# ---------------------------------------------------------------------------


def _collect_array_nodes(field_tree: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extrai todos os nós com is_array=True do field_tree."""
    if not field_tree:
        return []
    result: list[dict[str, Any]] = []

    def _walk(nodes: list[dict[str, Any]], prefix: str) -> None:
        for node in nodes:
            node_name = node.get("name", "")
            path = f"{prefix}.{node_name}" if prefix else node_name
            if node.get("is_array"):
                result.append({**node, "_path": path})
            _walk(node.get("children", []), path)

    _walk(field_tree.get("root_nodes", []), "")
    return result


def _children_of_node(field_tree: dict[str, Any] | None, array_path: str) -> list[dict[str, Any]]:
    """Retorna os filhos (item fields) de um nó XSD array pelo seu path."""
    if not field_tree:
        return []
    parts = array_path.split(".")

    def _find(nodes: list[dict[str, Any]], depth: int) -> list[dict[str, Any]] | None:
        for node in nodes:
            if node.get("name") == parts[depth]:
                if depth == len(parts) - 1:
                    return node.get("children", []) or []
                return _find(node.get("children", []) or [], depth + 1)
        return None

    return _find(field_tree.get("root_nodes", []), 0) or []


def _fuzzy_match_array_node(
    section_id: str,
    array_nodes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Encontra o nó XSD array mais similar ao section_id via fuzzy match."""
    if not array_nodes:
        return None

    best_score = 0.0
    best_node = None

    sid_lower = section_id.lower()
    for node in array_nodes:
        node_name = node.get("name", "").lower()
        node_path = node.get("_path", "").lower()

        score = max(
            difflib.SequenceMatcher(None, sid_lower, node_name).ratio(),
            difflib.SequenceMatcher(None, sid_lower, node_path).ratio(),
        )
        if score > best_score:
            best_score = score
            best_node = node

    if best_score < 0.1:
        return None
    return best_node


# ---------------------------------------------------------------------------
# Extração de repeated_sections dos document_trees
# ---------------------------------------------------------------------------


def _extract_repeated_sections_from_trees(
    document_trees: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extrai todos os nós repeated_section dos document_trees.

    document_trees é cluster_id → tree_dict (com 'tree', 'repeated_sections', etc.)
    """
    all_sections: list[dict[str, Any]] = []

    for cluster_id, tree_entry in document_trees.items():
        # repeated_sections podem estar no tree_entry diretamente (adicionados pelo tree_builder)
        repeated = tree_entry.get("repeated_sections", [])
        for rs in repeated:
            all_sections.append({**rs, "_cluster_id": cluster_id})

        # Ou podem estar como nós dentro da árvore (buscar nodes type="repeated_section")
        tree = tree_entry.get("tree", tree_entry)
        if isinstance(tree, dict):
            _scan_tree_for_repeated(tree, cluster_id, all_sections)

    # Deduplicar por section_id
    seen: set[str] = set()
    deduped = []
    for rs in all_sections:
        sid = rs.get("section_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            deduped.append(rs)

    return deduped


def _scan_tree_for_repeated(
    node: dict[str, Any],
    cluster_id: str,
    result: list[dict[str, Any]],
) -> None:
    """Recursivamente escaneia a árvore por nós type='repeated_section'."""
    if node.get("type") == "repeated_section":
        result.append({**node, "_cluster_id": cluster_id})
    for child in node.get("children", []):
        if isinstance(child, dict):
            _scan_tree_for_repeated(child, cluster_id, result)


# ---------------------------------------------------------------------------
# Core: gerar ListBinding para uma repeated_section
# ---------------------------------------------------------------------------


def _build_list_binding(
    rs: dict[str, Any],
    field_tree: dict[str, Any] | None,
    array_nodes: list[dict[str, Any]],
) -> ListBinding:
    """Cria um ListBinding para uma repeated_section."""
    section_id = rs.get("section_id", rs.get("id", "unknown"))
    cluster_id = rs.get("_cluster_id", "")
    instances = rs.get("instances", [])
    list_item_count = rs.get("list_item_count", len(instances))

    # Tentar localizar nó XSD array pelo fuzzy match
    matched_node = _fuzzy_match_array_node(section_id, array_nodes)
    xsd_list_path = ""
    xsd_max_occurs = "unbounded"
    item_fields: list[FieldMappingEntry] = []

    if matched_node:
        xsd_list_path = matched_node.get("_path", "")
        xsd_max_occurs = str(matched_node.get("max_occurs", "unbounded"))
        confidence = 0.6  # confiança moderada para match heurístico

        # Gerar item_fields para cada filho do nó XSD array
        children = _children_of_node(field_tree, xsd_list_path)
        for child in children:
            child_name = child.get("name", "")
            child_path = f"{xsd_list_path}.{child_name}"
            item_fields.append(
                FieldMappingEntry(
                    block_id="",  # será populado pelo Stage 5 ou editor
                    layout_type_id=cluster_id,
                    pdf_text="",
                    xsd_field_path=child_path,
                    xsd_type=child.get("type"),
                    confidence=0.5,
                    name=child_name,
                    path=child_path,
                    status="unmapped",
                )
            )
    else:
        confidence = 0.2  # baixa confiança — sem match XSD

    logger.debug(
        "ListBinding: section=%s → xsd=%s (confidence=%.2f, items=%d)",
        section_id,
        xsd_list_path or "(sem match XSD)",
        confidence,
        list_item_count,
    )

    return ListBinding(
        section_id=section_id,
        xsd_list_path=xsd_list_path,
        xsd_max_occurs=xsd_max_occurs,
        item_fields=item_fields,
        confidence=confidence,
        list_item_count=list_item_count,
        layout_type_id=cluster_id,
    )


# ---------------------------------------------------------------------------
# Entry point: Step 4.5b
# ---------------------------------------------------------------------------


def run_list_binding(
    document_trees: dict[str, dict[str, Any]],
    field_tree: dict[str, Any] | None,
) -> list[ListBinding]:
    """Step 4.5b — Gera ListBinding para todos os repeated_sections dos trees.

    Parameters
    ----------
    document_trees:
        Dict cluster_id → tree_entry (com 'repeated_sections' e 'tree').
    field_tree:
        XSD field_tree dict (pode ser None se XSD não disponível).

    Returns
    -------
    list[ListBinding]:
        Um ListBinding por repeated_section detectado.
    """
    repeated_sections = _extract_repeated_sections_from_trees(document_trees)

    if not repeated_sections:
        return []

    array_nodes = _collect_array_nodes(field_tree)

    logger.info(
        "Step 4.5b List Binding: %d seção(ões) repetida(s), %d nó(s) XSD array",
        len(repeated_sections),
        len(array_nodes),
    )

    bindings: list[ListBinding] = []
    for rs in repeated_sections:
        lb = _build_list_binding(rs, field_tree, array_nodes)
        bindings.append(lb)

    return bindings
