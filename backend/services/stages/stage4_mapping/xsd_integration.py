"""Stage 4 — XSD Integration sub-module (Steps 4.1, 4.2, 4.3).

Responsibilities:
  - XSD parsing via xsd_parser.py (4.1)
  - Pair validation: consume Stage 3.3 label-value pairs, pair remaining (4.2)
  - Format pre-detection: regex format detection before LLM matching (4.3)

Story 41.3 — extracted from stage4_field_mapping.py
"""

from __future__ import annotations

import logging
import re
from typing import Any

from models.pipeline_context import BlockClassification

logger = logging.getLogger(__name__)


def _to_bc(raw: dict[str, Any] | BlockClassification) -> BlockClassification:
    """Coerce a plain dict or existing BlockClassification to BlockClassification."""
    if isinstance(raw, BlockClassification):
        return raw
    return BlockClassification(**raw)


# ---------------------------------------------------------------------------
# Format detection patterns
# ---------------------------------------------------------------------------

_FORMAT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("currency_brl", re.compile(r"^R\$\s?[\d.,]+$")),
    ("date_numeric", re.compile(r"^\d{2}/\d{2}/\d{4}$")),
    (
        "date_extenso",
        re.compile(
            r"^\d{1,2}\s+de\s+"
            r"(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
            r"\s+de\s+\d{4}$",
            re.IGNORECASE,
        ),
    ),
    ("cpf", re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")),
    ("cnpj", re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")),
    ("phone", re.compile(r"^\(\d{2}\)\s?\d{4,5}-\d{4}$")),
    ("cep", re.compile(r"^\d{5}-?\d{3}$")),
    ("percentage", re.compile(r"^[\d.,]+\s?%$")),
]

_JS_FUNCTIONS: dict[str, str] = {
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
    "percentage": ("function formatPercent(v) { return String(v).trim().replace(/\\s?%$/, '') + '%'; }"),
}


# ---------------------------------------------------------------------------
# Sub-step 4.1 — XSD Parsing
# ---------------------------------------------------------------------------


def _step_4_1_xsd_parsing(context: dict[str, Any]) -> dict[str, Any] | None:
    """Parse XSD using existing xsd_parser.py. Returns field_tree dict or None."""
    from services.stages.xsd_parser import parse_xsd

    xsd_path = context.get("xsd_path")
    if not xsd_path:
        logger.warning("Stage 4.1: no xsd_path — field_tree will be None")
        context.setdefault("_pipeline_warnings", []).append(
            {
                "code": "xsd_not_found",
                "severity": "warning",
                "message": (
                    "XSD não encontrado — field_tree será None. Mapeamento de campos não disponível para este pipeline."
                ),
                "stage": 4,
            }
        )
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


def _get_block_text(enriched_documents: list[dict[str, Any]], block_id: str) -> str:
    """Retrieve text for a block_id from enriched_documents."""
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("id") == block_id:
                    return str(blk.get("text", "")).strip()
    return ""


def _get_block_bbox(enriched_documents: list[dict[str, Any]], block_id: str) -> list[float] | None:
    """Retrieve bbox for a block_id from enriched_documents."""
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("id") == block_id:
                    bbox = blk.get("bbox")
                    return list(bbox) if bbox else None
    return None


def _get_block_info(enriched_documents: list[dict[str, Any]], block_id: str) -> dict[str, Any]:
    """Retrieve full block info for a block_id."""
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            for blk in page.get("text_blocks", []):
                if blk.get("id") == block_id:
                    return dict(blk)
    return {}


def _find_nearest_label_block(
    block_id: str,
    layout_bc: dict[str, Any],
    enriched_documents: list[dict[str, Any]],
) -> str | None:
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

    best_label_id: str | None = None
    best_dist = float("inf")

    _empty_bc = BlockClassification()
    for other_id, other_raw in layout_bc.items():
        if other_id == block_id:
            continue
        other_bc = _to_bc(other_raw) if other_raw else _empty_bc
        if other_bc.semantic != "label":
            continue
        if other_bc.field_pair:
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

        x_dist = target_bbox[0] - other_bbox[2]
        if 0 <= x_dist <= x_max_diff and x_dist < best_dist:
            best_dist = x_dist
            best_label_id = other_id

    return best_label_id


def _step_4_2_pair_validation(
    context: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Validate label-value pairs from Stage 3.3 and pair remaining blocks."""
    intelligence = context.get("intelligence", {})
    enriched_documents = context.get("enriched_documents", [])
    clusters = context.get("clusters", [])

    validated_pairs: dict[str, list[dict[str, Any]]] = {}
    _empty_bc = BlockClassification()

    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        layout_intel = intelligence.get(layout_id, {})
        raw_bc = layout_intel.get("block_classifications", {})
        pairs: list[dict[str, Any]] = []
        unpaired_dynamics: list[str] = []

        for block_id, raw in raw_bc.items():
            bc = _to_bc(raw) if raw else _empty_bc
            field_pair = bc.field_pair
            semantic = bc.semantic

            if field_pair and semantic == "label":
                pair_raw = raw_bc.get(field_pair, {})
                pair_bc = _to_bc(pair_raw) if pair_raw else _empty_bc
                pair_semantic = pair_bc.semantic
                if pair_semantic in ("dynamic", "semi_dynamic", "likely_dynamic"):
                    pairs.append(
                        {
                            "label_block_id": block_id,
                            "value_block_id": field_pair,
                            "label_text": _get_block_text(enriched_documents, block_id),
                            "value_text": _get_block_text(enriched_documents, field_pair),
                            "source": "stage_3",
                            "label_bbox": _get_block_bbox(enriched_documents, block_id),
                            "value_bbox": _get_block_bbox(enriched_documents, field_pair),
                        }
                    )
            elif semantic in ("dynamic", "semi_dynamic", "likely_dynamic") and not field_pair:
                unpaired_dynamics.append(block_id)

        for block_id in unpaired_dynamics:
            adjacent_label = _find_nearest_label_block(block_id, raw_bc, enriched_documents)
            if adjacent_label:
                pairs.append(
                    {
                        "label_block_id": adjacent_label,
                        "value_block_id": block_id,
                        "label_text": _get_block_text(enriched_documents, adjacent_label),
                        "value_text": _get_block_text(enriched_documents, block_id),
                        "source": "stage_4_adjacency",
                        "label_bbox": _get_block_bbox(enriched_documents, adjacent_label),
                        "value_bbox": _get_block_bbox(enriched_documents, block_id),
                    }
                )
            else:
                pairs.append(
                    {
                        "label_block_id": None,
                        "value_block_id": block_id,
                        "label_text": "",
                        "value_text": _get_block_text(enriched_documents, block_id),
                        "source": "stage_4_solo",
                        "label_bbox": None,
                        "value_bbox": _get_block_bbox(enriched_documents, block_id),
                    }
                )

        validated_pairs[layout_id] = pairs

    return validated_pairs


# ---------------------------------------------------------------------------
# Sub-step 4.3 — Format Pre-Detection
# ---------------------------------------------------------------------------


def _detect_format(text: str) -> str | None:
    """Detect format of text via regex. Returns format name or None."""
    cleaned = text.strip()
    for name, pattern in _FORMAT_PATTERNS:
        if pattern.match(cleaned):
            return name
    return None


def _step_4_3_format_pre_detection(
    validated_pairs: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    """Detect format BEFORE matching — enriches LLM prompt."""
    format_functions: dict[str, str] = {}

    for layout_id, pairs in validated_pairs.items():
        for pair in pairs:
            fmt = _detect_format(pair.get("value_text", ""))
            pair["detected_format"] = fmt
            if fmt and fmt not in format_functions:
                if fmt in _JS_FUNCTIONS:
                    format_functions[fmt] = _JS_FUNCTIONS[fmt]

    return validated_pairs, format_functions
