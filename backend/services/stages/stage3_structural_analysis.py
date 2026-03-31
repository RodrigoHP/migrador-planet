"""Stage 3 — Structural Analysis (NER + GPT-4o Vision + Hierarchy).

Story 13.7 — Classifies blocks (label/dynamic), detects visual regions,
pairs label-value, and builds hierarchical document trees.

4 sub-steps:
  3.1 Multi-Example Analysis (statistical + regex + spaCy NER)
  3.2 Visual Analysis (GPT-4o Vision, 1 combined call per representative)
  3.3 Semantic Classification + Label-Value Pairing
  3.4 Hierarchy Builder (4 signals cascade)

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 7
Output contract: Section 3.3
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# spaCy — lazy-loaded, optional (mocked in tests)
# ---------------------------------------------------------------------------

_nlp = None  # None = not yet attempted; False = attempted and unavailable


def _get_nlp():
    """Load spaCy model lazily. Returns None if not available."""
    global _nlp
    if _nlp is False:
        return None  # Already attempted and failed — skip retry and warning
    if _nlp is not None:
        return _nlp
    try:
        import spacy

        _nlp = spacy.load("pt_core_news_lg")
        return _nlp
    except Exception:
        try:
            import spacy

            _nlp = spacy.load("pt_core_news_sm")
            return _nlp
        except Exception:
            logger.warning("spaCy model not available — NER layer disabled")
            _nlp = False  # Sentinel: mark as failed so we don't retry or re-log
            return None


# ---------------------------------------------------------------------------
# Sub-step 3.1 — Multi-Example Analysis (algorithmic + NER)
# ---------------------------------------------------------------------------

# Regex patterns for structured dynamic data
_DYNAMIC_PATTERNS: List[Tuple[str, str, float]] = [
    (r"\d{2}[/.\-]\d{2}[/.\-]\d{4}", "date", 0.8),
    (r"R\$\s*[\d.,]+", "currency", 0.9),
    (r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "cnpj", 0.95),
    (r"\d{3}\.\d{3}\.\d{3}-\d{2}", "cpf", 0.95),
    (r"\d{5}-?\d{3}", "cep", 0.85),
    (r"\(\d{2}\)\s*\d{4,5}-\d{4}", "phone", 0.9),
    (r"\d+[.,]\d{2}$", "decimal", 0.7),
]

_COMPILED_DYNAMIC_PATTERNS = [(re.compile(p), name, w) for p, name, w in _DYNAMIC_PATTERNS]


def _smart_classify(text: str) -> Tuple[Optional[bool], float, List[Tuple[str, float]]]:
    """Analyse text content to detect if it looks dynamic.

    Returns (is_likely_dynamic, score, signals).
    is_likely_dynamic: True (dynamic), False (label), None (uncertain).
    """
    signals: List[Tuple[str, float]] = []

    # Label signals (negative = pushes toward label)
    if text.rstrip().endswith(":"):
        signals.append(("ends_colon", -0.4))
    if len(text.strip()) < 20 and not any(c.isdigit() for c in text):
        signals.append(("short_no_digits", -0.2))

    # Layer 2: Regex
    for pattern, name, weight in _COMPILED_DYNAMIC_PATTERNS:
        if pattern.search(text):
            signals.append((f"regex_{name}", weight))

    # Layer 3: spaCy NER
    nlp = _get_nlp()
    if nlp is not None:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("PER", "LOC", "ORG"):
                    signals.append((f"ner_{ent.label_}", 0.7))
                elif ent.label_ == "MISC":
                    signals.append(("ner_misc", 0.4))
        except Exception:
            pass

    # Score: base 0.5, signals push toward label (0) or dynamic (1)
    score = 0.5
    for _, weight in signals:
        score += weight
    score = max(0.0, min(1.0, score))

    if score >= 0.7:
        return True, score, signals  # likely_dynamic
    elif score <= 0.3:
        return False, score, signals  # label
    else:
        return None, score, signals  # uncertain


def _run_3_1(
    clusters: List[Dict[str, Any]],
    raw_text_blocks: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Sub-step 3.1 — Multi-Example Analysis.

    3-layer classification cascade:
      1. Statistical: compare text at same position across PDFs
      2. Regex: CPF, CNPJ, dates, currency, CEP, phone
      3. spaCy NER: PER/LOC/ORG entities

    Returns dict keyed by cluster_id with classifications and classification_quality.
    """
    all_classifications: Dict[str, Any] = {}

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue  # skip _blank, _scanned

        position_map: Dict[Tuple[float, float], Dict[str, Any]] = {}

        for page_info in cluster["pages"]:
            page_key = f"{page_info['pdf_id']}:{page_info['page_index']}"
            page_blocks = raw_text_blocks.get(page_key, [])

            for block in page_blocks:
                pos_key = (round(block["x_center"], 2), round(block["y_center"], 2))
                if pos_key not in position_map:
                    position_map[pos_key] = {
                        "texts": [],
                        "pages": [],
                        "pdf_ids": set(),
                        "block": block,
                    }

                position_map[pos_key]["texts"].append(block["text"])
                position_map[pos_key]["pages"].append(page_key)
                position_map[pos_key]["pdf_ids"].add(page_info["pdf_id"])

        total_pages = len(cluster["pages"])
        total_pdfs = len({p["pdf_id"] for p in cluster["pages"]})
        classifications: List[Dict[str, Any]] = []

        for pos_key, info in position_map.items():
            presence_ratio = len(info["pages"]) / total_pages if total_pages > 0 else 1.0
            unique_texts = set(info["texts"])
            pdf_coverage = len(info["pdf_ids"]) / total_pdfs if total_pdfs > 0 else 1.0
            representative_text = info["texts"][0]

            c: Dict[str, Any] = {
                "position": list(pos_key),
                "presence_ratio": round(presence_ratio, 4),
                "pdf_coverage": round(pdf_coverage, 4),
                "sample_texts": sorted(unique_texts)[:5],
                "bbox_norm": info["block"].get("bbox_norm"),
            }

            # === LAYER 1: Statistical ===
            if len(unique_texts) == 1:
                c["classification"] = "label"
                c["confidence"] = 1.0
                c["method"] = "statistical"
            elif len(unique_texts) == len(info["pages"]):
                c["classification"] = "dynamic"
                c["confidence"] = 0.95
                c["method"] = "statistical"
            else:
                c["classification"] = "semi_dynamic"
                c["confidence"] = 0.80
                c["method"] = "statistical"

            # === LAYER 2+3: Smart override (NER + regex) ===
            if c["classification"] == "label":
                is_dynamic, smart_score, signals = _smart_classify(representative_text)
                if is_dynamic:
                    c["classification"] = "likely_dynamic"
                    c["confidence"] = round(smart_score, 4)
                    c["method"] = "smart_override"
                    c["smart_signals"] = [s[0] for s in signals if s[1] > 0]
                elif is_dynamic is None:
                    c["confidence"] = 0.50
                    c["method"] = "statistical_uncertain"
                    c["smart_signals"] = [s[0] for s in signals if s[1] > 0]

            # Stability
            if presence_ratio >= 0.90:
                c["stability"] = "stable"
            elif presence_ratio >= 0.10:
                c["stability"] = "variable"
            else:
                c["stability"] = "rare"

            # Variant
            if presence_ratio < 0.90 and pdf_coverage < 1.0:
                c["variant"] = "conditional"
                c["present_in_pdfs"] = sorted(info["pdf_ids"])
            elif presence_ratio < 0.90:
                c["variant"] = "optional"
            else:
                c["variant"] = "required"

            classifications.append(c)

        # classification_quality
        has_variation = any(
            len(set(info["texts"])) > 1 for info in position_map.values()
        )
        if total_pdfs <= 1:
            strength = "none"
        elif has_variation:
            strength = "strong"
        else:
            strength = "weak"

        smart_count = sum(1 for cl in classifications if cl.get("smart_signals"))
        uncertain_count = sum(
            1 for cl in classifications if cl.get("confidence", 1.0) < 0.70
        )

        all_classifications[cluster_id] = {
            "classifications": classifications,
            "classification_quality": {
                "total_pdfs": total_pdfs,
                "total_pages_in_cluster": total_pages,
                "statistical_strength": strength,
                "smart_override_count": smart_count,
                "uncertain_count": uncertain_count,
            },
        }

    return all_classifications


