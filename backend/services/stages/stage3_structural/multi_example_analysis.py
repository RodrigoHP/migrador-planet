"""Stage 3 — Multi-Example Analysis sub-module (Step 3.1).

Responsibilities:
  - Statistical classification of text blocks across PDFs
  - Regex-based dynamic pattern detection
  - spaCy NER layer for entity detection
  - Stability and variant assignment

Story 41.3 — extracted from stage3_structural_analysis.py
Story 48.14 — body-text filter: reclassify likely_dynamic letter prose as static_body_text
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.stages.stage3_structural.constants import _COMPILED_DYNAMIC_PATTERNS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy — lazy-loaded, optional (mocked in tests)
# SYS-018: Expected model name and version for validation at startup / health check.
# ---------------------------------------------------------------------------

# Expected spaCy model (preferred = lg, fallback = sm; both ship at version 3.8.0)
_EXPECTED_SPACY_MODEL = "pt_core_news_sm"  # minimum acceptable model
_EXPECTED_SPACY_VERSION = "3.8.0"  # from requirements.txt pinned version

_nlp: Any = None  # None = not yet attempted; False = attempted and unavailable


def _validate_spacy_model(nlp) -> None:
    """SYS-018: Validate the loaded spaCy model matches the expected version.

    Logs a warning (never raises) when:
    - Model name differs from expected (e.g., wrong language or size)
    - Model version differs from the pinned version in requirements.txt

    Graceful: any validation failure is logged and swallowed — NER continues.
    """
    try:
        meta = getattr(nlp, "meta", {})
        loaded_version = meta.get("version", "unknown")
        loaded_full = meta.get("lang", "?") + "_" + meta.get("name", "?")

        # Accept both sm and lg variants (lg is preferred, sm is the fallback)
        accepted_names = {"pt_core_news_sm", "pt_core_news_lg"}
        if loaded_full not in accepted_names:
            logger.warning(
                "SYS-018: spaCy model mismatch — loaded '%s' v%s, expected one of %s v%s. "
                "NER layer continues with loaded model.",
                loaded_full,
                loaded_version,
                sorted(accepted_names),
                _EXPECTED_SPACY_VERSION,
            )
        elif loaded_version != _EXPECTED_SPACY_VERSION:
            logger.warning(
                "SYS-018: spaCy model version mismatch — loaded '%s' v%s, expected v%s. "
                "NER layer continues. Update requirements.txt if this is intentional.",
                loaded_full,
                loaded_version,
                _EXPECTED_SPACY_VERSION,
            )
        else:
            logger.debug("SYS-018: spaCy model OK — '%s' v%s", loaded_full, loaded_version)
    except Exception as exc:
        logger.debug("SYS-018: Could not validate spaCy model metadata: %s", exc)


def validate_spacy_on_startup() -> None:
    """SYS-018: Attempt to load spaCy model and validate version at startup.

    Called from the FastAPI lifespan handler.  Logs warnings but never raises
    so that a missing/mismatched model does not prevent server startup.
    """
    nlp = _get_nlp()
    if nlp is None or nlp is False:
        logger.warning(
            "SYS-018: spaCy model not available at startup — NER layer disabled. "
            "Install pt_core_news_sm==%s (see requirements.txt).",
            _EXPECTED_SPACY_VERSION,
        )
    else:
        _validate_spacy_model(nlp)


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
            if orch_nlp is False:
                return None  # test patched to False → simulate unavailable
            if orch_nlp is not None:
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
        # SYS-018: Validate model version after successful load
        _validate_spacy_model(_nlp)
        return _nlp
    except Exception:
        try:
            import spacy

            _nlp = spacy.load("pt_core_news_sm")
            # SYS-018: Validate model version after successful load
            _validate_spacy_model(_nlp)
            return _nlp
        except Exception:
            logger.warning("spaCy model not available — NER layer disabled")
            _nlp = False  # Sentinel: mark as failed so we don't retry or re-log
            return None


# ---------------------------------------------------------------------------
# Body-text filter (Story 48.14 — RC-A)
# Prevents letter-prose fields from reaching Stage 4 as XSD binding candidates.
# ---------------------------------------------------------------------------

# Minimal Portuguese stopword set used when spaCy is unavailable.
# Threshold: stopword_ratio > _BODY_TEXT_STOPWORD_THRESHOLD (0.25)
# chosen so that:
#   - "Pedimos que você verifique seus dados"  → ratio ≈ 0.50  ✓ filtered
#   - "pessoais e planos contratados"           → ratio ≈ 0.25  ✓ filtered (boundary)
#   - "Conforme seu pedido, apresentamos"       → ratio ≈ 0.25  ✓ filtered
#   - "(demais localidades) e 0800 771 5472"    → ratio ≈ 0.14  — relies on spaCy LOC
#   - "de contato disponíveis no site"          → ratio ≈ 0.50  ✓ filtered
_PT_STOPWORDS: frozenset[str] = frozenset(
    {
        # articles
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "uns",
        "umas",
        # prepositions
        "de",
        "do",
        "da",
        "dos",
        "das",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "por",
        "pelo",
        "pela",
        "pelos",
        "pelas",
        "para",
        "com",
        "sem",
        "sobre",
        "sob",
        "entre",
        "até",
        "após",
        "ante",
        # conjunctions
        "e",
        "ou",
        "mas",
        "porém",
        "pois",
        "que",
        "se",
        "nem",
        "porque",
        "como",
        "quando",
        "embora",
        "enquanto",
        "logo",
        "porem",
        # pronouns
        "eu",
        "tu",
        "ele",
        "ela",
        "nós",
        "vós",
        "eles",
        "elas",
        "me",
        "te",
        "se",
        "nos",
        "vos",
        "lhe",
        "lhes",
        "meu",
        "minha",
        "meus",
        "minhas",
        "seu",
        "sua",
        "seus",
        "suas",
        "nosso",
        "nossa",
        "nossos",
        "nossas",
        "você",
        "vocês",
        # adverbs / discourse
        "não",
        "sim",
        "já",
        "mais",
        "menos",
        "muito",
        "pouco",
        "bem",
        "mal",
        "aqui",
        "ali",
        "lá",
        "ainda",
        "também",
        "sempre",
        "nunca",
        "talvez",
        "assim",
        "então",
        "apenas",
        # common verbs (lowercased)
        "é",
        "são",
        "foi",
        "foram",
        "está",
        "estão",
        "tem",
        "têm",
        "ter",
        "ser",
        "estar",
        "sendo",
        "tendo",
        "tendo",
        "pedimos",
        "verifique",
        "apresentamos",
        "disponíveis",
    }
)

_BODY_TEXT_STOPWORD_THRESHOLD: float = 0.25  # stopword_ratio >= 0.25 → prose

# Structured-field patterns — any match EXEMPTS the text from body-text filtering.
# NOTE: keep patterns anchored where possible to avoid matching sub-strings.
#   e.g. ^\d{5}-\d{3}$ matches CEP but NOT "JARDIM PAIQUERE, VALINHOS, SP"
_BODY_TEXT_EXEMPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\(\d{2}\)\s*\d{4,5}-\d{4}"),  # phone: (19) 98189-4732
    re.compile(r"[\w.+-]+@[\w-]+\.\w+"),  # e-mail
    re.compile(r"\d{2}/\d{2}/\d{4}"),  # date: dd/mm/yyyy
    re.compile(r"R\$\s*[\d.,]+"),  # currency: R$ 591,70
    re.compile(r"^\d{5}-\d{3}$"),  # CEP: 13271-608
    re.compile(r"^\d{8,15}$"),  # certificate/apólice number
    re.compile(r"^\d{1,3}[.,]\d{2}$"),  # decimal value: 591,70
    re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"),  # CPF
    re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"),  # CNPJ
    re.compile(  # street address (value fields)
        r"^(?:RUA|AV\.?|AVENIDA|TRAVESSA|AL\.?|ALAMEDA|ROD\.?|RODOVIA|PRACA|PC|ESTRADA|EST)\s",
        re.IGNORECASE,
    ),
]


def _matches_structured_exempt(text: str) -> bool:
    """Return True if text contains a structured-field pattern (must NOT be filtered)."""
    stripped = text.strip()
    return any(pat.search(stripped) for pat in _BODY_TEXT_EXEMPT_PATTERNS)


def _is_body_text(text: str, nlp=None) -> bool:
    """Return True if text looks like letter-prose and should be static_body_text.

    Two-layer detection (Story 48.14, threshold: _BODY_TEXT_STOPWORD_THRESHOLD):
      Layer 1 — stopword ratio via embedded PT list (works without spaCy).
      Layer 2 — spaCy LOC/PER entity detection for all-caps location strings
                 that have low stopword ratio (e.g. "JARDIM PAIQUERE, VALINHOS, SP").

    A text is body-text only when ALL of the following hold:
      - Has >= 4 space-separated tokens (avoids filtering short field values)
      - Does NOT match any _BODY_TEXT_EXEMPT_PATTERNS
      - Stopword ratio > _BODY_TEXT_STOPWORD_THRESHOLD  OR  spaCy flags LOC entity
    """
    tokens = text.split()
    if len(tokens) < 4:
        return False

    # Layer 1: stopword ratio (case-insensitive, embedded list)
    content_tokens = [t.strip(".,;:!?()'\"").lower() for t in tokens if t.strip(".,;:!?()'\"")]
    if not content_tokens:
        return False
    stop_count = sum(1 for t in content_tokens if t in _PT_STOPWORDS)
    stopword_ratio = stop_count / len(content_tokens)

    if stopword_ratio >= _BODY_TEXT_STOPWORD_THRESHOLD:
        return True

    # Layer 2: spaCy LOC entity (catches city/state strings like "JARDIM X, VALINHOS, SP")
    if nlp is not None:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("LOC", "GPE", "PER"):
                    return True
        except Exception:
            pass

    return False


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
    has_colon = text.rstrip().endswith(":")
    is_short_no_digits = len(text.strip()) < 20 and not any(c.isdigit() for c in text)
    if has_colon:
        signals.append(("ends_colon", -0.4))
    if is_short_no_digits:
        signals.append(("short_no_digits", -0.2))

    # Layer 2: Regex
    regex_matched = False
    for pattern, name, weight in _COMPILED_DYNAMIC_PATTERNS:
        if pattern.search(text):
            signals.append((f"regex_{name}", weight))
            regex_matched = True

    # Layer 3: spaCy NER — skip for definitive labels:
    #   - text ending with ":" is always a field label
    #   - short text with no digits and no dynamic pattern is likely a domain label
    skip_ner = has_colon or (is_short_no_digits and not regex_matched)
    nlp = None if skip_ner else _get_nlp()
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
            # Skip when only 1 PDF — statistical signal is absent, NER has false-positive rate
            # on static org names (e.g. "Equipe MAG Seguros" → ORG entity).
            if c["classification"] == "label" and total_pdfs > 1:
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

            # === LAYER 4: Body-text filter (Story 48.14 — RC-A) ===
            # Downgrade dynamic/semi_dynamic/likely_dynamic fields that are letter prose.
            # Applied after statistical + smart_override layers so that structured fields
            # already classified by regex/NER still reach Stage 4.
            # Structured fields (phone, email, CEP, currency, cert numbers) are exempt.
            _DYNAMIC_CLASSES = {"dynamic", "semi_dynamic", "likely_dynamic"}
            if c["classification"] in _DYNAMIC_CLASSES and not _matches_structured_exempt(representative_text):
                nlp = _get_nlp()
                if _is_body_text(representative_text, nlp):
                    c["classification"] = "static_body_text"
                    c["method"] = "body_text_filter"
                    c["smart_signals"] = (c.get("smart_signals") or []) + ["body_text_filtered"]

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
