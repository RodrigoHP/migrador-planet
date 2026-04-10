"""Stage 3 — Multi-Example Analysis sub-module (Step 3.1).

Responsibilities:
  - Statistical classification of text blocks across PDFs
  - Regex-based dynamic pattern detection
  - spaCy NER layer for entity detection
  - Stability and variant assignment

Story 41.3 — extracted from stage3_structural_analysis.py
"""

from __future__ import annotations

import logging
from typing import Any

from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy — lazy-loaded, optional (mocked in tests)
# ---------------------------------------------------------------------------

_nlp = None  # None = not yet attempted; False = attempted and unavailable


def _get_nlp():
    """Load spaCy model lazily. Returns None if not available.

    Backward-compat: if ``stage3_structural_analysis._nlp`` has been patched
    (e.g. in tests), that value takes precedence over the local cache.
    """
    global _nlp
    # Allow test patching via the orchestrator module's namespace.
    try:
        import sys

        _orch = sys.modules.get("services.stages.stage3_structural_analysis")
        if _orch is not None:
            orch_nlp = getattr(_orch, "_nlp", None)
            if orch_nlp is not None and orch_nlp is not False:
                return orch_nlp
    except Exception:
        pass
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
# Smart classification (regex + NER)
# ---------------------------------------------------------------------------


def _smart_classify(text: str) -> tuple[bool | None, float, list[tuple[str, float]]]:
    """Analyse text content to detect if it looks dynamic.

    Returns (is_likely_dynamic, score, signals).
    is_likely_dynamic: True (dynamic), False (label), None (uncertain).
    """
    signals: list[tuple[str, float]] = []

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


# ---------------------------------------------------------------------------
# Sub-step 3.1 — Multi-Example Analysis
# ---------------------------------------------------------------------------


def _run_3_1(
    clusters: list[dict[str, Any]],
    raw_text_blocks: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Sub-step 3.1 — Multi-Example Analysis.

    3-layer classification cascade:
      1. Statistical: compare text at same position across PDFs
      2. Regex: CPF, CNPJ, dates, currency, CEP, phone
      3. spaCy NER: PER/LOC/ORG entities

    Returns dict keyed by cluster_id with classifications and classification_quality.
    """
    all_classifications: dict[str, Any] = {}

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue  # skip _blank, _scanned

        position_map: dict[tuple[float, float], dict[str, Any]] = {}

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
        classifications: list[dict[str, Any]] = []

        for pos_key, info in position_map.items():
            presence_ratio = len(info["pages"]) / total_pages if total_pages > 0 else 1.0
            unique_texts = set(info["texts"])
            pdf_coverage = len(info["pdf_ids"]) / total_pdfs if total_pdfs > 0 else 1.0
            representative_text = info["texts"][0]

            c: dict[str, Any] = {
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
        has_variation = any(len(set(info["texts"])) > 1 for info in position_map.values())
        if total_pdfs <= 1:
            strength = "none"
        elif has_variation:
            strength = "strong"
        else:
            strength = "weak"

        smart_count = sum(1 for cl in classifications if cl.get("smart_signals"))
        uncertain_count = sum(1 for cl in classifications if cl.get("confidence", 1.0) < 0.70)

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
