"""Stage 4 — Field Mapping (Batch LLM + Two-Pass + Section Scoping).

Story 13.8 — Maps PDF fields to XSD paths via batch LLM, section scoping,
two-pass disambiguation, and heuristic confidence scoring.

7 sub-steps:
  4.1 XSD Parsing (lxml — reuses xsd_parser.py)
  4.2 Pair Validation (consume Stage 3.3 field_pair, pair remaining)
  4.3 Format Pre-Detection (regex BEFORE matching — enriches LLM prompt)
  4.4 Section-XSD Matching (fuzzy match sections to XSD complex nodes)
  4.5 Batch Field Matching (1 Gemini Flash call per layout, two-pass)
  4.6 Confidence Scoring (5 heuristic factors, per-layout)
  4.7 Consistency Validation (orphans, unmapped required, type-format)

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 7b
Output contract: Section 3.4
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import re
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"
AMBIGUITY_THRESHOLD = 0.1
HIGH_CONFIDENCE_THRESHOLD = 0.7
SECTION_MATCH_MIN_SCORE = 0.3

# Confidence scoring weights (5 factors — names per contract 3.4)
WEIGHTS = {
    "layout_stability": 0.25,
    "anchor_detection": 0.15,
    "grid_quality": 0.20,
    "field_variability": 0.25,
    "vision_agreement": 0.15,
}

THRESHOLD_APPROVED = 0.95
THRESHOLD_REVIEW = 0.80

# ---------------------------------------------------------------------------
# Format detection patterns (reused from format_detection.py)
# ---------------------------------------------------------------------------

_FORMAT_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("currency_brl", re.compile(r"^R\$\s?[\d.,]+$")),
    ("date_numeric", re.compile(r"^\d{2}/\d{2}/\d{4}$")),
    ("date_extenso", re.compile(
        r"^\d{1,2}\s+de\s+"
        r"(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
        r"\s+de\s+\d{4}$",
        re.IGNORECASE,
    )),
    ("cpf", re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")),
    ("cnpj", re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")),
    ("phone", re.compile(r"^\(\d{2}\)\s?\d{4,5}-\d{4}$")),
    ("cep", re.compile(r"^\d{5}-?\d{3}$")),
    ("percentage", re.compile(r"^[\d.,]+\s?%$")),
]

_JS_FUNCTIONS: Dict[str, str] = {
    "currency_brl": (
        "function formatCurrency(v) { "
        "var n = parseFloat(String(v).replace(/R\\$\\s?/, '').replace(/\\./g, '').replace(',', '.')); "
        "return 'R$ ' + n.toFixed(2).replace('.', ',').replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.'); "
        "}"
    ),
    "date_numeric": (
        "function formatDate(v) { "
        "var p = String(v).split('/'); "
        "if (p.length === 3) return p[0] + '/' + p[1] + '/' + p[2]; "
        "return v; "
        "}"
    ),
    "cpf": (
        "function formatCPF(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "return d.replace(/(\\d{3})(\\d{3})(\\d{3})(\\d{2})/, '$1.$2.$3-$4'); "
        "}"
    ),
    "cnpj": (
        "function formatCNPJ(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "return d.replace(/(\\d{2})(\\d{3})(\\d{3})(\\d{4})(\\d{2})/, '$1.$2.$3/$4-$5'); "
        "}"
    ),
    "phone": (
        "function formatPhone(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "if (d.length === 11) return '(' + d.slice(0,2) + ') ' + d.slice(2,7) + '-' + d.slice(7); "
        "if (d.length === 10) return '(' + d.slice(0,2) + ') ' + d.slice(2,6) + '-' + d.slice(6); "
        "return v; "
        "}"
    ),
    "cep": (
        "function formatCEP(v) { "
        "var d = String(v).replace(/\\D/g, ''); "
        "return d.replace(/(\\d{5})(\\d{3})/, '$1-$2'); "
        "}"
    ),
    "percentage": (
        "function formatPercent(v) { "
        "return String(v).trim().replace(/\\s?%$/, '') + '%'; "
        "}"
    ),
}

# Type-format compatibility map (v3.15)
_TYPE_FORMAT_COMPAT: Dict[str, set] = {
    "date": {"date_numeric", "date_extenso"},
    "decimal": {"currency_brl", "percentage"},
    "integer": {"percentage"},
    "string": {"cpf", "cnpj", "phone", "currency_brl", "date_numeric",
               "date_extenso", "percentage", "cep"},
    "boolean": set(),
}

# Batch LLM prompt template
_BATCH_MATCH_PROMPT = """\
You are an XSD field mapper for document extraction.

Below are label-value pairs extracted from a document section.
{section_context}

Map each pair to the best matching XSD field path from the candidates below.

Pairs:
{pairs_json}

Available XSD fields (scoped to this section):
{xsd_paths}

