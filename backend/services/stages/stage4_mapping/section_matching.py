"""Stage 4 — Section Matching sub-module (Steps 4.4, 4.5).

Responsibilities:
  - Section-XSD matching via fuzzy name + child count + format overlap (4.4)
  - Batch field matching with section scoping, LLM + two-pass (4.5)

Story 41.3 — extracted from stage4_field_mapping.py
"""

from __future__ import annotations

import difflib
import json
import logging
from typing import Any

from models.pipeline_context import BlockClassification, FieldMappingEntry
from services.stages.stage4_mapping.constants import (  # noqa: F401
    _BATCH_MATCH_PROMPT,
    AMBIGUITY_THRESHOLD,
    GEMINI_FLASH_MODEL,
    HIGH_CONFIDENCE_THRESHOLD,
    MINIMUM_MATCH_THRESHOLD,
    SECTION_MATCH_MIN_SCORE,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-step 4.4 — Section-XSD Matching
# ---------------------------------------------------------------------------


def _get_complex_nodes(field_tree: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract complex nodes (those with children) from FieldTree dict."""
    if not field_tree:
        return []
    result: list[dict[str, Any]] = []

    def _walk(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            if node.get("children"):
                result.append(node)
            _walk(node.get("children", []))

    _walk(field_tree.get("root_nodes", []))
    return result


def _extract_sections(tree: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract section nodes from a document_tree."""
    sections: list[dict[str, Any]] = []

    def _walk(node: dict[str, Any]) -> None:
        if node.get("type") == "section":
            sections.append(node)
        for child in node.get("children", []):
            if isinstance(child, dict):
                _walk(child)

    _walk(tree)
    return sections


def _section_xsd_similarity(section: dict[str, Any], xsd_node: dict[str, Any]) -> float:
    """Score similarity between a document section and an XSD complex node.

    3 weighted signals:
    1. Name similarity (0.5)
    2. Child count ratio (0.3)
    3. Format overlap (0.2)
    """
    section_name = (section.get("name") or "").lower().replace(" ", "").replace("_", "")
    xsd_name = xsd_node.get("name", "").lower().replace("_", "")

    name_score = difflib.SequenceMatcher(None, section_name, xsd_name).ratio() if section_name else 0.0

    section_children = section.get("children", [])
    section_count = len(
        [c for c in section_children if isinstance(c, dict) and c.get("type") in ("field", "label", "value", "dynamic")]
    )
    xsd_count = len(xsd_node.get("children", []))
    if xsd_count > 0 and section_count > 0:
        count_score = min(section_count, xsd_count) / max(section_count, xsd_count)
    else:
        count_score = 0.0

    section_formats: set = set()
    for child in section_children:
        if isinstance(child, dict):
            fmt = child.get("detected_format")
            if fmt:
                section_formats.add(fmt)
    xsd_child_names = {c.get("name", "").lower() for c in xsd_node.get("children", [])}
    format_overlap = len(section_formats & xsd_child_names) / max(1, len(section_formats)) if section_formats else 0.0

    return name_score * 0.5 + count_score * 0.3 + format_overlap * 0.2


def _expand_child_paths(node: dict[str, Any]) -> list[str]:
    """Return leaf XSD paths for a matched node.

    Handles the double-nesting pattern common in Planet Express XSDs
    (e.g. Propostas -> Propostas.Propostas[] -> leaf fields).
    When all direct children are complex nodes (no leaf paths at depth 1),
    expands one level deeper to expose the actual leaf fields to the LLM.
    """
    children = node.get("children", [])
    leaf_paths = [c.get("path", "") for c in children if not c.get("children")]
    if leaf_paths:
        return leaf_paths
    expanded: list[str] = []
    for c in children:
        expanded.extend(gc.get("path", "") for gc in c.get("children", []))
    return expanded or [c.get("path", "") for c in children]


def _step_4_4_section_xsd_matching(
    document_trees: dict[str, dict[str, Any]],
    field_tree: dict[str, Any] | None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Cross sections from document_trees with XSD complex nodes."""
    if not field_tree:
        return {}

    xsd_complex_nodes = _get_complex_nodes(field_tree)
    flat_paths = field_tree.get("flat_paths", [])
    section_xsd_map: dict[str, dict[str, dict[str, Any]]] = {}

    for layout_id, tree in document_trees.items():
        section_map: dict[str, dict[str, Any]] = {}

        for section in _extract_sections(tree):
            section_name = section.get("name", "")
            if not section_name:
                continue

            best_node: dict[str, Any] | None = None
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
                    "child_paths": _expand_child_paths(best_node),
                }
            else:
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
    candidate_paths: list[str],
) -> list[dict[str, Any]]:
    """Fuzzy match a single field against XSD paths using difflib."""
    if not candidate_paths:
        return []

    query = (label_text or value_text).lower().replace(" ", "").replace("_", "").replace(":", "")
    scored: list[tuple[float, str]] = []
    for path in candidate_paths:
        last_part = path.split(".")[-1]
        cand = last_part.lower().replace("_", "")
        ratio = difflib.SequenceMatcher(None, query, cand).ratio()
        scored.append((ratio, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"path": p, "score": round(s, 4)} for s, p in scored[:5]]


def _fuzzy_batch_match(
    pairs_json: list[dict[str, Any]],
    scoped_paths: list[str],
) -> dict[int, list[dict[str, Any]]]:
    """Fuzzy fallback for batch matching (no LLM)."""
    result: dict[int, list[dict[str, Any]]] = {}
    for pair in pairs_json:
        idx = pair.get("index", 0)
        label = pair.get("label", "")
        value = pair.get("value", "")
        candidates = _fuzzy_match_single(label, value, scoped_paths)
        result[idx] = candidates
    return result


async def _llm_batch_match_scoped(
    pairs_json: list[dict[str, Any]],
    scoped_paths: list[str],
    section_context: str,
    openrouter_client: Any,
) -> dict[int, list[dict[str, Any]]]:
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

        result: dict[int, list[dict[str, Any]]] = {}
        for m in data.get("mappings", []):
            idx = m.get("pair_index", -1)
            candidates = [
                {"path": c["path"], "score": float(c["score"])}
                for c in m.get("candidates", [])
                if isinstance(c, dict) and "path" in c and "score" in c
            ]
            candidates.sort(key=lambda x: x["score"], reverse=True)
            result[idx] = candidates
        return result
    except Exception as exc:
        logger.warning("LLM batch match failed (%s); using fuzzy fallback.", exc)
        return _fuzzy_batch_match(pairs_json, scoped_paths)


def _get_pair_section(
    pair: dict[str, Any],
    document_trees: dict[str, dict[str, Any]],
    layout_id: str,
) -> str:
    """Determine which section a pair belongs to by checking the document tree."""
    tree = document_trees.get(layout_id, {})
    value_block_id = pair.get("value_block_id", "")

    def _find_section(node: dict[str, Any], current_section: str) -> str | None:
        if node.get("type") == "section":
            current_section = node.get("name", "")
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
    pairs: list[dict[str, Any]],
    section_xsd_map: dict[str, dict[str, Any]],
    document_trees: dict[str, dict[str, Any]],
    layout_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Group pairs by their section for scoped LLM calls."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for i, pair in enumerate(pairs):
        section = _get_pair_section(pair, document_trees, layout_id)
        pair_entry = {**pair, "original_index": i}
        groups.setdefault(section, []).append(pair_entry)
    return groups


def _get_xsd_type(field_tree: dict[str, Any], xsd_path: str) -> str | None:
    """Get XSD type for a given path from the field_tree."""
    if not field_tree or not xsd_path:
        return None

    def _walk(nodes: list[dict[str, Any]]) -> str | None:
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
    candidates: list[dict[str, Any]],
    bbox: list[float] | None = None,
    xsd_type: str | None = None,
    is_table_cell: bool = False,
    from_table: bool = False,
    smart_signals: Any = None,
    semantic_confirmed: str | None = None,
    detected_format: str | None = None,
    page_number: int = 0,
    pdf_id: str = "",
    debug_section: str | None = None,
    debug_top_candidate_path: str | None = None,
    debug_top_candidate_score: float | None = None,
    debug_scoped_paths_count: int | None = None,
) -> FieldMappingEntry:
    """Build a typed FieldMappingEntry conforming to contract 3.4.

    Story 42.6 — returns FieldMappingEntry instead of plain dict.
    Callers that need a plain dict should call .model_dump().
    """
    if is_ambiguous:
        fe_status = "ambiguous"
    elif xsd_field_path:
        fe_status = "mapped"
    else:
        fe_status = "unmapped"

    return FieldMappingEntry(
        block_id=block_id or "",
        layout_type_id=layout_type_id,
        pdf_text=pdf_text,
        label_text=label_text,
        bbox=bbox,
        xsd_field_path=xsd_field_path,
        xsd_type=xsd_type,
        confidence=round(confidence, 4),
        is_ambiguous=is_ambiguous,
        candidates=candidates,
        page_number=page_number,
        pdf_id=pdf_id,
        is_table_cell=is_table_cell,
        from_table=from_table,
        detected_format=detected_format,
        smart_signals=smart_signals,
        semantic_confirmed=semantic_confirmed,
        name=label_text or pdf_text,
        path=xsd_field_path,
        type=xsd_type or "text",
        status=fe_status,
        isOptional=False,
        debug_section=debug_section,
        debug_top_candidate_path=debug_top_candidate_path,
        debug_top_candidate_score=debug_top_candidate_score,
        debug_scoped_paths_count=debug_scoped_paths_count,
    )


def _is_body_text_pair(pair: dict[str, Any]) -> bool:
    """True for unlabeled prose fragments that should not be sent to the LLM matcher.

    Body text pairs (source=stage_4_solo, empty label, plain prose) land in validated_pairs
    because Stage 3 classifies them as dynamic. Without filtering, they reach the LLM first
    (lower original_index), receive incorrect XSD paths (ClienteTelefone/ClienteEmail/CEP),
    and steal those paths via used_paths dedup before structured fields can claim them (RC-G).
    """
    label = (pair.get("label_text") or "").strip()
    value = (pair.get("value_text") or "").strip()
    detected_format = pair.get("detected_format")
    if label:
        return False
    if detected_format:
        return False
    words = value.split()
    # "WORD: rest of value" pattern indicates an embedded label — it's a structured field.
    if words and words[0].endswith(":"):
        return False
    return len(words) >= 4


async def _step_4_5_field_matching(
    validated_pairs: dict[str, list[dict[str, Any]]],
    field_tree: dict[str, Any] | None,
    intelligence: dict[str, Any],
    section_xsd_map: dict[str, dict[str, dict[str, Any]]],
    document_trees: dict[str, dict[str, Any]],
    openrouter_client: Any,
) -> tuple[list[FieldMappingEntry], list[str], dict[str, dict[str, Any]]]:
    """Batch field matching with section scoping and two-pass.

    Story 42.6 — returns list[FieldMappingEntry] instead of list[dict].
    Caller (stage4_field_mapping.run_stage4) serializes to plain dicts at context boundary.
    """
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    field_mappings: list[FieldMappingEntry] = []
    ambiguous_fields: list[str] = []
    confirmations: dict[str, dict[str, Any]] = {}
    _empty_bc = BlockClassification()
    # cross-layout dedup: each XSD path assigned at most once per job
    used_paths: set = set()

    for layout_id, pairs in validated_pairs.items():
        if not pairs:
            continue

        layout_intel = intelligence.get(layout_id, {})
        raw_bc = layout_intel.get("block_classifications", {})

        def _get_bc(block_id: str) -> BlockClassification:
            raw = raw_bc.get(block_id)
            if raw is None:
                return _empty_bc
            return BlockClassification(**raw) if isinstance(raw, dict) else raw

        if not flat_paths:
            for pair in pairs:
                bc = _get_bc(pair.get("value_block_id", ""))
                field_mappings.append(
                    _make_mapping_v2(
                        block_id=pair.get("value_block_id", ""),
                        layout_type_id=layout_id,
                        pdf_text=pair.get("value_text", ""),
                        label_text=pair.get("label_text", ""),
                        xsd_field_path="",
                        confidence=0.0,
                        is_ambiguous=False,
                        candidates=[],
                        bbox=pair.get("value_bbox"),
                        is_table_cell=getattr(bc, "is_table_cell", False),
                        from_table=getattr(bc, "from_table", False),
                        smart_signals=bc.smart_signals,
                        detected_format=pair.get("detected_format"),
                    )
                )
            continue

        layout_section_map = section_xsd_map.get(layout_id, {})

        section_groups = _group_pairs_by_section(pairs, layout_section_map, document_trees, layout_id)

        all_results: dict[int, list[dict[str, Any]]] = {}
        # Debug: record per-pair section and scoped path count for diagnosis
        pair_debug: dict[int, tuple[str, int]] = {}

        for section_name, group in section_groups.items():
            scoped_paths = layout_section_map.get(section_name, {}).get("child_paths", flat_paths)
            if not scoped_paths:
                scoped_paths = flat_paths
            xsd_node = layout_section_map.get(section_name, {}).get("xsd_node")

            section_context = (
                (f"This section is mapped to XSD node '{xsd_node}'. Focus on its children.")
                if xsd_node
                else "No section mapping available. Use all XSD fields."
            )

            # RC-G: use positional indices within the section so the LLM always
            # receives 0-based positions (0, 1, 2…) regardless of original_index values.
            # After the LLM call, remap local position → original_index before update
            # to prevent key collision when multiple sections share the same positions.
            # RC-I: body-text pairs (no label, no format, ≥4 words) are excluded from the
            # LLM call so they cannot steal XSD paths from structured fields.
            _local_idx_map: dict[int, int] = {}
            pairs_json = []
            _llm_pos = 0
            for _p in group:
                if _is_body_text_pair(_p):
                    continue
                pairs_json.append(
                    {
                        "index": _llm_pos,
                        "label": _p.get("label_text", ""),
                        "value": _p.get("value_text", ""),
                        "detected_format": _p.get("detected_format"),
                    }
                )
                _local_idx_map[_llm_pos] = _p["original_index"]
                _llm_pos += 1

            if openrouter_client:
                batch = await _llm_batch_match_scoped(pairs_json, scoped_paths, section_context, openrouter_client)
            else:
                batch = _fuzzy_batch_match(pairs_json, scoped_paths)

            batch = {_local_idx_map.get(k, k): v for k, v in batch.items()}
            all_results.update(batch)

            for _p in group:
                pair_debug[_p["original_index"]] = (section_name, len(scoped_paths))

            # DIAG: diagnose why TELEFONE/INSCRIÇÃO/etc. don't map
            _DIAG_LABELS = {"TELEFONE", "INSCRIÇÃO", "FORMA DE PAGAMENTO", "E-MAIL", "ENDEREÇO DE RELACIONAMENTO"}
            _DIAG_FMTS = {"phone", "email", "cep"}
            for _p in group:
                _lbl = (_p.get("label_text") or "").strip().upper()
                _fmt = _p.get("detected_format") or ""
                if _lbl in _DIAG_LABELS or _fmt in _DIAG_FMTS:
                    _idx = _p["original_index"]
                    _cands = batch.get(_idx, [])
                    logger.warning(
                        "[DIAG] layout=%s section=%r label=%r value=%r fmt=%r scoped_paths[:20]=%r candidates=%r",
                        layout_id,
                        section_name,
                        _p.get("label_text"),
                        _p.get("value_text"),
                        _fmt,
                        scoped_paths[:20],
                        _cands,
                    )

        # === PASS 1: Accept high-confidence matches ===
        # A path is claimed only if it hasn't been taken by a prior pair.
        # Without this check, two high-confidence pairs for the same path both
        # receive needs_pass2=False and emit duplicate xsd_field_paths (RCA 2026-04-13).
        # used_paths is declared OUTSIDE the layout loop (cross-layout dedup) — see below.
        pass1_entries: list[tuple[int, dict, list[dict[str, Any]], bool]] = []

        for i, pair in enumerate(pairs):
            candidates = all_results.get(i, [])
            best = candidates[0] if candidates else None

            if best and best["score"] >= HIGH_CONFIDENCE_THRESHOLD and best["path"] not in used_paths:
                used_paths.add(best["path"])
                pass1_entries.append((i, pair, candidates, False))
            else:
                pass1_entries.append((i, pair, candidates, True))

        # === PASS 2: Re-rank remaining without used paths ===
        # used_paths is updated after each assignment so that low-confidence pairs
        # processed later cannot claim a path already taken by an earlier pair in
        # this same pass (RCA 2026-04-13 — Pass 2 dedup missing).
        for i, pair, candidates, needs_pass2 in pass1_entries:
            orig_top = candidates[0] if candidates else None
            if needs_pass2 and candidates:
                filtered = [c for c in candidates if c["path"] not in used_paths]
                if filtered:
                    candidates = filtered

            best = candidates[0] if candidates else None
            is_ambiguous = False
            if best and len(candidates) >= 2:
                if candidates[0]["score"] - candidates[1]["score"] < AMBIGUITY_THRESHOLD:
                    is_ambiguous = True
                    ambiguous_fields.append(best["path"])

            best_score = best["score"] if best else 0.0
            best_path = (best["path"] or "") if best else ""
            xsd_path = best_path if best_score >= MINIMUM_MATCH_THRESHOLD else ""
            confidence = best_score

            # Claim this path so subsequent pairs in Pass 2 skip it
            if xsd_path:
                used_paths.add(xsd_path)

            bc = _get_bc(pair.get("value_block_id", ""))
            smart_signals = bc.smart_signals
            semantic_confirmed: str | None = None

            if bc.semantic == "likely_dynamic" and confidence >= HIGH_CONFIDENCE_THRESHOLD:
                semantic_confirmed = "dynamic"
                confirmations[pair.get("value_block_id", "")] = {
                    "original_semantic": "likely_dynamic",
                    "confirmed_semantic": "dynamic",
                    "xsd_path": xsd_path,
                    "xsd_confidence": confidence,
                }

            xsd_type = _get_xsd_type(field_tree, xsd_path) if (xsd_path and field_tree) else None

            _dbg_section, _dbg_scoped_count = pair_debug.get(i, ("", 0))
            field_mappings.append(
                _make_mapping_v2(
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
                    is_table_cell=getattr(bc, "is_table_cell", False),
                    from_table=getattr(bc, "from_table", False),
                    smart_signals=smart_signals,
                    semantic_confirmed=semantic_confirmed,
                    detected_format=pair.get("detected_format"),
                    debug_section=_dbg_section,
                    debug_top_candidate_path=orig_top["path"] if orig_top else None,
                    debug_top_candidate_score=orig_top["score"] if orig_top else None,
                    debug_scoped_paths_count=_dbg_scoped_count,
                )
            )

    return field_mappings, ambiguous_fields, confirmations