# ---------------------------------------------------------------------------
# Sub-step 3.2 — Visual Analysis (GPT-4o Vision)
# ---------------------------------------------------------------------------

_VISUAL_ANALYSIS_PROMPT = """\
Analyze this document page image. Return ONLY valid JSON with:

1. "regions": visual regions with bbox and type
2. For each region: "html_suggestion" (representative HTML snippet)
3. For chart_area: identify "chart_type" (bar|line|pie|doughnut|polarArea) and "confidence" (0-100)
4. For barcode_area: identify "barcode_format" (CODE128|CODE39|EAN13|EAN8|UPC|ITF|MSI) and "confidence" (0-100)
5. Compare your visual analysis against this programmatic extraction:
   {extraction_summary}

   Provide a "consistency_score" (0-100).

JSON structure:
{{
  "regions": [
    {{
      "type": "header|body|footer|sidebar|table_area|chart_area|barcode_area|image_area",
      "bbox": [x0, y0, x1, y1],
      "description": "brief description of content",
      "html_suggestion": "<suggested HTML for this region>",
      "chart_type": "bar",
      "barcode_format": "CODE128",
      "confidence": 85
    }}
  ],
  "consistency_score": 85,
  "consistency_notes": "brief notes on discrepancies"
}}
"""

VALID_REGION_TYPES = {
    "header",
    "body",
    "footer",
    "sidebar",
    "table_area",
    "chart_area",
    "barcode_area",
    "image_area",
}


def _summarize_extraction(page_data: Dict[str, Any]) -> str:
    """Build a brief summary of programmatic extraction for the prompt."""
    blocks = page_data.get("text_blocks", [])
    tables = page_data.get("tables", [])
    images = page_data.get("images", [])
    drawn = page_data.get("drawn_elements")

    parts = [f"Text blocks: {len(blocks)}"]
    if tables:
        parts.append(f"Tables: {len(tables)}")
    if images:
        parts.append(f"Images: {len(images)}")
    if drawn and isinstance(drawn, dict) and drawn.get("horizontal_lines"):
        parts.append(f"Horizontal lines: {len(drawn['horizontal_lines'])}")
    return "; ".join(parts)


def _parse_visual_response(raw_json: str) -> Dict[str, Any]:
    """Parse GPT-4o JSON response into validated structure."""
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:\w*)\s*\n?", "", raw_json.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return {"regions": [], "consistency_score": 0, "consistency_notes": "parse_error"}

    # Defensive: model returned array directly instead of object
    if isinstance(data, list):
        data = {"regions": data, "consistency_score": 0, "consistency_notes": "auto_wrapped"}

    regions = data.get("regions", [])
    validated_regions = []
    for r in regions:
        if not isinstance(r, dict):
            continue
        rtype = r.get("type", "body")
        if rtype not in VALID_REGION_TYPES:
            rtype = "body"
        bbox = r.get("bbox", [0, 0, 100, 100])
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0, 0, 100, 100]
        validated_regions.append({
            "type": rtype,
            "bbox": [int(v) if isinstance(v, (int, float)) else 0 for v in bbox],
            "description": str(r.get("description", "")),
            "html_suggestion": str(r.get("html_suggestion", "")),
            "chart_type": r.get("chart_type"),
            "barcode_format": r.get("barcode_format"),
            "confidence": r.get("confidence"),
        })

    score = data.get("consistency_score", 0)
    if not isinstance(score, (int, float)):
        score = 0

    return {
        "regions": validated_regions,
        "consistency_score": int(score),
        "consistency_notes": str(data.get("consistency_notes", "")),
    }


