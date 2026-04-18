"""Stage 1 — Ensemble Voting Signals (Stories 48.10, 48.11).

Four structure-only signals invariant to dynamic content:
  1. masked_phash         — pHash of thumbnail with text blocks grayed out
  2. font_signature       — frozenset of (y_bucket, font_name, size_bucket) tuples
  3. struct_sequence      — normalized (x0, y0, width) sequence for edit distance
  4. markdown_fingerprint — SHA256 prefix of normalized pymupdf4llm markdown

All functions accept fitz.Page and return pure Python objects.
Calibrated thresholds (from spike 48.9):
  T_PHASH  = 16   hamming distance <= 16 → SAME
  T_FONT   = 0.47 Jaccard >= 0.47 → SAME
  T_STRUCT = 0.65 edit distance <= 0.65 → SAME
  T_MDHASH = exact match (True/False) — hash equality after normalization
"""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import fitz

# Calibrated thresholds from spike 48.9
T_PHASH: int = 16
T_FONT: float = 0.47
T_STRUCT: float = 0.65

# Ensemble score mapping: matches_count → similarity float (4-signal scale)
ENSEMBLE_SCORES: dict[int, float] = {4: 0.97, 3: 0.90, 2: 0.75, 1: 0.35, 0: 0.05}

# Normalization patterns for markdown fingerprint (same as ABSTRACTION_PATTERNS but for markdown text)
_MD_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"), "[CPF]"),
    (re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"), "[CNPJ]"),
    (re.compile(r"\d{2}/\d{2}/\d{4}"), "[DATE]"),
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "[DATE]"),
    (re.compile(r"R\$\s*[\d.,]+"), "[BRL]"),
    (re.compile(r"\d[\d.,]*"), "[NUM]"),
]


def masked_phash(page: fitz.Page, size: int = 128):
    """pHash of thumbnail with text blocks replaced by gray (200,200,200).

    Returns imagehash.ImageHash or None if imagehash is unavailable.
    Masking text blocks makes the hash invariant to dynamic content changes
    while preserving structural layout (logos, barcodes, borders remain visible).
    """
    try:
        import fitz as _fitz
        import imagehash
        from PIL import Image, ImageDraw

        scale = size / max(page.rect.width, page.rect.height, 1.0)
        pix = page.get_pixmap(matrix=_fitz.Matrix(scale, scale))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)
        sw = pix.width / (page.rect.width or 1.0)
        sh = pix.height / (page.rect.height or 1.0)
        for block in page.get_text("blocks"):
            if int(block[6]) == 0:  # text block only
                x0 = block[0] * sw
                y0 = block[1] * sh
                x1 = block[2] * sw
                y1 = block[3] * sh
                draw.rectangle([x0, y0, x1, y1], fill=(200, 200, 200))
        return imagehash.phash(img.convert("L"))
    except Exception:
        return None


def markdown_fingerprint(page: fitz.Page) -> str | None:
    """SHA256[:16] of normalized pymupdf4llm markdown for the page.

    Replaces CPF, CNPJ, dates, amounts, and numbers with tokens so the
    fingerprint captures structural layout (headings, tables, labels) but
    is invariant to dynamic field values.
    Returns None if pymupdf4llm is unavailable.
    """
    try:
        import pymupdf4llm

        md = pymupdf4llm.to_markdown(page.parent, pages=[page.number])
        for pattern, token in _MD_PATTERNS:
            md = pattern.sub(token, md)
        digest = hashlib.sha256(md.encode("utf-8")).hexdigest()[:16]
        return digest
    except Exception:
        return None


def font_signature(page: fitz.Page) -> frozenset | None:
    """Frozenset of (y_bucket, font_name, size_bucket) for Jaccard similarity.

    y_bucket normalised to page height in 0.1 increments.
    size_bucket rounded to nearest 0.5pt.
    Returns None on error.
    """
    try:
        sig: set[tuple] = set()
        h = page.rect.height or 1.0
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    y_bucket = round(span["origin"][1] / h, 1)
                    size_bucket = round(span["size"] * 2) / 2
                    sig.add((y_bucket, span.get("font", ""), size_bucket))
        return frozenset(sig)
    except Exception:
        return None


def struct_sequence(blocks_raw: list) -> list[tuple]:
    """Normalised (x0, y0, width) sequence from raw block list (page.get_text('blocks')).

    Sorted top-to-bottom then left-to-right. Used with SequenceMatcher for
    edit distance — invariant to text content, sensitive to layout structure.
    """
    page_w = max((b[2] for b in blocks_raw if int(b[6]) == 0), default=1.0) or 1.0
    page_h = max((b[3] for b in blocks_raw if int(b[6]) == 0), default=1.0) or 1.0
    seq = []
    for b in sorted(blocks_raw, key=lambda b: (b[1], b[0])):
        if int(b[6]) == 0:
            seq.append(
                (
                    round(b[0] / page_w, 2),
                    round(b[1] / page_h, 2),
                    round((b[2] - b[0]) / page_w, 2),
                )
            )
    return seq


def jaccard(sig_a: frozenset, sig_b: frozenset) -> float:
    """Jaccard similarity between two frozensets."""
    union = sig_a | sig_b
    if not union:
        return 1.0
    return len(sig_a & sig_b) / len(union)


def edit_distance(seq_a: list, seq_b: list) -> float:
    """Normalised edit distance (0=identical, 1=totally different)."""
    if not seq_a and not seq_b:
        return 0.0
    if not seq_a or not seq_b:
        return 1.0
    return 1.0 - SequenceMatcher(None, seq_a, seq_b).ratio()


def ensemble_match_count(
    phash_a,
    phash_b,
    font_a: frozenset | None,
    font_b: frozenset | None,
    seq_a: list,
    seq_b: list,
    md_a: str | None = None,
    md_b: str | None = None,
) -> int:
    """Count how many of the 4 signals agree that a and b are SAME template.

    Returns 0-4.  Signals with missing data (None/empty) are skipped — only
    available signals vote.  Returns -1 if zero signals are available.
    """
    votes = 0
    total = 0

    # Signal 1: pHash
    if phash_a is not None and phash_b is not None:
        total += 1
        dist = int(phash_a - phash_b)
        if dist <= T_PHASH:
            votes += 1

    # Signal 2: Font Jaccard
    if font_a is not None and font_b is not None:
        total += 1
        if jaccard(font_a, font_b) >= T_FONT:
            votes += 1

    # Signal 3: Structural edit distance
    if seq_a and seq_b:
        total += 1
        if edit_distance(seq_a, seq_b) <= T_STRUCT:
            votes += 1

    # Signal 4: Markdown fingerprint — one-sided bonus signal.
    # Match → strong positive evidence (SAME vote).
    # Mismatch → abstain (normalization is incomplete; mismatch ≠ DIFF evidence).
    # Only 5.7% of SAME pairs match exactly (spike 48.9 re-calibration 2026-04-18).
    if md_a is not None and md_b is not None and md_a == md_b:
        total += 1
        votes += 1

    if total == 0:
        return -1  # no signals available → caller should fallback
    return votes


def ensemble_to_similarity(match_count: int, total_signals: int = 4) -> float:
    """Map voting result to similarity float in [0, 1].

    Matches ENSEMBLE_SCORES for 4 signals.  Falls back proportionally
    if fewer signals are available (scales to 4-signal basis).
    """
    if match_count < 0:
        return -1.0  # signal: use fallback
    # Normalise to 4-signal scale
    if total_signals > 0 and total_signals != 4:
        match_count = round(match_count * 4 / total_signals)
    return ENSEMBLE_SCORES.get(match_count, 0.05)
