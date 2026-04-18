"""Tests for Stage 1 Ensemble Voting Signals (Story 48.10).

Covers:
- ensemble_match_count: SAME pair returns 3/3
- ensemble_match_count: DIFF pair returns 0/3
- ensemble_similarity: fallback when signals absent
- signals module: functions return expected types
- PageInfo: phash/font_sig/struct_seq fields exist
"""

from __future__ import annotations

import pytest

from services.stages.stage1_clustering.page_preprocessing import PageInfo
from services.stages.stage1_clustering.signals import (
    ENSEMBLE_SCORES,
    T_FONT,
    T_PHASH,
    T_STRUCT,
    edit_distance,
    ensemble_match_count,
    ensemble_to_similarity,
    jaccard,
)

# ---------------------------------------------------------------------------
# Helpers — synthetic signal data
# ---------------------------------------------------------------------------


def _make_phash_mock(value: int = 0):
    """Return an object that supports '-' operator like imagehash.ImageHash."""

    class FakeHash:
        def __init__(self, v):
            self.v = v

        def __sub__(self, other):
            return abs(self.v - other.v)

    return FakeHash(value)


# ---------------------------------------------------------------------------
# Unit: jaccard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_jaccard_identical():
    sig = frozenset([(0.1, "Arial", 10.0), (0.5, "Arial", 12.0)])
    assert jaccard(sig, sig) == 1.0


@pytest.mark.unit
def test_jaccard_disjoint():
    a = frozenset([(0.1, "Arial", 10.0)])
    b = frozenset([(0.9, "Times", 12.0)])
    assert jaccard(a, b) == 0.0


@pytest.mark.unit
def test_jaccard_partial():
    a = frozenset([(0.1, "Arial", 10.0), (0.5, "Arial", 12.0)])
    b = frozenset([(0.1, "Arial", 10.0), (0.9, "Times", 8.0)])
    result = jaccard(a, b)
    assert 0.0 < result < 1.0


# ---------------------------------------------------------------------------
# Unit: edit_distance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_edit_distance_identical():
    seq = [(0.1, 0.1, 0.8), (0.1, 0.5, 0.6)]
    assert edit_distance(seq, seq) == 0.0


@pytest.mark.unit
def test_edit_distance_totally_different():
    a = [(0.1, 0.1, 0.8)]
    b = [(0.9, 0.9, 0.1)]
    # Single element lists, totally different → distance close to 1
    result = edit_distance(a, b)
    assert result > 0.5


@pytest.mark.unit
def test_edit_distance_empty():
    assert edit_distance([], []) == 0.0
    assert edit_distance([], [(0.1, 0.1, 0.5)]) == 1.0


# ---------------------------------------------------------------------------
# Unit: ensemble_match_count — SAME pair
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ensemble_same_pair_all_signals_agree():
    """SAME pair: same phash, same font, same struct → 3/3."""
    phash_a = _make_phash_mock(0)
    phash_b = _make_phash_mock(5)  # distance=5 <= T_PHASH=16 ✓

    font = frozenset([(0.1, "Arial", 10.0), (0.5, "Arial", 12.0)])

    seq = [(0.1, 0.1, 0.8), (0.1, 0.3, 0.7)]

    count = ensemble_match_count(phash_a, phash_b, font, font, seq, seq)
    assert count == 3


@pytest.mark.unit
def test_ensemble_same_pair_similarity_high():
    phash_a = _make_phash_mock(0)
    phash_b = _make_phash_mock(5)
    font = frozenset([(0.1, "Arial", 10.0)])
    seq = [(0.1, 0.1, 0.8)]

    count = ensemble_match_count(phash_a, phash_b, font, font, seq, seq)
    sim = ensemble_to_similarity(count)
    assert sim >= 0.82, f"SAME pair similarity {sim} should be >= 0.82"


# ---------------------------------------------------------------------------
# Unit: ensemble_match_count — DIFF pair
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ensemble_diff_pair_no_signals_agree():
    """DIFF pair: very different phash, disjoint fonts, different struct → 0/3."""
    phash_a = _make_phash_mock(0)
    phash_b = _make_phash_mock(30)  # distance=30 > T_PHASH=16 ✗

    font_a = frozenset([(0.1, "Arial", 10.0)])
    font_b = frozenset([(0.9, "Times", 8.0)])  # jaccard=0 < T_FONT=0.47 ✗

    seq_a = [(0.1, 0.1, 0.8), (0.1, 0.3, 0.7), (0.1, 0.5, 0.6)]
    seq_b = [(0.9, 0.9, 0.1)]  # totally different ✗

    count = ensemble_match_count(phash_a, phash_b, font_a, font_b, seq_a, seq_b)
    assert count == 0


@pytest.mark.unit
def test_ensemble_diff_pair_similarity_low():
    phash_a = _make_phash_mock(0)
    phash_b = _make_phash_mock(30)
    font_a = frozenset([(0.1, "Arial", 10.0)])
    font_b = frozenset([(0.9, "Times", 8.0)])
    seq_a = [(0.1, 0.1, 0.8)]
    seq_b = [(0.9, 0.9, 0.1)]

    count = ensemble_match_count(phash_a, phash_b, font_a, font_b, seq_a, seq_b)
    sim = ensemble_to_similarity(count)
    assert sim < 0.82, f"DIFF pair similarity {sim} should be < 0.82"


# ---------------------------------------------------------------------------
# Unit: fallback when signals absent
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ensemble_no_signals_returns_minus_one():
    count = ensemble_match_count(None, None, None, None, [], [])
    assert count == -1


@pytest.mark.unit
def test_ensemble_to_similarity_fallback():
    """ensemble_to_similarity(-1) returns -1.0 → caller uses geometry fallback."""
    sim = ensemble_to_similarity(-1)
    assert sim == -1.0


# ---------------------------------------------------------------------------
# Unit: _ensemble_similarity fallback via PageInfo
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ensemble_similarity_fallback_no_signals():
    """PageInfo with no signals → _ensemble_similarity returns -1.0."""
    from services.stages.stage1_clustering.clustering_algorithms import _ensemble_similarity

    pi_a = PageInfo(pdf_id="a", page_index=0)
    pi_b = PageInfo(pdf_id="b", page_index=0)
    # phash=None, font_sig=None, struct_seq=[] by default
    result = _ensemble_similarity(pi_a, pi_b)
    assert result == -1.0


# ---------------------------------------------------------------------------
# Unit: PageInfo fields exist (regression — Story 48.10)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_page_info_has_ensemble_fields():
    pi = PageInfo(pdf_id="x", page_index=0)
    assert hasattr(pi, "phash")
    assert hasattr(pi, "font_sig")
    assert hasattr(pi, "struct_seq")
    assert pi.phash is None
    assert pi.font_sig is None
    assert pi.struct_seq == []


# ---------------------------------------------------------------------------
# Unit: ensemble constants sanity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ensemble_scores_monotonic():
    """Scores must be monotonically increasing with match count."""
    assert ENSEMBLE_SCORES[0] < ENSEMBLE_SCORES[1] < ENSEMBLE_SCORES[2] < ENSEMBLE_SCORES[3]


@pytest.mark.unit
def test_thresholds_in_valid_range():
    assert 0 <= T_PHASH <= 64
    assert 0.0 <= T_FONT <= 1.0
    assert 0.0 <= T_STRUCT <= 1.0