Return a JSON object with key 'mappings': a list of objects, each with:
- 'pair_index' (int): index of the pair (0-based)
- 'candidates': list of up to 3 objects with 'path' (XSD field) and 'score' (float 0-1)
Return only valid JSON.
"""


# ---------------------------------------------------------------------------
# Sub-step 4.1 — XSD Parsing
# ---------------------------------------------------------------------------


def _step_4_1_xsd_parsing(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse XSD using existing xsd_parser.py. Returns field_tree dict or None."""
    from services.stages.xsd_parser import parse_xsd

    xsd_path = context.get("xsd_path")
    if not xsd_path:
        logger.warning("Stage 4.1: no xsd_path — field_tree will be None")
        return None

    try:
        field_tree = parse_xsd(xsd_path)
        return field_tree.to_dict()
    except (ValueError, FileNotFoundError) as exc:
        logger.error("Stage 4.1: XSD parse failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Sub-step 4.2 — Pair Validation
# ---------------------------------------------------------------------------


def _get_block_text(enriched_documents: List[Dict[str, Any]], block_id: str) -> str:
    """Retrieve text for a block_id from enriched_documents."""
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("id") == block_id:
                    return blk.get("text", "").strip()
    return ""


def _get_block_bbox(enriched_documents: List[Dict[str, Any]], block_id: str) -> Optional[List[float]]:
    """Retrieve bbox for a block_id from enriched_documents."""
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("id") == block_id:
                    bbox = blk.get("bbox")
                    return list(bbox) if bbox else None
    return None


def _get_block_info(enriched_documents: List[Dict[str, Any]], block_id: str) -> Dict[str, Any]:
    """Retrieve full block info for a block_id."""
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("id") == block_id:
                    return blk
    return {}


def _find_nearest_label_block(
    block_id: str,
    layout_bc: Dict[str, Dict[str, Any]],
    enriched_documents: List[Dict[str, Any]],
) -> Optional[str]:
    """Find nearest label block for an unpaired dynamic block by adjacency."""
    target_block = _get_block_info(enriched_documents, block_id)
    if not target_block:
        return None

    target_bbox = target_block.get("bbox", [0, 0, 0, 0])
    if not target_bbox or len(target_bbox) < 4:
        return None

    ty_mid = (target_bbox[1] + target_bbox[3]) / 2.0
    y_tolerance = 20.0
    x_max_diff = 250.0

    best_label_id: Optional[str] = None
    best_dist = float("inf")

    for other_id, other_bc in layout_bc.items():
        if other_id == block_id:
            continue
        if other_bc.get("semantic") != "label":
            continue
        # Skip labels that already have a pair
        if other_bc.get("field_pair"):
            continue

        other_block = _get_block_info(enriched_documents, other_id)
        if not other_block:
            continue
        other_bbox = other_block.get("bbox", [0, 0, 0, 0])
        if not other_bbox or len(other_bbox) < 4:
            continue

        oy_mid = (other_bbox[1] + other_bbox[3]) / 2.0
        if abs(ty_mid - oy_mid) > y_tolerance:
            continue

        x_dist = target_bbox[0] - other_bbox[2]  # value.x0 - label.x1
        if 0 <= x_dist <= x_max_diff and x_dist < best_dist:
            best_dist = x_dist
            best_label_id = other_id

    return best_label_id


def _step_4_2_pair_validation(
    context: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """Validate label-value pairs from Stage 3.3 and pair remaining blocks."""
    intelligence = context.get("intelligence", {})
    enriched_documents = context.get("enriched_documents", [])
    clusters = context.get("clusters", [])

    validated_pairs: Dict[str, List[Dict[str, Any]]] = {}

    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        layout_intel = intelligence.get(layout_id, {})
        block_classifications = layout_intel.get("block_classifications", {})
        pairs: List[Dict[str, Any]] = []
        unpaired_dynamics: List[str] = []

        for block_id, bc in block_classifications.items():
            field_pair = bc.get("field_pair")
            semantic = bc.get("semantic", "")

            if field_pair and semantic == "label":
                # This is a label with a paired value — validate the pair
                pair_bc = block_classifications.get(field_pair, {})
                pair_semantic = pair_bc.get("semantic", "")
                if pair_semantic in ("dynamic", "semi_dynamic", "likely_dynamic"):
                    pairs.append({
                        "label_block_id": block_id,
                        "value_block_id": field_pair,
                        "label_text": _get_block_text(enriched_documents, block_id),
                        "value_text": _get_block_text(enriched_documents, field_pair),
                        "source": "stage_3",
                        "label_bbox": _get_block_bbox(enriched_documents, block_id),
                        "value_bbox": _get_block_bbox(enriched_documents, field_pair),
                    })
            elif semantic in ("dynamic", "semi_dynamic", "likely_dynamic") and not field_pair:
                unpaired_dynamics.append(block_id)

        # Pair remaining unpaired dynamics with adjacent labels
        for block_id in unpaired_dynamics:
            adjacent_label = _find_nearest_label_block(
                block_id, block_classifications, enriched_documents,
            )
            if adjacent_label:
                pairs.append({
                    "label_block_id": adjacent_label,
                    "value_block_id": block_id,
                    "label_text": _get_block_text(enriched_documents, adjacent_label),
                    "value_text": _get_block_text(enriched_documents, block_id),
                    "source": "stage_4_adjacency",
                    "label_bbox": _get_block_bbox(enriched_documents, adjacent_label),
                    "value_bbox": _get_block_bbox(enriched_documents, block_id),
                })
            else:
                # Solo dynamic block (no label found)
                pairs.append({
                    "label_block_id": None,
                    "value_block_id": block_id,
                    "label_text": "",
                    "value_text": _get_block_text(enriched_documents, block_id),
                    "source": "stage_4_solo",
                    "label_bbox": None,
                    "value_bbox": _get_block_bbox(enriched_documents, block_id),
                })

        validated_pairs[layout_id] = pairs

    return validated_pairs


# ---------------------------------------------------------------------------
# Sub-step 4.3 — Format Pre-Detection
# ---------------------------------------------------------------------------


def _detect_format(text: str) -> Optional[str]:
    """Detect format of text via regex. Returns format name or None."""
    cleaned = text.strip()
    for name, pattern in _FORMAT_PATTERNS:
        if pattern.match(cleaned):
            return name
    return None


def _step_4_3_format_pre_detection(
    validated_pairs: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, str]]:
    """Detect format BEFORE matching — enriches LLM prompt."""
    format_functions: Dict[str, str] = {}

    for layout_id, pairs in validated_pairs.items():
        for pair in pairs:
            fmt = _detect_format(pair.get("value_text", ""))
            pair["detected_format"] = fmt
            if fmt and fmt not in format_functions:
                if fmt in _JS_FUNCTIONS:
                    format_functions[fmt] = _JS_FUNCTIONS[fmt]

    return validated_pairs, format_functions


# ---------------------------------------------------------------------------
# Sub-step 4.4 — Section-XSD Matching
# ---------------------------------------------------------------------------


def _get_complex_nodes(field_tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract complex nodes (those with children) from FieldTree dict."""
    if not field_tree:
        return []
    result: List[Dict[str, Any]] = []

    def _walk(nodes: List[Dict[str, Any]]) -> None:
        for node in nodes:
            if node.get("children"):
                result.append(node)
            _walk(node.get("children", []))

    _walk(field_tree.get("root_nodes", []))
    return result


def _extract_sections(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract section nodes from a document_tree."""
    sections: List[Dict[str, Any]] = []

    def _walk(node: Dict[str, Any]) -> None:
        if node.get("type") == "section":
            sections.append(node)
        for child in node.get("children", []):
            if isinstance(child, dict):
                _walk(child)

    _walk(tree)
    return sections


def _section_xsd_similarity(section: Dict[str, Any], xsd_node: Dict[str, Any]) -> float:
    """Score similarity between a document section and an XSD complex node.

    3 weighted signals:
    1. Name similarity (0.5): difflib between section name and XSD node name
    2. Child count ratio (0.3): proportion of children
    3. Format overlap (0.2): detected formats matching XSD child names
    """
    section_name = (section.get("name") or "").lower().replace(" ", "").replace("_", "")
    xsd_name = xsd_node.get("name", "").lower().replace("_", "")

    # Signal 1: Name similarity
    name_score = difflib.SequenceMatcher(None, section_name, xsd_name).ratio() if section_name else 0.0

    # Signal 2: Child count ratio
    section_children = section.get("children", [])
    section_count = len([c for c in section_children
                         if isinstance(c, dict) and c.get("type") in ("field", "label", "value", "dynamic")])
    xsd_count = len(xsd_node.get("children", []))
    if xsd_count > 0 and section_count > 0:
        count_score = min(section_count, xsd_count) / max(section_count, xsd_count)
    else:
        count_score = 0.0

    # Signal 3: Format overlap
    section_formats: set = set()
    for child in section_children:
        if isinstance(child, dict):
            fmt = child.get("detected_format")
            if fmt:
                section_formats.add(fmt)
    xsd_child_names = {c.get("name", "").lower() for c in xsd_node.get("children", [])}
    format_overlap = (
        len(section_formats & xsd_child_names) / max(1, len(section_formats))
        if section_formats else 0.0
    )

    return name_score * 0.5 + count_score * 0.3 + format_overlap * 0.2


def _step_4_4_section_xsd_matching(
    document_trees: Dict[str, Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Cross sections from document_trees with XSD complex nodes."""
    if not field_tree:
        return {}

    xsd_complex_nodes = _get_complex_nodes(field_tree)
    flat_paths = field_tree.get("flat_paths", [])
    section_xsd_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for layout_id, tree in document_trees.items():
        section_map: Dict[str, Dict[str, Any]] = {}

        for section in _extract_sections(tree):
            section_name = section.get("name", "")
            if not section_name:
                continue

            best_node: Optional[Dict[str, Any]] = None
            best_score = 0.0

            for xsd_node in xsd_complex_nodes:
                score = _section_xsd_similarity(section, xsd_node)
                if score > best_score:
                    best_score = score
                    best_node = xsd_node

            if best_node and best_score >= SECTION_MATCH_MIN_SCORE:
                section_map[section_name] = {
                    "xsd_node": best_node.get("path", ""),
                    "xsd_score": round(best_score, 4),
                    "child_paths": [c.get("path", "") for c in best_node.get("children", [])],
                }
            else:
                # Fallback: all XSD paths
                section_map[section_name] = {
                    "xsd_node": None,
                    "xsd_score": 0.0,
                    "child_paths": flat_paths,
                }

        section_xsd_map[layout_id] = section_map

    return section_xsd_map


# ---------------------------------------------------------------------------
# Sub-step 4.5 — Batch Field Matching (LLM + Two-Pass)
# ---------------------------------------------------------------------------


def _fuzzy_match_single(
    label_text: str,
    value_text: str,
    candidate_paths: List[str],
) -> List[Dict[str, Any]]:
    """Fuzzy match a single field against XSD paths using difflib."""
    if not candidate_paths:
        return []

    query = (label_text or value_text).lower().replace(" ", "").replace("_", "").replace(":", "")
    scored: List[Tuple[float, str]] = []
    for path in candidate_paths:
        last_part = path.split(".")[-1]
        cand = last_part.lower().replace("_", "")
        ratio = difflib.SequenceMatcher(None, query, cand).ratio()
        scored.append((ratio, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"path": p, "score": round(s, 4)} for s, p in scored[:5]]


def _fuzzy_batch_match(
    pairs_json: List[Dict[str, Any]],
    scoped_paths: List[str],
) -> Dict[int, List[Dict[str, Any]]]:
    """Fuzzy fallback for batch matching (no LLM)."""
    result: Dict[int, List[Dict[str, Any]]] = {}
    for pair in pairs_json:
        idx = pair.get("index", 0)
        label = pair.get("label", "")
        value = pair.get("value", "")
        candidates = _fuzzy_match_single(label, value, scoped_paths)
        result[idx] = candidates
    return result


async def _llm_batch_match_scoped(
    pairs_json: List[Dict[str, Any]],
    scoped_paths: List[str],
    section_context: str,
    openrouter_client: Any,
) -> Dict[int, List[Dict[str, Any]]]:
    """1 LLM call for pairs from a section, with scoped paths and format hints."""
    paths_str = "\n".join(f"- {p}" for p in scoped_paths[:40])
    prompt = _BATCH_MATCH_PROMPT.format(
        section_context=section_context,
        pairs_json=json.dumps(pairs_json, ensure_ascii=False),
        xsd_paths=paths_str,
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        from services.openrouter_client import _call_with_retry, strip_markdown_fences

        completion = await _call_with_retry(
            openrouter_client,
            messages=messages,
            model=GEMINI_FLASH_MODEL,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or "{}"
        data = json.loads(strip_markdown_fences(raw))

        result: Dict[int, List[Dict[str, Any]]] = {}
        for m in data.get("mappings", []):
            idx = m.get("pair_index", -1)
            candidates = [
                {"path": c["path"], "score": float(c["score"])}
                for c in m.get("candidates", [])
                if isinstance(c, dict) and "path" in c and "score" in c
            ]
            # Sort by score descending
            candidates.sort(key=lambda x: x["score"], reverse=True)
            result[idx] = candidates
        return result
    except Exception as exc:
        logger.warning("LLM batch match failed (%s); using fuzzy fallback.", exc)
        return _fuzzy_batch_match(pairs_json, scoped_paths)


def _get_pair_section(
    pair: Dict[str, Any],
    document_trees: Dict[str, Dict[str, Any]],
    layout_id: str,
) -> str:
    """Determine which section a pair belongs to by checking the document tree."""
    tree = document_trees.get(layout_id, {})
    value_block_id = pair.get("value_block_id", "")

    def _find_section(node: Dict[str, Any], current_section: str) -> Optional[str]:
        if node.get("type") == "section":
            current_section = node.get("name", "")
        # Check if any child block matches
        for child in node.get("children", []):
            if isinstance(child, dict):
                if child.get("block_id") == value_block_id:
                    return current_section
                result = _find_section(child, current_section)
                if result is not None:
                    return result
        return None

    return _find_section(tree, "") or ""


def _group_pairs_by_section(
    pairs: List[Dict[str, Any]],
    section_xsd_map: Dict[str, Dict[str, Any]],
    document_trees: Dict[str, Dict[str, Any]],
    layout_id: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group pairs by their section for scoped LLM calls."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for i, pair in enumerate(pairs):
        section = _get_pair_section(pair, document_trees, layout_id)
        pair_entry = {**pair, "original_index": i}
        groups.setdefault(section, []).append(pair_entry)
    return groups


def _get_xsd_type(field_tree: Dict[str, Any], xsd_path: str) -> Optional[str]:
    """Get XSD type for a given path from the field_tree."""
    if not field_tree or not xsd_path:
        return None

    def _walk(nodes: List[Dict[str, Any]]) -> Optional[str]:
        for node in nodes:
            if node.get("path") == xsd_path:
                node_type = node.get("type", "string")
                return node_type if node_type != "complex" else None
            result = _walk(node.get("children", []))
            if result is not None:
                return result
        return None

    return _walk(field_tree.get("root_nodes", []))


def _make_mapping_v2(
    block_id: str,
    layout_type_id: str,
    pdf_text: str,
    label_text: str,
    xsd_field_path: str,
    confidence: float,
    is_ambiguous: bool,
    candidates: List[Dict[str, Any]],
    bbox: Optional[List[float]] = None,
    xsd_type: Optional[str] = None,
    is_table_cell: bool = False,
    from_table: bool = False,
    smart_signals: Any = None,
    semantic_confirmed: Optional[str] = None,
    detected_format: Optional[str] = None,
    page_number: int = 0,
    pdf_id: str = "",
) -> Dict[str, Any]:
    """Build a field mapping entry conforming to contract 3.4."""
    # Derive frontend-compatible status
    if is_ambiguous:
        fe_status = "ambiguous"
    elif xsd_field_path:
        fe_status = "mapped"
    else:
        fe_status = "unmapped"

    result: Dict[str, Any] = {
        "block_id": block_id or "",
        "layout_type_id": layout_type_id,
        "pdf_text": pdf_text,
        "label_text": label_text,
        "bbox": bbox,
        "xsd_field_path": xsd_field_path,
        "xsd_type": xsd_type,
        "confidence": round(confidence, 4),
        "is_ambiguous": is_ambiguous,
        "candidates": candidates,
        "page_number": page_number,
        "pdf_id": pdf_id,
        "is_table_cell": is_table_cell,
        "from_table": from_table,
        "detected_format": detected_format,
        "smart_signals": smart_signals,
        "semantic_confirmed": semantic_confirmed,
        # Frontend-compatible aliases
        "name": label_text or pdf_text,
        "path": xsd_field_path,
        "type": xsd_type or "text",
        "status": fe_status,
        "isOptional": False,
    }
    return result


async def _step_4_5_field_matching(
    validated_pairs: Dict[str, List[Dict[str, Any]]],
    field_tree: Optional[Dict[str, Any]],
    intelligence: Dict[str, Any],
    section_xsd_map: Dict[str, Dict[str, Dict[str, Any]]],
    document_trees: Dict[str, Dict[str, Any]],
    openrouter_client: Any,
) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Dict[str, Any]]]:
    """Batch field matching with section scoping and two-pass."""
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    field_mappings: List[Dict[str, Any]] = []
    ambiguous_fields: List[str] = []
    confirmations: Dict[str, Dict[str, Any]] = {}

    for layout_id, pairs in validated_pairs.items():
        if not pairs:
            continue

        layout_intel = intelligence.get(layout_id, {})
        block_classifications = layout_intel.get("block_classifications", {})

        if not flat_paths:
            # No XSD — create minimal mappings
            for pair in pairs:
                bc = block_classifications.get(pair.get("value_block_id", ""), {})
                field_mappings.append(_make_mapping_v2(
                    block_id=pair.get("value_block_id", ""),
                    layout_type_id=layout_id,
                    pdf_text=pair.get("value_text", ""),
                    label_text=pair.get("label_text", ""),
                    xsd_field_path="",
                    confidence=0.0,
                    is_ambiguous=False,
                    candidates=[],
                    bbox=pair.get("value_bbox"),
                    is_table_cell=bc.get("is_table_cell", False),
                    from_table=bc.get("from_table", False),
                    smart_signals=bc.get("smart_signals"),
                    detected_format=pair.get("detected_format"),
                ))
            continue

        layout_section_map = section_xsd_map.get(layout_id, {})

        # Group pairs by section for scoped LLM calls
        section_groups = _group_pairs_by_section(
            pairs, layout_section_map, document_trees, layout_id,
        )

        all_results: Dict[int, List[Dict[str, Any]]] = {}

        for section_name, group in section_groups.items():
            scoped_paths = layout_section_map.get(section_name, {}).get("child_paths", flat_paths)
            if not scoped_paths:
                scoped_paths = flat_paths
            xsd_node = layout_section_map.get(section_name, {}).get("xsd_node")

            section_context = (
                f"This section is mapped to XSD node '{xsd_node}'. "
                f"Focus on its children."
            ) if xsd_node else "No section mapping available. Use all XSD fields."

            # Build pairs JSON with format hints
            pairs_json = [
                {
                    "index": p["original_index"],
                    "label": p.get("label_text", ""),
                    "value": p.get("value_text", ""),
                    "detected_format": p.get("detected_format"),
                }
                for p in group
            ]

            if openrouter_client:
                batch = await _llm_batch_match_scoped(
                    pairs_json, scoped_paths, section_context, openrouter_client,
                )
            else:
                batch = _fuzzy_batch_match(pairs_json, scoped_paths)

            all_results.update(batch)

        # === PASS 1: Accept high-confidence matches ===
        used_paths: set = set()
        pass1_entries: List[Tuple[int, Dict, List[Dict[str, Any]], bool]] = []

        for i, pair in enumerate(pairs):
            candidates = all_results.get(i, [])
            best = candidates[0] if candidates else None

            if best and best["score"] >= HIGH_CONFIDENCE_THRESHOLD:
                used_paths.add(best["path"])
                pass1_entries.append((i, pair, candidates, False))  # not needs_pass2
            else:
                pass1_entries.append((i, pair, candidates, True))  # needs pass 2

        # === PASS 2: Re-rank remaining without used paths ===
        for i, pair, candidates, needs_pass2 in pass1_entries:
            if needs_pass2 and candidates:
                # Filter out paths already claimed in pass 1
                filtered = [c for c in candidates if c["path"] not in used_paths]
                if filtered:
                    candidates = filtered

            best = candidates[0] if candidates else None
            is_ambiguous = False
            if best and len(candidates) >= 2:
                if candidates[0]["score"] - candidates[1]["score"] < AMBIGUITY_THRESHOLD:
                    is_ambiguous = True
                    ambiguous_fields.append(best["path"])

            xsd_path = best["path"] if best else ""
            confidence = best["score"] if best else 0.0

            # PA4: XSD confirms likely_dynamic -> dynamic
            bc = block_classifications.get(pair.get("value_block_id", ""), {})
            smart_signals = bc.get("smart_signals")
            semantic_confirmed: Optional[str] = None

            if bc.get("semantic") == "likely_dynamic" and confidence >= HIGH_CONFIDENCE_THRESHOLD:
                semantic_confirmed = "dynamic"
                confirmations[pair.get("value_block_id", "")] = {
                    "original_semantic": "likely_dynamic",
                    "confirmed_semantic": "dynamic",
                    "xsd_path": xsd_path,
                    "xsd_confidence": confidence,
                }

            xsd_type = _get_xsd_type(field_tree, xsd_path) if xsd_path else None

            field_mappings.append(_make_mapping_v2(
                block_id=pair.get("value_block_id", ""),
                layout_type_id=layout_id,
                pdf_text=pair.get("value_text", ""),
                label_text=pair.get("label_text", ""),
                xsd_field_path=xsd_path,
                xsd_type=xsd_type,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                candidates=candidates,
                bbox=pair.get("value_bbox"),
                is_table_cell=bc.get("is_table_cell", False),
                from_table=bc.get("from_table", False),
                smart_signals=smart_signals,
                semantic_confirmed=semantic_confirmed,
                detected_format=pair.get("detected_format"),
            ))

    return field_mappings, ambiguous_fields, confirmations


# ---------------------------------------------------------------------------
# Sub-step 4.6 — Confidence Scoring (heuristic, per-layout)
# ---------------------------------------------------------------------------


def _get_layout_stability(intelligence: Dict[str, Any], layout_id: str) -> float:
    """Get layout stability factor for a layout."""
    layout_intel = intelligence.get(layout_id, {})
    cq = layout_intel.get("classification_quality", {})
    # Stronger stats -> higher stability
    strength = cq.get("statistical_strength", "none")
    if strength == "strong":
        return 0.9
    elif strength == "weak":
        return 0.7
    return 0.5


def _get_anchor_detection(layout_mappings: List[Dict[str, Any]]) -> float:
    """Fraction of mappings with non-empty label_text."""
    if not layout_mappings:
        return 0.5
    with_label = sum(1 for m in layout_mappings if m.get("label_text"))
    return round(with_label / len(layout_mappings), 4)


def _get_grid_quality(cluster: Dict[str, Any]) -> float:
    """Grid quality from cluster info."""
    # Look for table indicators in the cluster
    page_count = cluster.get("page_count", 1)
    return 0.7 if page_count > 1 else 0.5


def _get_field_variability(intelligence: Dict[str, Any], layout_id: str) -> float:
    """Field variability factor from intelligence."""
    layout_intel = intelligence.get(layout_id, {})
    cq = layout_intel.get("classification_quality", {})
    uncertain = cq.get("uncertain_count", 0)
    total = cq.get("total_pages_in_cluster", 1)
    # More uncertain blocks -> lower variability confidence
    if total > 0:
        ratio = uncertain / max(total, 1)
        return round(max(0.3, 1.0 - ratio), 4)
    return 0.5


def _get_vision_agreement(visual_analysis: Dict[str, Any], cluster: Dict[str, Any]) -> float:
    """Vision agreement from visual_analysis consistency scores."""
    if not visual_analysis:
        return 0.5
    scores = []
    for page_key, page_data in visual_analysis.items():
        if isinstance(page_data, dict):
            cs = page_data.get("consistency_score")
            if cs is not None:
                try:
                    scores.append(max(0.0, min(1.0, float(cs) / 100.0)))
                except (TypeError, ValueError):
                    pass
    if not scores:
        return 0.5
    return round(sum(scores) / len(scores), 4)


def _step_4_6_confidence_scoring(
    field_mappings: List[Dict[str, Any]],
    intelligence: Dict[str, Any],
    visual_analysis: Dict[str, Any],
    clusters: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Confidence scoring per-layout. Heuristic (no LLM)."""
    confidence_scores: Dict[str, Dict[str, Any]] = {}

    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        layout_mappings = [m for m in field_mappings if m.get("layout_type_id") == layout_id]
        layout_intel = intelligence.get(layout_id, {})
        cq = layout_intel.get("classification_quality", {})

        factors = {
            "layout_stability": _get_layout_stability(intelligence, layout_id),
            "anchor_detection": _get_anchor_detection(layout_mappings),
            "grid_quality": _get_grid_quality(cluster),
            "field_variability": _get_field_variability(intelligence, layout_id),
            "vision_agreement": _get_vision_agreement(visual_analysis, cluster),
        }

        # Heuristic 1: Tabular + low anchor -> don't penalise anchor_detection
        if factors["anchor_detection"] < 0.4 and factors["grid_quality"] >= 0.7:
            factors["anchor_detection"] = max(factors["anchor_detection"], 0.6)

        # Heuristic 2 (PA1): smart_signals -> adjust field_variability
        if cq.get("smart_override_count", 0) > 0:
            factors["field_variability"] = max(0.0, factors["field_variability"] - 0.10)
        if cq.get("statistical_strength") == "none":
            factors["field_variability"] = max(0.0, factors["field_variability"] - 0.15)
        elif cq.get("statistical_strength") == "strong":
            factors["field_variability"] = min(1.0, factors["field_variability"] + 0.10)

        # Heuristic 3: Many ambiguous -> penalise
        ambiguous_ratio = (
            sum(1 for m in layout_mappings if m.get("is_ambiguous")) / max(1, len(layout_mappings))
        )
        if ambiguous_ratio > 0.3:
            factors["anchor_detection"] = max(0.0, factors["anchor_detection"] - 0.1)

        # Weighted average
        overall = sum(WEIGHTS[k] * factors[k] for k in WEIGHTS)
        overall = round(overall, 4)

        # Status
        if overall >= THRESHOLD_APPROVED:
            status = "approved"
        elif overall >= THRESHOLD_REVIEW:
            status = "review_recommended"
        else:
            status = "human_review_required"

        confidence_scores[layout_id] = {
            **factors,
            "overall": round(overall * 100),
            "status": status,
        }

    return confidence_scores


# ---------------------------------------------------------------------------
# Sub-step 4.7 — Consistency Validation
# ---------------------------------------------------------------------------


def _get_required_paths(field_tree: Dict[str, Any]) -> List[str]:
    """Extract flat_paths of fields with required=True."""
    if not field_tree:
        return []
    required: List[str] = []

    def _walk(nodes: List[Dict[str, Any]]) -> None:
        for node in nodes:
            if node.get("required", True) and node.get("type") != "complex":
                required.append(node.get("path", ""))
            _walk(node.get("children", []))

    _walk(field_tree.get("root_nodes", []))
    return required


def _validate_type_format(
    field_mappings: List[Dict[str, Any]],
    warnings: List[str],
) -> List[Dict[str, Any]]:
    """Cross-validate XSD type vs detected_format. Returns mismatches."""
    mismatches: List[Dict[str, Any]] = []
    for m in field_mappings:
        xsd_type = m.get("xsd_type")
        fmt = m.get("detected_format")
        if not xsd_type or not fmt:
            continue
        compatible = _TYPE_FORMAT_COMPAT.get(xsd_type, {"string"})
        if fmt not in compatible:
            mismatches.append({
                "block_id": m.get("block_id", ""),
                "xsd_type": xsd_type,
                "detected_format": fmt,
                "xsd_path": m.get("xsd_field_path", ""),
            })
            warnings.append(
                f"type_format_mismatch: '{m.get('xsd_field_path', '')}' "
                f"is {xsd_type} in XSD but detected_format is {fmt}"
            )
    return mismatches


def _step_4_7_consistency_validation(
    field_mappings: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    intelligence: Dict[str, Any],
) -> Dict[str, Any]:
    """Consistency validation: orphans, unmapped required, type-format."""
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    flat_paths_set = set(p for p in flat_paths if p)

    warnings: List[str] = []
    errors: List[str] = []

    # 1. Dynamic blocks without mapping
    dynamic_count = 0
    for layout_id, layout_intel in intelligence.items():
        bc = layout_intel.get("block_classifications", {})
        for block_id, block_bc in bc.items():
            if block_bc.get("semantic") in ("dynamic", "semi_dynamic", "likely_dynamic"):
                dynamic_count += 1

    mapped_count = len([m for m in field_mappings if m.get("xsd_field_path")])
    orphan_count = 0
    if dynamic_count > 0 and mapped_count < dynamic_count:
        orphan_count = dynamic_count - mapped_count
        warnings.append(
            f"skeleton_vs_result: {orphan_count} dynamic block(s) "
            f"without field_mapping ({mapped_count}/{dynamic_count} mapped)"
        )

    # 2. XSD coverage
    mapped_paths = {m.get("xsd_field_path", "") for m in field_mappings if m.get("xsd_field_path")}
    unmapped_xsd = [p for p in flat_paths if p not in mapped_paths]
    if unmapped_xsd:
        warnings.append(
            f"xsd_coverage: {len(unmapped_xsd)} XSD field(s) without mapping: "
            + ", ".join(unmapped_xsd[:10])
        )

    # 3. Orphan mappings (paths not in field_tree)
    for m in field_mappings:
        path = m.get("xsd_field_path", "")
        if path and path not in flat_paths_set:
            errors.append(f"orphan_mapping: '{path}' does not exist in field_tree")

    # 4. Required XSD fields without mapping (reverse mapping)
    required_paths = _get_required_paths(field_tree) if field_tree else []
    unmapped_required = [p for p in required_paths if p not in mapped_paths]
    if unmapped_required:
        errors.append(
            f"required_unmapped: {len(unmapped_required)} required XSD field(s) "
            f"without mapping: " + ", ".join(unmapped_required[:10])
        )

    # 5. Type-format mismatches
    type_format_mismatches = _validate_type_format(field_mappings, warnings)

    return {
        "warnings": warnings,
        "errors": errors,
        "orphan_count": orphan_count,
        "unmapped_xsd_fields": unmapped_xsd,
        "unmapped_required_xsd_fields": unmapped_required,
        "type_format_mismatches": type_format_mismatches,
    }


# ---------------------------------------------------------------------------
# Main stage orchestrator
# ---------------------------------------------------------------------------


async def run_stage4(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 4: Field Mapping — 7 sub-steps.

    Reads:
        context["xsd_path"], context["intelligence"], context["clusters"],
        context["enriched_documents"], context["document_trees"],
        context["visual_analysis"]

    Writes:
        context["field_tree"], context["field_mappings"],
        context["format_functions"], context["confidence_scores"],
        context["validation_result"], context["ambiguous_fields"],
        context["block_classifications_confirmed"]
    """
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    stage = 4
    name = "Field Mapping"
    context["_current_stage"] = stage
    context["_current_stage_name"] = name

    intelligence = context.get("intelligence", {})
    clusters = context.get("clusters", [])
    visual_analysis = context.get("visual_analysis", {})
    document_trees: Dict[str, Dict[str, Any]] = context.get("document_trees", {})

    # Determine LLM availability
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_client = context.get("openrouter_client")
    if api_key and openrouter_client is None:
        try:
            from services.openrouter_client import get_client
            openrouter_client = get_client(api_key=api_key)
        except Exception as exc:
            logger.warning("Cannot create OpenRouter client: %s. Using fuzzy fallback.", exc)
            openrouter_client = None

    # --- 4.1 XSD Parsing ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.05),
        sub_step="4.1 XSD Parsing", sub_progress_pct=0.05,
    ))

    field_tree = _step_4_1_xsd_parsing(context)
    context["field_tree"] = field_tree

    # --- 4.2 Pair Validation ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.15),
        sub_step="4.2 Pair Validation", sub_progress_pct=0.15,
    ))

    validated_pairs = _step_4_2_pair_validation(context)

    # --- 4.3 + 4.4 in parallel ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.30),
        sub_step="4.3 Format Pre-Detection + 4.4 Section-XSD Matching", sub_progress_pct=0.30,
    ))

    # 4.3 Format Pre-Detection
    validated_pairs, format_functions = _step_4_3_format_pre_detection(validated_pairs)
    context["format_functions"] = format_functions

    # 4.4 Section-XSD Matching
    section_xsd_map = _step_4_4_section_xsd_matching(document_trees, field_tree)

    # --- 4.5 Batch Field Matching ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.55),
        sub_step="4.5 Batch Field Matching", sub_progress_pct=0.55,
    ))

    field_mappings, ambiguous_fields, confirmations = await _step_4_5_field_matching(
        validated_pairs, field_tree, intelligence, section_xsd_map,
        document_trees, openrouter_client,
    )
    context["field_mappings"] = field_mappings
    context["ambiguous_fields"] = ambiguous_fields
    context["block_classifications_confirmed"] = confirmations

    # --- 4.6 + 4.7 in parallel ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.80),
        sub_step="4.6 Confidence Scoring + 4.7 Consistency Validation", sub_progress_pct=0.80,
    ))

    # 4.6 Confidence Scoring (per-layout)
    confidence_scores = _step_4_6_confidence_scoring(
        field_mappings, intelligence, visual_analysis, clusters,
    )
    context["confidence_scores"] = confidence_scores

    # 4.7 Consistency Validation
    validation_result = _step_4_7_consistency_validation(
        field_mappings, field_tree, intelligence,
    )
    context["validation_result"] = validation_result

    # --- Build per-layout mapping stats ---
    mapping_stats: Dict[str, Dict[str, Any]] = {}
    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        layout_mappings = [m for m in field_mappings if m.get("layout_type_id") == layout_id]
        total = len(layout_mappings)
        mapped = len([m for m in layout_mappings if m.get("xsd_field_path")])
        accuracy_est = round(mapped / max(total, 1), 4)
        mapping_stats[layout_id] = {
            "total_fields": total,
            "mapped_fields": mapped,
            "accuracy_estimate": accuracy_est,
        }

    # --- Done ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="completed",
        progress_pct=compute_overall_progress(stage, 1.0),
        sub_step="4.7 Done", sub_progress_pct=1.0,
        summary={
            "total_mappings": len(field_mappings),
            "ambiguous_count": len(ambiguous_fields),
            "confirmations": len(confirmations),
            "warnings": len(validation_result.get("warnings", [])),
            "errors": len(validation_result.get("errors", [])),
        },
    ))

    context["stage_4_result"] = {
        "field_mappings": field_mappings,
        "confidence_scores": confidence_scores,
        "validation_result": validation_result,
        "mapping_stats": mapping_stats,
    }

    return context