def _fallback_visual_analysis(
    page_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate fallback visual analysis using adaptive thresholds.

    Used when GPT-4o Vision is unavailable.
    Top 10% = header, bottom 10% = footer, rest = body.
    """
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)

    header_end = int(page_height * 0.10)
    footer_start = int(page_height * 0.90)

    regions = [
        {
            "type": "header",
            "bbox": [0, 0, int(page_width), header_end],
            "description": "Header region (threshold-based)",
            "html_suggestion": "<header></header>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
        {
            "type": "body",
            "bbox": [0, header_end, int(page_width), footer_start],
            "description": "Body region (threshold-based)",
            "html_suggestion": "<main></main>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
        {
            "type": "footer",
            "bbox": [0, footer_start, int(page_width), int(page_height)],
            "description": "Footer region (threshold-based)",
            "html_suggestion": "<footer></footer>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
    ]

    return {
        "regions": regions,
        "consistency_score": 50,
        "consistency_notes": "Fallback: threshold-based zones (no GPT-4o Vision)",
    }


async def _run_3_2(
    clusters: List[Dict[str, Any]],
    enriched_documents: List[Dict[str, Any]],
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Dict[str, Any]]:
    """Sub-step 3.2 — Visual Analysis.

    1 combined GPT-4o Vision call per representative page.
    MANDATORY but with fallback via handle_service_failure().
    """
    visual_analysis: Dict[str, Dict[str, Any]] = {}

    # Build page lookup: {pdf_id}:{page_index} -> page_data
    page_lookup: Dict[str, Dict[str, Any]] = {}
    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            pk = f"{pdf_id}:{page['page_index']}"
            page_lookup[pk] = page

    # Get or create vision client
    vision_client = context.get("vision_client")
    vision_available = vision_client is not None

    if not vision_available:
        import os

        vision_enabled = os.environ.get("VISION_AI_ENABLED", "true").lower() not in (
            "false", "0", "no", "off"
        )
        if not vision_enabled:
            context.setdefault("_pipeline_warnings", []).append(
                "Vision AI desabilitado via configuração (VISION_AI_ENABLED=false)."
            )
        else:
            try:
                from services.openrouter_client import get_client

                vision_client = get_client()
                vision_available = True
            except (ValueError, ImportError) as e:
                vision_available = False
                context.setdefault("_pipeline_warnings", []).append(
                    f"Vision AI desabilitado: {e}. "
                    "Análise estrutural rodando em modo fallback (~75% qualidade)."
                )

    api_calls = 0

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue

        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = page_lookup.get(page_key)

        if page_data is None:
            visual_analysis[page_key] = _fallback_visual_analysis({"height": 842.0, "width": 595.0})
            continue

        if not vision_available:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        screenshot_path = page_data.get("screenshot_path")
        if not screenshot_path:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        # Try GPT-4o Vision call
        try:
            from services.openrouter_client import load_image_as_base64, chat_with_vision

            image_b64 = load_image_as_base64(screenshot_path)
            extraction_summary = _summarize_extraction(page_data)
            prompt = _VISUAL_ANALYSIS_PROMPT.replace("{extraction_summary}", extraction_summary)

            raw_response = await chat_with_vision(
                vision_client,
                image_b64=image_b64,
                prompt=prompt,
            )
            result = _parse_visual_response(raw_response)
            api_calls += 1

            # Determine consistency level
            score = result["consistency_score"]
            if score >= 80:
                result["consistency_level"] = "consistent"
            elif score >= 50:
                result["consistency_level"] = "partial"
            else:
                result["consistency_level"] = "inconsistent"

            visual_analysis[page_key] = result

        except Exception as exc:
            logger.warning("Vision API call failed for %s: %s", page_key, exc)

            # Try handle_service_failure if job is available
            job = context.get("_job")
            if job is not None:
                try:
                    from services.pipeline_orchestrator_v2 import handle_service_failure

                    decision = await handle_service_failure(
                        context=context,
                        service_name="GPT-4o Vision",
                        stage_name="Stage 3.2 Visual Analysis",
                        error=exc,
                        fallback_description="Usar thresholds adaptativos (header 10%, footer 90%)",
                        impact_description="Qualidade reduzida (~75% vs ~95%)",
                        job=job,
                        emit_progress=emit_progress,
                    )
                    if decision == "retry":
                        # One retry
                        try:
                            raw_response = await chat_with_vision(
                                vision_client,
                                image_b64=image_b64,
                                prompt=prompt,
                            )
                            result = _parse_visual_response(raw_response)
                            api_calls += 1
                            score = result["consistency_score"]
                            result["consistency_level"] = (
                                "consistent" if score >= 80
                                else ("partial" if score >= 50 else "inconsistent")
                            )
                            visual_analysis[page_key] = result
                            continue
                        except Exception:
                            pass
                except Exception:
                    pass

            # Fallback
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)

    context["_vision_api_calls"] = context.get("_vision_api_calls", 0) + api_calls
    return visual_analysis


# ---------------------------------------------------------------------------
# Sub-step 3.3 — Semantic Classification + Label-Value Pairing
# ---------------------------------------------------------------------------


def _get_visual_zone(
    bbox: List[float],
    visual_analysis: Dict[str, Dict[str, Any]],
    page_key: str,
) -> Optional[str]:
    """Determine zone from visual_analysis regions."""
    va = visual_analysis.get(page_key)
    if not va or not va.get("regions"):
        return None

    block_cy = (bbox[1] + bbox[3]) / 2

    for region in va["regions"]:
        ry0 = region["bbox"][1]
        ry1 = region["bbox"][3]
        rtype = region["type"]
        if ry0 <= block_cy <= ry1 and rtype in ("header", "footer", "sidebar"):
            return rtype

    return None


def _get_zone_by_threshold(
    bbox: List[float],
    page_height: float,
) -> Optional[str]:
    """Fallback zone detection by threshold."""
    y_mid = (bbox[1] + bbox[3]) / 2
    relative = y_mid / page_height if page_height > 0 else 0.5

    if relative <= 0.10:
        return "header"
    if relative >= 0.90:
        return "footer"
    return None


def _find_position_match(
    block_bbox: List[float],
    page_width: float,
    page_height: float,
    position_classifications: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Find the classification from 3.1 that matches this block position."""
    if not position_classifications or page_width <= 0 or page_height <= 0:
        return None

    block_xc = ((block_bbox[0] + block_bbox[2]) / 2) / page_width
    block_yc = ((block_bbox[1] + block_bbox[3]) / 2) / page_height

    best = None
    best_dist = float("inf")
    tolerance = 0.03  # 3% normalized

    for pc in position_classifications:
        pos = pc.get("position", [0, 0])
        dx = abs(block_xc - pos[0])
        dy = abs(block_yc - pos[1])
        dist = (dx ** 2 + dy ** 2) ** 0.5

        if dist < best_dist and dx < tolerance and dy < tolerance:
            best = pc
            best_dist = dist

    return best


def _find_adjacent_value(
    label_block: Dict[str, Any],
    dynamics: List[Dict[str, Any]],
    page_width: float,
    page_height: float,
) -> Optional[Dict[str, Any]]:
    """Find the value block nearest to a label.

    Priority:
      1. Right of label (same Y, within 40% page width)
      2. Below label (same X, within 3.5% page height)
    """
    lx0, ly0, lx1, ly1 = label_block["bbox"]
    below_threshold = page_height * 0.035
    best = None
    best_dist = float("inf")

    for d in dynamics:
        if d.get("_paired"):
            continue
        dx0, dy0, dx1, dy1 = d["bbox"]

        # Right: same Y (within 5pts), X right after label
        if abs(dy0 - ly0) < 5 and dx0 > lx1 and dx0 - lx1 < page_width * 0.4:
            dist = dx0 - lx1
            if dist < best_dist:
                best, best_dist = d, dist

        # Below: same X (within 10pts), Y just below label
        elif abs(dx0 - lx0) < 10 and dy0 > ly1 and dy0 - ly1 < below_threshold:
            dist = dy0 - ly1 + 1000  # penalize to prefer "right"
            if dist < best_dist:
                best, best_dist = d, dist

    return best


def _run_3_3(
    enriched_documents: List[Dict[str, Any]],
    position_classifications_by_cluster: Dict[str, Any],
    visual_analysis: Dict[str, Dict[str, Any]],
    clusters: List[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Sub-step 3.3 — Semantic Classification + Label-Value Pairing.

    Returns (block_classifications, label_value_pairs).
    """
    block_classifications: Dict[str, Dict[str, Any]] = {}
    label_value_pairs: List[Dict[str, Any]] = []

    # Build cluster_id -> cluster lookup
    cluster_map = {c["cluster_id"]: c for c in clusters if not c["cluster_id"].startswith("_")}

    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            if not page.get("is_representative"):
                continue

            cluster_id = page.get("cluster_id", "")
            page_key = f"{pdf_id}:{page['page_index']}"
            page_width = page.get("width", 595.0)
            page_height = page.get("height", 842.0)

            # Get position classifications for this cluster
            cluster_data = position_classifications_by_cluster.get(cluster_id, {})
            pos_classifications = cluster_data.get("classifications", [])

            # Classify each block
            for block in page.get("text_blocks", []):
                block_id = block.get("id", str(uuid.uuid4()))

                # Match position to 3.1 classification
                pos_class = _find_position_match(
                    block["bbox"], page_width, page_height, pos_classifications
                )

                # Determine zone via visual analysis
                zone = _get_visual_zone(block["bbox"], visual_analysis, page_key)
                if zone is None:
                    zone = _get_zone_by_threshold(block["bbox"], page_height)

                # Build classification
                if pos_class:
                    semantic = pos_class.get("classification", "unknown")
                    stability = pos_class.get("stability", "unknown")
                    variant = pos_class.get("variant", "required")
                    confidence = pos_class.get("confidence", 0.50)
                    presence_ratio = pos_class.get("presence_ratio", 1.0)
                    pdf_coverage = pos_class.get("pdf_coverage", 1.0)
                    smart_signals = pos_class.get("smart_signals")
                else:
                    # Fallback: heuristic
                    text = block.get("text", "").strip()
                    if text.endswith(":"):
                        semantic = "label"
                    elif any(p.search(text) for p, _, _ in _COMPILED_DYNAMIC_PATTERNS):
                        semantic = "dynamic"
                    else:
                        semantic = "label" if len(text) <= 30 else "dynamic"
                    stability = "unknown"
                    variant = "required"
                    confidence = 0.50
                    presence_ratio = 1.0
                    pdf_coverage = 1.0
                    smart_signals = None

                # Zone override: header/footer text
                semantic_label = semantic
                if zone == "header":
                    semantic_label = "header"
                elif zone == "footer":
                    semantic_label = "footer_text"

                block["semantic_label"] = semantic_label
                block["_classification"] = semantic

                bc_entry: Dict[str, Any] = {
                    "semantic": semantic,
                    "stability": stability,
                    "variant": variant,
                    "presence_ratio": presence_ratio,
                    "pdf_coverage": pdf_coverage,
                    "confidence": confidence,
                    "field_pair": None,
                    "smart_signals": smart_signals,
                }

                # Propagate present_in_pdfs from position classification
                if pos_class and pos_class.get("present_in_pdfs"):
                    bc_entry["present_in_pdfs"] = pos_class["present_in_pdfs"]

                block_classifications[block_id] = bc_entry

            # Label-Value Pairing
            labels = [
                b for b in page.get("text_blocks", [])
                if block_classifications.get(b.get("id", ""), {}).get("semantic") == "label"
            ]
            dynamics = [
                b for b in page.get("text_blocks", [])
                if block_classifications.get(b.get("id", ""), {}).get("semantic")
                in ("dynamic", "semi_dynamic", "likely_dynamic")
            ]

            for label_block in labels:
                pair = _find_adjacent_value(label_block, dynamics, page_width, page_height)
                if pair:
                    lid = label_block.get("id", "")
                    vid = pair.get("id", "")
                    if lid in block_classifications:
                        block_classifications[lid]["field_pair"] = vid
                    if vid in block_classifications:
                        block_classifications[vid]["field_pair"] = lid
                    pair["_paired"] = True

                    label_value_pairs.append({
                        "label_block_id": lid,
                        "value_block_id": vid,
                        "confidence": min(
                            block_classifications.get(lid, {}).get("confidence", 0.5),
                            block_classifications.get(vid, {}).get("confidence", 0.5),
                        ),
                        "method": "adjacency",
                    })

    return block_classifications, label_value_pairs


# ---------------------------------------------------------------------------
# Sub-step 3.4 — Hierarchy Builder
# ---------------------------------------------------------------------------


def _zones_from_visual_regions(
    regions: List[Dict[str, Any]],
    page_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build zones from visual analysis regions."""
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)
    text_blocks = page_data.get("text_blocks", [])

    zone_map: Dict[str, Dict[str, Any]] = {}

    for region in regions:
        rtype = region["type"]
        # Map region types to zone types
        if rtype == "header":
            ztype = "header"
        elif rtype == "footer":
            ztype = "footer"
        elif rtype in ("body", "table_area", "image_area", "form_area"):
            ztype = "flow"
        elif rtype == "sidebar":
            ztype = "flow"  # treat sidebar as part of flow
        else:
            ztype = "flow"

        if ztype not in zone_map:
            zone_map[ztype] = {
                "type": ztype,
                "source": "visual",
                "bbox": list(region["bbox"]),
                "blocks": [],
            }
        else:
            # Expand bbox
            existing = zone_map[ztype]["bbox"]
            existing[0] = min(existing[0], region["bbox"][0])
            existing[1] = min(existing[1], region["bbox"][1])
            existing[2] = max(existing[2], region["bbox"][2])
            existing[3] = max(existing[3], region["bbox"][3])

    # Ensure flow zone exists
    if "flow" not in zone_map:
        header_end = zone_map.get("header", {}).get("bbox", [0, 0, 0, 0])[3] if "header" in zone_map else int(page_height * 0.10)
        footer_start = zone_map.get("footer", {}).get("bbox", [0, 0, 0, 0])[1] if "footer" in zone_map else int(page_height * 0.90)
        zone_map["flow"] = {
            "type": "flow",
            "source": "visual",
            "bbox": [0, header_end, int(page_width), footer_start],
            "blocks": [],
        }

    # Assign text blocks to zones
    zones = list(zone_map.values())
    for block in text_blocks:
        block_cy = (block["bbox"][1] + block["bbox"][3]) / 2
        assigned = False
        for zone in zones:
            zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
            if zy0 <= block_cy <= zy1:
                zone["blocks"].append(block)
                assigned = True
                break
        if not assigned:
            # Default to flow
            for zone in zones:
                if zone["type"] == "flow":
                    zone["blocks"].append(block)
                    break

    # Sort zones: header, flow, footer
    zone_order = {"header": 0, "flow": 1, "footer": 2}
    zones.sort(key=lambda z: zone_order.get(z["type"], 1))

    return zones


def _zones_from_thresholds(
    page_data: Dict[str, Any],
    header_pct: float = 0.10,
    footer_pct: float = 0.90,
) -> List[Dict[str, Any]]:
    """Fallback: build zones from adaptive thresholds."""
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)
    text_blocks = page_data.get("text_blocks", [])

    header_end = page_height * header_pct
    footer_start = page_height * footer_pct

    zones = [
        {
            "type": "header",
            "source": "threshold",
            "bbox": [0, 0, page_width, header_end],
            "blocks": [],
        },
        {
            "type": "flow",
            "source": "threshold",
            "bbox": [0, header_end, page_width, footer_start],
            "blocks": [],
        },
        {
            "type": "footer",
            "source": "threshold",
            "bbox": [0, footer_start, page_width, page_height],
            "blocks": [],
        },
    ]

    for block in text_blocks:
        block_cy = (block["bbox"][1] + block["bbox"][3]) / 2
        if block_cy <= header_end:
            zones[0]["blocks"].append(block)
        elif block_cy >= footer_start:
            zones[2]["blocks"].append(block)
        else:
            zones[1]["blocks"].append(block)

    return zones


def _split_by_drawn_lines(
    blocks: List[Dict[str, Any]],
    h_lines: List[float],
) -> List[Dict[str, Any]]:
    """Split blocks into sections using horizontal separator lines."""
    if not blocks:
        return []

    # Sort blocks by Y
    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
    sorted_lines = sorted(h_lines)

    sections = []
    current_blocks: List[Dict[str, Any]] = []

    line_idx = 0
    for block in sorted_blocks:
        block_cy = (block["bbox"][1] + block["bbox"][3]) / 2
        while line_idx < len(sorted_lines) and block_cy > sorted_lines[line_idx]:
            if current_blocks:
                sections.append({"blocks": current_blocks})
                current_blocks = []
            line_idx += 1
        current_blocks.append(block)

    if current_blocks:
        sections.append({"blocks": current_blocks})

    return sections


def _split_by_gap(
    blocks: List[Dict[str, Any]],
    gap_threshold: float,
) -> List[Dict[str, Any]]:
    """Split blocks into sections by proportional gap."""
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
    sections = []
    current_blocks = [sorted_blocks[0]]

    for i in range(1, len(sorted_blocks)):
        prev_bottom = sorted_blocks[i - 1]["bbox"][3]
        curr_top = sorted_blocks[i]["bbox"][1]
        gap = curr_top - prev_bottom

        if gap > gap_threshold:
            sections.append({"blocks": current_blocks})
            current_blocks = [sorted_blocks[i]]
        else:
            current_blocks.append(sorted_blocks[i])

    if current_blocks:
        sections.append({"blocks": current_blocks})

    return sections


def _get_horizontal_separators(
    drawn_elements: Optional[Any],
    zone_bbox: List[float],
) -> List[float]:
    """Extract horizontal line Y positions from drawn_elements within zone bbox."""
    if not drawn_elements:
        return []

    # drawn_elements may be a dict with "horizontal_lines" key or a list of elements
    if isinstance(drawn_elements, dict):
        h_lines = drawn_elements.get("horizontal_lines", [])
    elif isinstance(drawn_elements, list):
        h_lines = [
            el for el in drawn_elements
            if isinstance(el, dict) and el.get("orientation") == "horizontal"
        ]
    else:
        return []

    if not h_lines:
        return []

    zy0, zy1 = zone_bbox[1], zone_bbox[3]
    result = []

    for line in h_lines:
        y = line.get("y") or line.get("bbox", [0, 0, 0, 0])[1]
        if zy0 < y < zy1:
            result.append(y)

    return result


def _section_variant(
    blocks: List[Dict[str, Any]],
    block_classifications: Dict[str, Dict[str, Any]],
) -> str:
    """Determine section variant from child block variants."""
    variants = [
        block_classifications.get(b.get("id", ""), {}).get("variant", "required")
        for b in blocks
    ]
    if not variants:
        return "required"
    if all(v == "conditional" for v in variants):
        return "conditional"
    elif any(v in ("optional", "conditional") for v in variants):
        return "optional"
    return "required"


def _get_conditional_pdfs(
    blocks: List[Dict[str, Any]],
    block_classifications: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Get sorted list of pdf_ids where conditional blocks are present."""
    pdf_ids: Set[str] = set()
    for b in blocks:
        bc = block_classifications.get(b.get("id", ""), {})
        if bc.get("variant") == "conditional" and bc.get("present_in_pdfs"):
            pdf_ids.update(bc["present_in_pdfs"])
    return sorted(pdf_ids)


def _run_3_4(
    enriched_documents: List[Dict[str, Any]],
    block_classifications: Dict[str, Dict[str, Any]],
    visual_analysis: Dict[str, Dict[str, Any]],
    clusters: List[Dict[str, Any]],
    position_classifications_by_cluster: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Sub-step 3.4 — Hierarchy Builder.

    4 signals cascade: visual_regions -> drawn_elements -> grid_info -> proportional gap.
    Returns list of document_trees.
    """
    document_trees: List[Dict[str, Any]] = []

    # Build page lookup
    page_lookup: Dict[str, Dict[str, Any]] = {}
    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            pk = f"{pdf_id}:{page['page_index']}"
            page_lookup[pk] = page

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue

        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = page_lookup.get(page_key)

        if page_data is None:
            continue

        page_height = page_data.get("height", 842.0)
        page_width = page_data.get("width", 595.0)

        # Step 1: Determine zones
        va = visual_analysis.get(page_key)
        if va and va.get("regions") and va.get("consistency_score", 0) > 0:
            zones = _zones_from_visual_regions(va["regions"], page_data)
        else:
            zones = _zones_from_thresholds(page_data)

        # Step 2: Split zones into sections
        for zone in zones:
            blocks_in_zone = zone["blocks"]
            drawn = page_data.get("drawn_elements")

            # Signal 2: drawn_elements (horizontal lines as strong separators)
            h_lines = _get_horizontal_separators(drawn, zone["bbox"])

            if h_lines:
                sections = _split_by_drawn_lines(blocks_in_zone, h_lines)
            else:
                # Signal 4: Gap proportional (fallback)
                gap_threshold = page_height * 0.025
                sections = _split_by_gap(blocks_in_zone, gap_threshold)

            # Signal 3: Multi-column (grid_info)
            grid_info = page_data.get("grid_info")
            if grid_info and isinstance(grid_info, dict) and grid_info.get("columns", 1) > 1:
                # Mark sections as multi-column (used by Stage 5)
                for section in sections:
                    section["multi_column"] = True
                    section["column_positions"] = grid_info.get("column_positions", [])

            zone["sections"] = sections

        # Step 3: Assign images, charts, barcodes
        _assign_images_to_sections(zones, page_data.get("images", []))
        _assign_visual_elements_to_sections(zones, visual_analysis, page_key)

        # Step 4: Build tree
        tree = _build_tree(cluster_id, zones, block_classifications, page_data)

        document_trees.append({
            "cluster_id": cluster_id,
            "representative_page": {"pdf_id": rep["pdf_id"], "page_index": rep["page_index"]},
            "tree": tree,
        })

    return document_trees


def _assign_images_to_sections(
    zones: List[Dict[str, Any]],
    images: List[Dict[str, Any]],
) -> None:
    """Distribute images from Stage 2 into sections by position."""
    for img in images:
        bbox = img.get("bbox", [0, 0, 0, 0])
        img_cy = (bbox[1] + bbox[3]) / 2
        best_section = None
        best_overlap = 0

        for zone in zones:
            for section in zone.get("sections", []):
                if not section.get("blocks"):
                    continue
                sy0 = min(b["bbox"][1] for b in section["blocks"])
                sy1 = max(b["bbox"][3] for b in section["blocks"])
                overlap = max(0, min(bbox[3], sy1) - max(bbox[1], sy0))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_section = section

        if best_section is None:
            for zone in zones:
                zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
                if zy0 <= img_cy <= zy1 and zone.get("sections"):
                    best_section = zone["sections"][0]
                    break

        if best_section:
            best_section.setdefault("images", []).append(img)


def _assign_visual_elements_to_sections(
    zones: List[Dict[str, Any]],
    visual_analysis: Dict[str, Dict[str, Any]],
    page_key: str,
) -> None:
    """Convert GPT-4o visual elements (charts, barcodes) into section entries."""
    va = visual_analysis.get(page_key)
    if not va or not va.get("regions"):
        return

    for region in va["regions"]:
        rtype = region.get("type", "")
        if rtype not in ("chart_area", "barcode_area"):
            continue

        ry0, ry1 = region["bbox"][1], region["bbox"][3]
        region_cy = (ry0 + ry1) / 2

        for zone in zones:
            zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
            if zy0 <= region_cy <= zy1:
                for section in zone.get("sections", []):
                    if rtype == "chart_area":
                        section.setdefault("charts", []).append({
                            "bbox": region["bbox"],
                            "description": region.get("description", ""),
                            "chart_type": region.get("chart_type", "bar"),
                            "confidence": region.get("confidence", 50),
                        })
                    elif rtype == "barcode_area":
                        section.setdefault("barcodes", []).append({
                            "bbox": region["bbox"],
                            "description": region.get("description", ""),
                            "barcode_format": region.get("barcode_format", "CODE128"),
                            "confidence": region.get("confidence", 50),
                        })
                    break
                break


def _build_tree(
    cluster_id: str,
    zones: List[Dict[str, Any]],
    block_classifications: Dict[str, Dict[str, Any]],
    page_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Build hierarchical tree: document > page > zones > sections > fields."""
    root: Dict[str, Any] = {
        "id": f"root-{cluster_id}",
        "type": "document",
        "children": [{
            "type": "page",
            "children": [],
        }],
    }
    page_node = root["children"][0]

    # Build block lookup for pair resolution
    block_lookup: Dict[str, Dict[str, Any]] = {}
    for block in page_data.get("text_blocks", []):
        bid = block.get("id", "")
        if bid:
            block_lookup[bid] = block

    for zone in zones:
        zone_node: Dict[str, Any] = {
            "type": zone["type"],
            "source": zone.get("source", "threshold"),
            "children": [],
        }

        for section in zone.get("sections", []):
            section_blocks = section.get("blocks", [])
            variant = _section_variant(section_blocks, block_classifications)

            section_node: Dict[str, Any] = {
                "type": "section",
                "variant": variant,
                "children": [],
            }

            # Add conditional info
            if variant == "conditional":
                section_node["present_in_pdfs"] = _get_conditional_pdfs(
                    section_blocks, block_classifications
                )

            # Process blocks: paired label+value -> field node
            processed_ids: Set[str] = set()

            for block in section_blocks:
                bid = block.get("id", "")
                if bid in processed_ids:
                    continue

                bc = block_classifications.get(bid, {})

                if bc.get("field_pair") and bc.get("semantic") == "label":
                    # Label with pair -> field node
                    pair_id = bc["field_pair"]
                    pair_block = block_lookup.get(pair_id)
                    pair_bc = block_classifications.get(pair_id, {})

                    field_children = [
                        {"type": "label", "block_id": bid, "text": block.get("text", "")},
                    ]
                    if pair_block:
                        field_children.append(
                            {"type": "value", "block_id": pair_id, "text": pair_block.get("text", "")}
                        )
                        processed_ids.add(pair_id)

                    section_node["children"].append({
                        "type": "field",
                        "variant": bc.get("variant", "required"),
                        "children": field_children,
                    })
                    processed_ids.add(bid)

                elif bc.get("field_pair") and bc.get("semantic") != "label":
                    # Value that was paired — skip if already included via label
                    if bid not in processed_ids:
                        processed_ids.add(bid)
                    continue

                else:
                    # Standalone block
                    section_node["children"].append({
                        "type": bc.get("semantic", "unknown"),
                        "block_id": bid,
                        "text": block.get("text", ""),
                        "variant": bc.get("variant", "required"),
                    })
                    processed_ids.add(bid)

            # Tables
            for table in section.get("tables", []):
                table_node: Dict[str, Any] = {
                    "type": "table",
                    "table_id": table.get("table_id", str(uuid.uuid4())),
                    "children": [],
                }
                if table.get("headers"):
                    table_node["children"].append({
                        "type": "header_row",
                        "children": [{"type": "cell", "text": h, "children": []} for h in table["headers"]],
                    })
                for row in table.get("rows", []):
                    table_node["children"].append({
                        "type": "data_row",
                        "children": [{"type": "cell", "text": str(c), "children": []} for c in row],
                    })
                section_node["children"].append(table_node)

            # Images
            for img in section.get("images", []):
                section_node["children"].append({
                    "type": "image",
                    "image_path": img.get("path", ""),
                    "bbox": img.get("bbox", [0, 0, 0, 0]),
                    "bbox_valid": img.get("bbox_valid", True),
                    "format": img.get("format", "unknown"),
                    "children": [],
                })

            # Charts
            for chart in section.get("charts", []):
                section_node["children"].append({
                    "type": "chart",
                    "bbox": chart.get("bbox", [0, 0, 0, 0]),
                    "description": chart.get("description", ""),
                    "chart_type": chart.get("chart_type", "bar"),
                    "confidence": chart.get("confidence", 50),
                    "source": "visual_analysis",
                    "children": [],
                })

            # Barcodes
            for barcode in section.get("barcodes", []):
                section_node["children"].append({
                    "type": "barcode",
                    "bbox": barcode.get("bbox", [0, 0, 0, 0]),
                    "description": barcode.get("description", ""),
                    "barcode_format": barcode.get("barcode_format", "CODE128"),
                    "confidence": barcode.get("confidence", 50),
                    "source": "visual_analysis",
                    "children": [],
                })

            zone_node["children"].append(section_node)

        page_node["children"].append(zone_node)

    return root


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_stage3(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 3: Structural Analysis — 4 sub-steps.

    3.1 and 3.2 run in parallel.
    3.3 depends on both.
    3.4 depends on 3.3.
    """
    from services.pipeline_orchestrator_v2 import (
        make_sub_progress_event,
        compute_overall_progress,
    )

    stage, name = 3, "Structural Analysis"
    context["_current_stage"] = stage
    context["_current_stage_name"] = name

    clusters: List[Dict[str, Any]] = context.get("clusters", [])
    raw_text_blocks: Dict[str, List[Dict[str, Any]]] = context.get("_raw_text_blocks", {})
    enriched_documents: List[Dict[str, Any]] = context.get("enriched_documents", [])

    # --- Parallel: 3.1 + 3.2 ---
    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 0.05),
        sub_step="3.1+3.2 Parallel (Multi-Example + Visual)",
        sub_progress_pct=0.05,
    ))

    # 3.1 is synchronous (CPU-bound), wrap in executor
    loop = asyncio.get_event_loop()
    task_3_1 = loop.run_in_executor(None, _run_3_1, clusters, raw_text_blocks)
    task_3_2 = _run_3_2(clusters, enriched_documents, context, emit_progress)

    position_classifications, visual_analysis_result = await asyncio.gather(
        task_3_1, task_3_2
    )

    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 0.50),
        sub_step="3.1+3.2 Complete",
        sub_progress_pct=0.50,
    ))

    # --- Sequential: 3.3 ---
    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 0.55),
        sub_step="3.3 Semantic Classification",
        sub_progress_pct=0.55,
    ))

    block_classifications, label_value_pairs = _run_3_3(
        enriched_documents, position_classifications, visual_analysis_result, clusters
    )

    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 0.75),
        sub_step="3.3 Complete",
        sub_progress_pct=0.75,
    ))

    # --- Sequential: 3.4 ---
    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 0.80),
        sub_step="3.4 Hierarchy Builder",
        sub_progress_pct=0.80,
    ))

    _raw_trees = _run_3_4(
        enriched_documents,
        block_classifications,
        visual_analysis_result,
        clusters,
        position_classifications,
    )
    # Normalize to dict keyed by cluster_id — all downstream stages (4, 5) expect this format
    document_trees: Dict[str, Dict[str, Any]] = {
        entry.get("cluster_id", ""): entry.get("tree", {})
        for entry in _raw_trees
    }

    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 0.95),
        sub_step="3.4 Complete",
        sub_progress_pct=0.95,
    ))

    # --- Build intelligence with derived views ---
    intelligence: Dict[str, Any] = {}
    for cluster in clusters:
        cid = cluster["cluster_id"]
        if cid.startswith("_"):
            continue

        cluster_block_ids = set()
        # Find block_ids belonging to this cluster
        for doc in enriched_documents:
            for page in doc.get("pages", []):
                if page.get("cluster_id") == cid and page.get("is_representative"):
                    for block in page.get("text_blocks", []):
                        bid = block.get("id", "")
                        if bid:
                            cluster_block_ids.add(bid)

        cluster_bc = {
            bid: block_classifications[bid]
            for bid in cluster_block_ids
            if bid in block_classifications
        }

        labels_list = [bid for bid, bc in cluster_bc.items() if bc.get("semantic") == "label"]
        dynamic_list = [
            bid for bid, bc in cluster_bc.items()
            if bc.get("semantic") in ("dynamic", "semi_dynamic", "likely_dynamic")
        ]
        optional_list = [
            bid for bid, bc in cluster_bc.items()
            if bc.get("variant") in ("optional",)
        ]
        conditional_list = [
            bid for bid, bc in cluster_bc.items()
            if bc.get("variant") == "conditional"
        ]

        cluster_quality = position_classifications.get(cid, {}).get(
            "classification_quality",
            {
                "total_pdfs": 0,
                "total_pages_in_cluster": 0,
                "statistical_strength": "none",
                "smart_override_count": 0,
                "uncertain_count": 0,
            },
        )

        intelligence[cid] = {
            "block_classifications": cluster_bc,
            "labels": labels_list,
            "dynamic_fields": dynamic_list,
            "optional_fields": optional_list,
            "conditional_fields": conditional_list,
            "classification_quality": cluster_quality,
        }

    # Derive layout_types from intelligence + clusters for Stage 5 consumption.
    # Each item must have: id, cluster_id, name, page_height_pts, page_width_pts.
    # Page dimensions come from the representative page in enriched_documents.
    _page_dims: Dict[str, Dict[str, float]] = {}
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            cid = page.get("cluster_id", "")
            if cid and page.get("is_representative") and cid not in _page_dims:
                _page_dims[cid] = {
                    "width": float(page.get("width", 595.0)),
                    "height": float(page.get("height", 842.0)),
                }

    layout_types: List[Dict[str, Any]] = []
    for cluster in clusters:
        cid = cluster["cluster_id"]
        if cid.startswith("_"):
            continue
        dims = _page_dims.get(cid, {"width": 595.0, "height": 842.0})
        layout_types.append({
            "id": cid,
            "cluster_id": cid,
            "name": cid,
            "page_width_pts": dims["width"],
            "page_height_pts": dims["height"],
            "page_count": cluster.get("page_count", len(cluster.get("pages", []))),
        })

    context["layout_types"] = layout_types

    # Write to context
    context["document_trees"] = document_trees
    context["intelligence"] = intelligence
    context["visual_analysis"] = visual_analysis_result
    context["label_value_pairs"] = label_value_pairs

    # Stage 3 result summary
    context["stage_3_result"] = {
        "document_trees": document_trees,
        "intelligence": intelligence,
    }

    total_blocks = sum(
        len(v.get("block_classifications", {}))
        for v in intelligence.values()
    )
    total_labels = sum(len(v.get("labels", [])) for v in intelligence.values())
    total_dynamic = sum(len(v.get("dynamic_fields", [])) for v in intelligence.values())
    total_pairs = len(label_value_pairs)

    await emit_progress(make_sub_progress_event(
        stage=stage,
        stage_name=name,
        status="running",
        progress_pct=compute_overall_progress(stage, 1.0),
        sub_step="3.done",
        sub_progress_pct=1.0,
        summary={
            "total_blocks_classified": total_blocks,
            "total_labels": total_labels,
            "total_dynamic": total_dynamic,
            "total_pairs": total_pairs,
            "trees_built": len(document_trees),
            "vision_api_calls": context.get("_vision_api_calls", 0),
        },
    ))

    return context
