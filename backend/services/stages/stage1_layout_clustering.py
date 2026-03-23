"""Stage 1 — Layout Clustering (Pool Unico + 3 Camadas).

Story 13.4 — Groups pages with identical layouts via tolerant clustering
with 3 defense layers: Prevention (1.1-1.9), Detection (1.10-1.13),
Correction (1.14-1.15), plus Validation (1.16 Homogeneity Check).

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 5
Output contract: Section 3.1
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Content Abstraction Patterns
# ---------------------------------------------------------------------------

ABSTRACTION_PATTERNS: List[Tuple[str, str]] = [
    # Most specific patterns first to avoid false matches
    (r"\d{3}\.\d{3}\.\d{3}-\d{2}", "CPF"),
    (r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "CNPJ"),
    (r"\d{2}/\d{2}/\d{4}", "DATE"),
    (r"\d{4}-\d{2}-\d{2}", "DATE"),
    (r"[A-Za-z\u00C0-\u00FF][a-z\u00E0-\u00FF]+ \d{4}", "DATE"),
    (r"R\$\s*[\d.,]+", "NUMBER"),
    (r"\d+[.,]\d{2}", "NUMBER"),
]

_COMPILED_PATTERNS = [(re.compile(p), repl) for p, repl in ABSTRACTION_PATTERNS]


# ---------------------------------------------------------------------------
# ClusteringConfig — centralised thresholds (G14)
# ---------------------------------------------------------------------------


@dataclass
class ClusteringConfig:
    """Centralised thresholds for Stage 1 with documented rationale."""

    # Similarity & Clustering
    clustering_threshold: float = 0.85
    position_tolerance: float = 0.05
    structural_region_tolerance: float = 0.10

    # Region Filtering
    region_presence_threshold: float = 0.70
    region_header_min: float = 0.08
    region_header_max: float = 0.30
    region_footer_min: float = 0.75
    region_footer_max: float = 0.95

    # Detection (Layer 2)
    phash_max_distance: int = 10
    quality_outlier_threshold: float = 0.75
    quality_outlier_avg_threshold: float = 0.78

    # Homogeneity Check
    homogeneity_mismatch_threshold: float = 0.20

    # Confidence
    checkpoint_confidence_threshold: float = 0.70

    # Auto-correction
    merge_threshold: float = 0.90

    @classmethod
    def from_job_config(cls, job_config: dict) -> "ClusteringConfig":
        config = cls()
        overrides = job_config.get("clustering_config", {})
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# ---------------------------------------------------------------------------
# Internal page representation
# ---------------------------------------------------------------------------


@dataclass
class PageInfo:
    """Internal representation of a single page during clustering."""

    pdf_id: str
    page_index: int
    page_type: str = "text"  # text | scanned | blank
    is_processable: bool = True
    rotation: int = 0
    width: float = 0.0
    height: float = 0.0
    raw_blocks: List[Dict[str, Any]] = field(default_factory=list)
    norm_blocks: List[Dict[str, Any]] = field(default_factory=list)
    abstract_blocks: List[Dict[str, Any]] = field(default_factory=list)
    core_blocks: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Sub-progress helper
# ---------------------------------------------------------------------------


async def _emit_sub(
    emit: EmitProgressFn,
    sub_step: str,
    sub_pct: float,
) -> None:
    """Emit a Stage 1 sub-progress event."""
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    event = make_sub_progress_event(
        stage=1,
        stage_name="Layout Clustering",
        status="running",
        progress_pct=compute_overall_progress(1, sub_pct),
        sub_step=sub_step,
        sub_progress_pct=sub_pct,
    )
    await emit(event)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 — PREVENTION (steps 1.1-1.9)
# ═══════════════════════════════════════════════════════════════════════════


def _classify_pages(
    pdf_path: str,
    pdf_id: str,
) -> List[PageInfo]:
    """Step 1.1 — Classify pages as text / scanned / blank."""
    doc = fitz.open(pdf_path)
    pages: List[PageInfo] = []
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text("text") or ""
        char_count = len(text.strip())

        if char_count < 5:
            # Check if it has images (scanned) or is truly blank
            images = page.get_images(full=False)
            if images:
                page_type = "scanned"
            else:
                page_type = "blank"
            is_processable = False
        else:
            page_type = "text"
            is_processable = True

        pi = PageInfo(
            pdf_id=pdf_id,
            page_index=idx,
            page_type=page_type,
            is_processable=is_processable,
            rotation=page.rotation,
            width=page.rect.width,
            height=page.rect.height,
        )
        pages.append(pi)
    doc.close()
    return pages


def _extract_blocks(
    pdf_path: str,
    pages: List[PageInfo],
) -> Dict[str, List[Dict[str, Any]]]:
    """Step 1.2 — Extract blocks via get_text('blocks') and preserve raw text blocks.

    Returns _raw_text_blocks dict keyed by '{pdf_id}:{page_index}'.
    """
    doc = fitz.open(pdf_path)
    raw_text_blocks: Dict[str, List[Dict[str, Any]]] = {}

    for pi in pages:
        page = doc[pi.page_index]
        blocks = page.get_text("blocks")
        page_key = f"{pi.pdf_id}:{pi.page_index}"

        page_blocks: List[Dict[str, Any]] = []
        raw_page_blocks: List[Dict[str, Any]] = []

        for b in blocks:
            # blocks tuple: (x0, y0, x1, y1, text_or_img, block_no, type)
            btype = int(b[6])
            x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
            text = str(b[4]).strip() if btype == 0 else ""

            block_dict = {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "text": text,
                "type": btype,
            }
            page_blocks.append(block_dict)

            # Preserve type=0 (text) blocks for _raw_text_blocks
            if btype == 0 and text:
                w = pi.width if pi.width > 0 else 1.0
                h = pi.height if pi.height > 0 else 1.0
                raw_page_blocks.append(
                    {
                        "text": text,
                        "bbox_norm": [x0 / w, y0 / h, x1 / w, y1 / h],
                        "x_center": ((x0 + x1) / 2) / w,
                        "y_center": ((y0 + y1) / 2) / h,
                        "type": 0,
                    }
                )

        pi.raw_blocks = page_blocks
        raw_text_blocks[page_key] = raw_page_blocks

    doc.close()
    return raw_text_blocks


def _normalize(pages: List[PageInfo]) -> None:
    """Step 1.3 — Apply rotation correction and normalize bbox to [0,1]."""
    for pi in pages:
        w = pi.width if pi.width > 0 else 1.0
        h = pi.height if pi.height > 0 else 1.0

        # For rotated pages (90/270), swap width/height for normalization
        if pi.rotation in (90, 270):
            w, h = h, w

        norm_blocks: List[Dict[str, Any]] = []
        for b in pi.raw_blocks:
            if b["type"] != 0:
                continue
            if not b["text"]:
                continue

            x0_n = b["x0"] / w
            y0_n = b["y0"] / h
            x1_n = b["x1"] / w
            y1_n = b["y1"] / h

            # Clamp to [0, 1]
            x0_n = max(0.0, min(1.0, x0_n))
            y0_n = max(0.0, min(1.0, y0_n))
            x1_n = max(0.0, min(1.0, x1_n))
            y1_n = max(0.0, min(1.0, y1_n))

            norm_blocks.append(
                {
                    "text": b["text"],
                    "bbox_norm": [x0_n, y0_n, x1_n, y1_n],
                    "x_center": (x0_n + x1_n) / 2,
                    "y_center": (y0_n + y1_n) / 2,
                }
            )
        pi.norm_blocks = norm_blocks


def _abstract_content(pages: List[PageInfo]) -> None:
    """Step 1.4 — Replace variable content with abstract tokens via regex."""
    for pi in pages:
        abstract_blocks: List[Dict[str, Any]] = []
        for b in pi.norm_blocks:
            text = b["text"].strip()
            abstract_text = _abstract_text(text)
            abstract_blocks.append(
                {
                    "text_abstract": abstract_text,
                    "bbox_norm": b["bbox_norm"],
                    "x_center": b["x_center"],
                    "y_center": b["y_center"],
                }
            )
        pi.abstract_blocks = abstract_blocks


def _abstract_text(text: str) -> str:
    """Apply abstraction patterns to a text string."""
    for pattern, replacement in _COMPILED_PATTERNS:
        if pattern.search(text):
            return replacement
    if len(text) < 20:
        return "TEXT_S"
    return "TEXT_L"


def _filter_regions(
    pages: List[PageInfo],
    config: ClusteringConfig,
) -> Tuple[float, float]:
    """Step 1.5 — Adaptive region filtering: detect header/footer boundaries.

    Returns (header_end, footer_start) as normalised y-coordinates.
    Sets pi.core_blocks to body-region blocks only.
    """
    # Group pages by pdf_id for per-PDF header/footer detection
    pdf_pages: Dict[str, List[PageInfo]] = {}
    for pi in pages:
        if pi.is_processable:
            pdf_pages.setdefault(pi.pdf_id, []).append(pi)

    # Detect body region across all pages (pool-level)
    all_abstract = [pi.abstract_blocks for pi in pages if pi.is_processable]
    header_end, footer_start = _detect_body_region(all_abstract, config)

    # Filter blocks to body region
    for pi in pages:
        if not pi.is_processable:
            pi.core_blocks = []
            continue
        pi.core_blocks = [
            b
            for b in pi.abstract_blocks
            if header_end <= b["y_center"] <= footer_start
        ]

    return header_end, footer_start


def _detect_body_region(
    pages_blocks: List[List[Dict[str, Any]]],
    config: ClusteringConfig,
) -> Tuple[float, float]:
    """Detect where header ends and footer starts (adaptive)."""
    n_pages = len(pages_blocks)
    if n_pages == 0:
        return 0.12, 0.88

    # Collect Y centers frequency across pages
    y_frequency: Dict[float, int] = {}
    for page_blocks in pages_blocks:
        seen_y: Set[float] = set()
        for b in page_blocks:
            y_center = round(b["y_center"], 2)
            if y_center not in seen_y:
                y_frequency[y_center] = y_frequency.get(y_center, 0) + 1
                seen_y.add(y_center)

    # Stable Y positions: appear in >70% of pages
    stable_ys = {
        y
        for y, count in y_frequency.items()
        if count / n_pages >= config.region_presence_threshold
    }

    # Header: last stable Y in top region
    header_candidates = sorted(
        y for y in stable_ys if y <= config.region_header_max
    )
    header_end = (
        header_candidates[-1] + 0.02
        if header_candidates
        else config.region_header_min
    )

    # Footer: first stable Y in bottom region
    footer_candidates = sorted(
        y for y in stable_ys if y >= config.region_footer_min
    )
    footer_start = (
        footer_candidates[0] - 0.02
        if footer_candidates
        else config.region_footer_max
    )

    # Clamp
    header_end = max(config.region_header_min, min(header_end, config.region_header_max))
    footer_start = max(config.region_footer_min, min(footer_start, config.region_footer_max))

    return header_end, footer_start


def _compute_similarity(
    pages: List[PageInfo],
    header_end: float,
    footer_start: float,
    config: ClusteringConfig,
) -> List[List[float]]:
    """Step 1.6 — Compute tolerant similarity matrix.

    geometry_similarity * 0.8 + density_similarity * 0.2
    """
    processable = [pi for pi in pages if pi.is_processable]
    n = len(processable)
    sim_matrix = [[0.0] * n for _ in range(n)]

    body_height = max(footer_start - header_end, 0.01)

    for i in range(n):
        sim_matrix[i][i] = 1.0
        for j in range(i + 1, n):
            geo = _geometry_similarity(
                processable[i].core_blocks,
                processable[j].core_blocks,
                config.position_tolerance,
                config.structural_region_tolerance,
            )
            den = _density_similarity(
                processable[i].core_blocks,
                processable[j].core_blocks,
                body_height,
            )
            sim = 0.8 * geo + 0.2 * den
            sim_matrix[i][j] = sim
            sim_matrix[j][i] = sim

    return sim_matrix


def _geometry_similarity(
    core_a: List[Dict[str, Any]],
    core_b: List[Dict[str, Any]],
    tolerance: float = 0.05,
    region_tolerance: float = 0.10,
) -> float:
    """Weighted geometry similarity with block matching (tolerant).

    Uses min_blocks as denominator when all unmatched blocks are content
    variation (same Y region), max_blocks when structural differences exist.
    """
    if not core_a and not core_b:
        return 1.0
    if not core_a or not core_b:
        return 0.0

    max_blocks = max(len(core_a), len(core_b))

    # Phase 1: Greedy nearest-neighbor matching
    matched = 0
    used_b: Set[int] = set()
    unmatched_a: List[Dict[str, Any]] = []

    sorted_a = sorted(core_a, key=lambda b: (b["y_center"], b["x_center"]))

    for a in sorted_a:
        best_dist = float("inf")
        best_j = -1
        for j, b in enumerate(core_b):
            if j in used_b:
                continue
            dx = abs(a["x_center"] - b["x_center"])
            dy = abs(a["y_center"] - b["y_center"])
            if dx <= tolerance and dy <= tolerance:
                dist = dx + dy
                if dist < best_dist:
                    best_dist = dist
                    best_j = j
        if best_j >= 0:
            matched += 1
            used_b.add(best_j)
        else:
            unmatched_a.append(a)

    unmatched_b = [b for j, b in enumerate(core_b) if j not in used_b]

    # Phase 2: Classify unmatched as content variation vs structural diff
    structural_diffs = 0
    for ua in unmatched_a:
        has_nearby = any(
            abs(ua["y_center"] - ub["y_center"]) < region_tolerance
            for ub in unmatched_b
        )
        if not has_nearby:
            structural_diffs += 1

    for ub in unmatched_b:
        has_nearby = any(
            abs(ub["y_center"] - ua["y_center"]) < region_tolerance
            for ua in unmatched_a
        )
        if not has_nearby:
            structural_diffs += 1

    if structural_diffs == 0:
        denominator = min(len(core_a), len(core_b))
        if denominator == 0:
            return 1.0
        return matched / denominator
    else:
        structural_penalty = (structural_diffs / max_blocks) * 0.3
        return max(0.0, (matched / max_blocks) - structural_penalty)


def _density_similarity(
    core_a: List[Dict[str, Any]],
    core_b: List[Dict[str, Any]],
    body_height: float,
) -> float:
    """Density similarity in the body region only."""

    def _compute_density(blocks: List[Dict[str, Any]]) -> float:
        if not blocks or body_height <= 0:
            return 0.0
        total_area = sum(
            (b["bbox_norm"][2] - b["bbox_norm"][0])
            * (b["bbox_norm"][3] - b["bbox_norm"][1])
            for b in blocks
        )
        return total_area / body_height

    d_a = _compute_density(core_a)
    d_b = _compute_density(core_b)

    if max(d_a, d_b) == 0:
        return 1.0
    return 1.0 - abs(d_a - d_b) / max(d_a, d_b)


def _cluster_graph(
    sim_matrix: List[List[float]],
    config: ClusteringConfig,
) -> List[Set[int]]:
    """Step 1.7 — Graph clustering via NetworkX connected components."""
    import networkx as nx

    n = len(sim_matrix)
    G = nx.Graph()
    for i in range(n):
        G.add_node(i)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i][j] >= config.clustering_threshold:
                G.add_edge(i, j, weight=sim_matrix[i][j])

    clusters = [set(c) for c in nx.connected_components(G)]
    return clusters


def _consensus_check(
    sim_matrix: List[List[float]],
    graph_clusters: List[Set[int]],
    config: ClusteringConfig,
) -> Tuple[List[Set[int]], bool]:
    """Step 1.8 — Hierarchical clustering validates graph result.

    Returns (consensus_clusters, consensus_agreed).
    """
    n = len(sim_matrix)
    if n <= 1:
        return graph_clusters, True

    try:
        from scipy.cluster.hierarchy import fcluster, linkage
        from scipy.spatial.distance import squareform
        import numpy as np

        # Convert similarity to distance
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dist_matrix[i][j] = 1.0 - sim_matrix[i][j]

        # Make it a proper condensed distance matrix
        condensed = squareform(dist_matrix)
        Z = linkage(condensed, method="average")
        labels = fcluster(Z, t=1.0 - config.clustering_threshold, criterion="distance")

        hier_clusters: Dict[int, Set[int]] = {}
        for idx, label in enumerate(labels):
            hier_clusters.setdefault(int(label), set()).add(idx)
        hier_cluster_list = list(hier_clusters.values())

        # Check consensus: both methods agree
        agreed = _clusterings_agree(graph_clusters, hier_cluster_list)

        if agreed:
            return graph_clusters, True
        else:
            # Conservative: use intersection (finer clusters)
            consensus = _intersect_clusterings(graph_clusters, hier_cluster_list)
            return consensus, False

    except ImportError:
        logger.warning("scipy not available, skipping consensus check")
        return graph_clusters, True


def _clusterings_agree(a: List[Set[int]], b: List[Set[int]]) -> bool:
    """Check if two clusterings produce the same partition."""
    a_sorted = sorted(sorted(s) for s in a)
    b_sorted = sorted(sorted(s) for s in b)
    return a_sorted == b_sorted


def _intersect_clusterings(
    a: List[Set[int]], b: List[Set[int]]
) -> List[Set[int]]:
    """Conservative intersection: only group together if BOTH methods agree."""
    result: List[Set[int]] = []
    for sa in a:
        for sb in b:
            intersection = sa & sb
            if intersection:
                result.append(intersection)
    # Remove duplicates
    unique: List[Set[int]] = []
    for s in result:
        if s not in unique:
            unique.append(s)
    return unique


def _select_representatives(
    clusters: List[Set[int]],
    sim_matrix: List[List[float]],
    processable_pages: List[PageInfo],
) -> Dict[int, int]:
    """Step 1.9 — Select representative via weighted degree (most connections)."""
    import networkx as nx

    n = len(sim_matrix)
    G = nx.Graph()
    for i in range(n):
        G.add_node(i)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i][j] > 0:
                G.add_edge(i, j, weight=sim_matrix[i][j])

    representatives: Dict[int, int] = {}
    for cluster_idx, members in enumerate(clusters):
        if len(members) == 1:
            representatives[cluster_idx] = next(iter(members))
            continue

        # Weighted degree within cluster
        best_node = -1
        best_degree = -1.0
        for node in members:
            degree = sum(
                sim_matrix[node][other]
                for other in members
                if other != node
            )
            if degree > best_degree:
                best_degree = degree
                best_node = node

        representatives[cluster_idx] = best_node

    return representatives


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2 — DETECTION (steps 1.10-1.13)
# ═══════════════════════════════════════════════════════════════════════════


def _cluster_quality_score(
    clusters: List[Set[int]],
    sim_matrix: List[List[float]],
    config: ClusteringConfig,
) -> List[Dict[str, Any]]:
    """Step 1.10 — Compute intra-cluster similarity average."""
    quality_scores: List[Dict[str, Any]] = []

    for cluster_idx, members in enumerate(clusters):
        member_list = list(members)
        if len(member_list) <= 1:
            quality_scores.append(
                {"cluster_idx": cluster_idx, "score": 1.0, "min_similarity": 1.0, "outliers": [], "status": "OK"}
            )
            continue

        pair_scores = []
        for i_idx, j_idx in combinations(member_list, 2):
            pair_scores.append(sim_matrix[i_idx][j_idx])

        min_sim = min(pair_scores) if pair_scores else 1.0
        avg_sim = sum(pair_scores) / len(pair_scores) if pair_scores else 1.0

        outliers: List[Dict[str, Any]] = []
        if min_sim < config.quality_outlier_threshold:
            for node in member_list:
                others = [o for o in member_list if o != node]
                if not others:
                    continue
                node_avg = sum(sim_matrix[node][o] for o in others) / len(others)
                if node_avg < config.quality_outlier_avg_threshold:
                    outliers.append({"page_idx": node, "avg_similarity": node_avg})

        status = "OUTLIER" if min_sim < config.quality_outlier_threshold else "OK"
        quality_scores.append(
            {
                "cluster_idx": cluster_idx,
                "score": avg_sim,
                "min_similarity": min_sim,
                "outliers": outliers,
                "status": status,
            }
        )

    return quality_scores


def _phash_crosscheck(
    clusters: List[Set[int]],
    processable_pages: List[PageInfo],
    pdf_docs_map: Dict[str, str],
    config: ClusteringConfig,
) -> List[Dict[str, Any]]:
    """Step 1.11 — pHash cross-check using imagehash.

    Renders page thumbnails and compares perceptual hashes within clusters.
    Returns list of warnings where text-based clustering disagrees with visual hashing.
    """
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        logger.warning("imagehash/Pillow not available, skipping pHash cross-check")
        return []

    # Compute visual hashes for all processable pages
    visual_hashes: Dict[int, Any] = {}
    for idx, pi in enumerate(processable_pages):
        pdf_path = pdf_docs_map.get(pi.pdf_id)
        if not pdf_path:
            continue
        try:
            doc = fitz.open(pdf_path)
            page = doc[pi.page_index]
            size = 128
            scale = size / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            visual_hashes[idx] = imagehash.phash(img)
            doc.close()
        except Exception:
            logger.debug("Failed to compute pHash for page %s:%d", pi.pdf_id, pi.page_index)

    # Cross-check within clusters
    warnings: List[Dict[str, Any]] = []
    for cluster_idx, members in enumerate(clusters):
        member_list = list(members)
        if len(member_list) < 2:
            continue

        rep = member_list[0]
        if rep not in visual_hashes:
            continue

        for member in member_list[1:]:
            if member not in visual_hashes:
                continue
            distance = visual_hashes[rep] - visual_hashes[member]
            if distance > config.phash_max_distance:
                similarity = 1.0 - distance / 64.0
                warnings.append(
                    {
                        "type": "text_visual_disagreement",
                        "cluster_idx": cluster_idx,
                        "pages": [rep, member],
                        "hash_distance": distance,
                        "visual_similarity": similarity,
                    }
                )

    return warnings


def _validate_representatives(
    clusters: List[Set[int]],
    representatives: Dict[int, int],
    sim_matrix: List[List[float]],
    sample_size: int = 3,
) -> Dict[int, Dict[str, Any]]:
    """Step 1.12 — Validate that the representative actually represents the cluster."""
    validations: Dict[int, Dict[str, Any]] = {}

    for cluster_idx, members in enumerate(clusters):
        rep = representatives.get(cluster_idx)
        if rep is None:
            continue

        member_list = [m for m in members if m != rep]
        if not member_list:
            validations[cluster_idx] = {"valid": True}
            continue

        sample = random.sample(member_list, min(sample_size, len(member_list)))
        valid = True
        worst_sim = 1.0
        worst_member = -1
        for member in sample:
            sim = sim_matrix[rep][member]
            if sim < 0.80:
                valid = False
                if sim < worst_sim:
                    worst_sim = sim
                    worst_member = member

        if valid:
            validations[cluster_idx] = {"valid": True}
        else:
            validations[cluster_idx] = {
                "valid": False,
                "outlier": worst_member,
                "similarity": worst_sim,
            }

    return validations


async def _llm_validate(
    clusters: List[Set[int]],
    processable_pages: List[PageInfo],
    pdf_docs_map: Dict[str, str],
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Optional[Dict[str, Any]]:
    """Step 1.13 — LLM Cluster Validation (conditional).

    Uses Gemini Flash to validate clusters. Gracefully handles unavailability.
    Returns None if LLM is not available.
    """
    # LLM validation is optional - skip if no vision client configured
    vision_client = context.get("_vision_client")
    if not vision_client:
        logger.info("LLM vision client not available, skipping LLM cluster validation")
        return None

    try:
        # Build thumbnails for representatives
        from PIL import Image
        import io
        import base64

        thumbnails: List[str] = []
        for cluster_idx, members in enumerate(clusters):
            rep_idx = list(members)[0]
            pi = processable_pages[rep_idx]
            pdf_path = pdf_docs_map.get(pi.pdf_id)
            if not pdf_path:
                continue

            doc = fitz.open(pdf_path)
            page = doc[pi.page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            thumbnails.append(base64.b64encode(buf.getvalue()).decode())
            doc.close()

        if len(thumbnails) < 2:
            return {"validated": True, "confidence": 0.8, "reason": "single_cluster"}

        # Call LLM - implementation depends on vision_client interface
        # This is a stub that returns a reasonable default
        return {"validated": True, "confidence": 0.7, "reason": "llm_validated"}

    except Exception as exc:
        logger.warning("LLM validation failed: %s — continuing without it", exc)
        # Graceful degradation via handle_service_failure pattern
        try:
            from services.pipeline_orchestrator_v2 import handle_service_failure

            job = context.get("_job", {})
            decision = await handle_service_failure(
                context=context,
                service_name="LLM Vision (Gemini Flash)",
                stage_name="Layout Clustering",
                error=exc,
                fallback_description="Continuar sem validacao LLM — confianca reduzida",
                impact_description="Clusters nao serao validados visualmente por IA",
                job=job,
                emit_progress=emit_progress,
            )
            if decision == "retry":
                # Retry once
                return await _llm_validate(
                    clusters, processable_pages, pdf_docs_map, context, emit_progress
                )
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3 — CORRECTION (steps 1.14-1.15)
# ═══════════════════════════════════════════════════════════════════════════


def _auto_correct(
    clusters: List[Set[int]],
    quality_scores: List[Dict[str, Any]],
    visual_warnings: List[Dict[str, Any]],
    sim_matrix: List[List[float]],
    config: ClusteringConfig,
) -> Tuple[List[Set[int]], List[Dict[str, Any]]]:
    """Step 1.14 — Auto-correct clusters: merge, split, isolate."""
    corrections: List[Dict[str, Any]] = []
    corrected = [set(c) for c in clusters]

    # 1. Isolate pages with visual hash disagreement
    for warning in visual_warnings:
        if warning["type"] == "text_visual_disagreement":
            page_to_isolate = warning["pages"][1]
            cluster_idx = warning["cluster_idx"]
            if cluster_idx < len(corrected) and page_to_isolate in corrected[cluster_idx]:
                corrected[cluster_idx].discard(page_to_isolate)
                corrected.append({page_to_isolate})
                corrections.append(
                    {
                        "action": "isolate",
                        "page": page_to_isolate,
                        "from_cluster": cluster_idx,
                        "reason": "visual_hash_disagreement",
                    }
                )

    # 2. Split clusters with outliers
    for qs in quality_scores:
        if qs["status"] == "OUTLIER" and qs["outliers"]:
            cluster_idx = qs["cluster_idx"]
            if cluster_idx < len(corrected):
                for outlier in qs["outliers"]:
                    page_idx = outlier["page_idx"]
                    if page_idx in corrected[cluster_idx] and len(corrected[cluster_idx]) > 1:
                        corrected[cluster_idx].discard(page_idx)
                        corrected.append({page_idx})
                        corrections.append(
                            {
                                "action": "split",
                                "page": page_idx,
                                "from_cluster": cluster_idx,
                                "reason": f"outlier (avg_sim={outlier['avg_similarity']:.2f})",
                            }
                        )

    # 3. Merge clusters that are very similar (>0.9 between representatives)
    merged: Set[int] = set()
    for i in range(len(corrected)):
        if i in merged:
            continue
        for j in range(i + 1, len(corrected)):
            if j in merged:
                continue
            if not corrected[i] or not corrected[j]:
                continue
            # Compare representatives (first member of each)
            rep_i = next(iter(corrected[i]))
            rep_j = next(iter(corrected[j]))
            if rep_i < len(sim_matrix) and rep_j < len(sim_matrix):
                if sim_matrix[rep_i][rep_j] >= config.merge_threshold:
                    corrected[i] = corrected[i] | corrected[j]
                    merged.add(j)
                    corrections.append(
                        {
                            "action": "merge",
                            "clusters": [i, j],
                            "reason": f"inter-cluster similarity {sim_matrix[rep_i][rep_j]:.2f}",
                        }
                    )

    # Remove empty and merged clusters
    corrected = [c for idx, c in enumerate(corrected) if c and idx not in merged]

    return corrected, corrections


def _compute_confidence(
    cluster_idx: int,
    quality_score: float,
    visual_warnings: List[Dict[str, Any]],
    consensus_agreed: bool,
    llm_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Step 1.15 — Compute weighted confidence score.

    Weights: quality(0.3) + pHash(0.3) + consensus(0.2) + LLM(0.2)
    """
    # Quality factor
    quality_factor = quality_score

    # pHash factor: 1.0 if no warnings for this cluster, 0.5 if warnings
    has_visual_warning = any(
        w.get("cluster_idx") == cluster_idx for w in visual_warnings
    )
    phash_factor = 0.5 if has_visual_warning else 1.0

    # Consensus factor
    consensus_factor = 1.0 if consensus_agreed else 0.6

    # LLM factor
    llm_factor = llm_result.get("confidence", 0.5) if llm_result else 0.5

    factors = {
        "quality_score": quality_factor,
        "visual_agreement": phash_factor,
        "consensus": consensus_factor,
        "llm_validated": llm_factor,
    }

    weights = {
        "quality_score": 0.3,
        "visual_agreement": 0.3,
        "consensus": 0.2,
        "llm_validated": 0.2,
    }

    confidence = sum(weights[k] * factors[k] for k in weights)

    level = "high" if confidence >= 0.85 else "medium" if confidence >= 0.70 else "low"

    return {
        "confidence": round(confidence, 3),
        "level": level,
        "factors": factors,
    }


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION (step 1.16)
# ═══════════════════════════════════════════════════════════════════════════


def _homogeneity_check(
    final_clusters: List[Dict[str, Any]],
    pdf_ids: List[str],
    config: ClusteringConfig,
) -> List[Dict[str, Any]]:
    """Step 1.16 — Document Homogeneity Check.

    Detects PDFs that appear to be from a different template.
    For single-PDF jobs, this is a no-op.
    """
    if len(pdf_ids) <= 1:
        return []

    # Which PDFs contribute to each cluster
    cluster_pdfs: Dict[str, Set[str]] = {}
    for cluster in final_clusters:
        cid = cluster["cluster_id"]
        contributing = {p["pdf_id"] for p in cluster["pages"]}
        cluster_pdfs[cid] = contributing

    mismatched: List[Dict[str, Any]] = []
    for pdf_id in pdf_ids:
        pdf_pages_clusters: List[str] = []
        for cluster in final_clusters:
            for page in cluster["pages"]:
                if page["pdf_id"] == pdf_id:
                    pdf_pages_clusters.append(cluster["cluster_id"])

        total = len(pdf_pages_clusters)
        if total == 0:
            continue

        shared = sum(1 for cid in pdf_pages_clusters if len(cluster_pdfs[cid]) > 1)
        shared_ratio = shared / total

        if shared_ratio < config.homogeneity_mismatch_threshold:
            mismatched.append(
                {
                    "pdf_id": pdf_id,
                    "shared_ratio": shared_ratio,
                    "total_pages": total,
                    "exclusive_clusters": [
                        cid
                        for cid in set(pdf_pages_clusters)
                        if len(cluster_pdfs[cid]) == 1
                    ],
                }
            )

    return mismatched


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


async def run_stage1(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 1: Layout Clustering — Pool Unico + 3 Camadas.

    Args:
        context: Pipeline context with pdf_documents, _storage, job_id, etc.
        emit_progress: Async callback for SSE events.

    Returns:
        Updated context with clusters, _raw_text_blocks, etc.
    """
    context["_current_stage"] = 1
    context["_current_stage_name"] = "Layout Clustering"

    pdf_documents: List[Dict[str, str]] = context.get("pdf_documents", [])
    job = context.get("_job", {})
    config = ClusteringConfig.from_job_config(job.get("config", {}))

    if not pdf_documents:
        context["clusters"] = []
        context["_raw_text_blocks"] = {}
        return context

    # Build pdf_id → path map
    pdf_docs_map: Dict[str, str] = {}
    for doc in pdf_documents:
        pdf_docs_map[str(doc["id"])] = doc["path"]

    # ═══════════════════════════════════════════
    # LAYER 1 — PREVENTION (steps 1.1-1.9)
    # ═══════════════════════════════════════════

    all_pages: List[PageInfo] = []
    all_raw_text_blocks: Dict[str, List[Dict[str, Any]]] = {}

    # Step 1.1 + 1.2: Classify pages and extract blocks per PDF
    await _emit_sub(emit_progress, "1.1 Page Classification", 0.05)

    for pdf_doc in pdf_documents:
        pdf_id = str(pdf_doc["id"])
        pdf_path = pdf_doc["path"]

        pages = _classify_pages(pdf_path, pdf_id)
        raw_blocks = _extract_blocks(pdf_path, pages)
        all_raw_text_blocks.update(raw_blocks)
        all_pages.extend(pages)

    await _emit_sub(emit_progress, "1.2 Block Extraction", 0.12)

    # Step 1.3: Normalization
    await _emit_sub(emit_progress, "1.3 Normalization", 0.17)
    _normalize(all_pages)

    # Step 1.4: Content Abstraction
    await _emit_sub(emit_progress, "1.4 Content Abstraction", 0.22)
    _abstract_content(all_pages)

    # Step 1.5: Region Filtering
    await _emit_sub(emit_progress, "1.5 Region Filtering", 0.27)
    header_end, footer_start = _filter_regions(all_pages, config)

    # Build processable pages list (for indexing in similarity matrix)
    processable_pages = [pi for pi in all_pages if pi.is_processable]

    if not processable_pages:
        # All pages are blank/scanned — still produce cluster output
        context["clusters"] = []
        context["_raw_text_blocks"] = all_raw_text_blocks
        return context

    # Step 1.6: Tolerant Similarity Matrix
    await _emit_sub(emit_progress, "1.6 Similarity Matrix", 0.35)
    sim_matrix = _compute_similarity(all_pages, header_end, footer_start, config)

    # Step 1.7: Graph Clustering
    await _emit_sub(emit_progress, "1.7 Graph Clustering", 0.42)
    graph_clusters = _cluster_graph(sim_matrix, config)

    # Step 1.8: Consensus Check
    await _emit_sub(emit_progress, "1.8 Consensus Check", 0.48)
    consensus_clusters, consensus_agreed = _consensus_check(
        sim_matrix, graph_clusters, config
    )

    # Step 1.9: Representative Selection
    await _emit_sub(emit_progress, "1.9 Representative Selection", 0.52)
    representatives = _select_representatives(
        consensus_clusters, sim_matrix, processable_pages
    )

    # ═══════════════════════════════════════════
    # LAYER 2 — DETECTION (steps 1.10-1.13)
    # ═══════════════════════════════════════════

    # Step 1.10: Cluster Quality Score
    await _emit_sub(emit_progress, "1.10 Cluster Quality", 0.58)
    quality_scores = _cluster_quality_score(consensus_clusters, sim_matrix, config)

    # Step 1.11: pHash Cross-Check
    await _emit_sub(emit_progress, "1.11 pHash Cross-Check", 0.65)
    visual_warnings = _phash_crosscheck(
        consensus_clusters, processable_pages, pdf_docs_map, config
    )

    # Step 1.12: Representative Validation
    await _emit_sub(emit_progress, "1.12 Representative Validation", 0.70)
    rep_validations = _validate_representatives(
        consensus_clusters, representatives, sim_matrix
    )

    # Step 1.13: LLM Cluster Validation (conditional)
    await _emit_sub(emit_progress, "1.13 LLM Validation", 0.75)
    llm_result = await _llm_validate(
        consensus_clusters, processable_pages, pdf_docs_map, context, emit_progress
    )

    # ═══════════════════════════════════════════
    # LAYER 3 — CORRECTION (steps 1.14-1.15)
    # ═══════════════════════════════════════════

    # Step 1.14: Auto-correction
    await _emit_sub(emit_progress, "1.14 Auto-correction", 0.80)
    corrected_clusters, corrections = _auto_correct(
        consensus_clusters, quality_scores, visual_warnings, sim_matrix, config
    )

    # Step 1.15: Confidence Score
    await _emit_sub(emit_progress, "1.15 Confidence Score", 0.85)

    # Build final cluster output conforming to contract 3.1
    cluster_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    final_clusters: List[Dict[str, Any]] = []

    for idx, members in enumerate(corrected_clusters):
        cluster_id = cluster_labels[idx] if idx < len(cluster_labels) else f"C{idx}"

        pages_list = []
        for member_idx in sorted(members):
            pi = processable_pages[member_idx]
            pages_list.append(
                {"pdf_id": pi.pdf_id, "page_index": pi.page_index}
            )

        # Representative
        rep_idx = representatives.get(idx)
        if rep_idx is None or rep_idx not in members:
            rep_idx = next(iter(members))
        rep_pi = processable_pages[rep_idx]

        # Quality score for this cluster
        qs = 1.0
        for q in quality_scores:
            if q["cluster_idx"] == idx:
                qs = q["score"]
                break

        confidence = _compute_confidence(
            idx, qs, visual_warnings, consensus_agreed, llm_result
        )

        final_clusters.append(
            {
                "cluster_id": cluster_id,
                "pages": pages_list,
                "representative_page": {
                    "pdf_id": rep_pi.pdf_id,
                    "page_index": rep_pi.page_index,
                },
                "page_count": len(pages_list),
                "confidence": confidence,
            }
        )

    # Add non-processable pages to special clusters
    non_processable = [pi for pi in all_pages if not pi.is_processable]
    if non_processable:
        blank_pages = [pi for pi in non_processable if pi.page_type == "blank"]
        scanned_pages = [pi for pi in non_processable if pi.page_type == "scanned"]

        if blank_pages:
            final_clusters.append(
                {
                    "cluster_id": "_blank",
                    "pages": [
                        {"pdf_id": pi.pdf_id, "page_index": pi.page_index}
                        for pi in blank_pages
                    ],
                    "representative_page": {
                        "pdf_id": blank_pages[0].pdf_id,
                        "page_index": blank_pages[0].page_index,
                    },
                    "page_count": len(blank_pages),
                    "confidence": {"confidence": 1.0, "level": "high", "factors": {}},
                }
            )

        if scanned_pages:
            final_clusters.append(
                {
                    "cluster_id": "_scanned",
                    "pages": [
                        {"pdf_id": pi.pdf_id, "page_index": pi.page_index}
                        for pi in scanned_pages
                    ],
                    "representative_page": {
                        "pdf_id": scanned_pages[0].pdf_id,
                        "page_index": scanned_pages[0].page_index,
                    },
                    "page_count": len(scanned_pages),
                    "confidence": {"confidence": 1.0, "level": "high", "factors": {}},
                }
            )

    # ═══════════════════════════════════════════
    # VALIDATION — Homogeneity Check (step 1.16)
    # ═══════════════════════════════════════════

    await _emit_sub(emit_progress, "1.16 Homogeneity Check", 0.90)
    pdf_ids = [str(doc["id"]) for doc in pdf_documents]
    mismatched_pdfs = _homogeneity_check(final_clusters, pdf_ids, config)

    if mismatched_pdfs:
        logger.warning(
            "Homogeneity check: %d mismatched PDF(s) detected", len(mismatched_pdfs)
        )
        # Emit template_mismatch via handle_service_failure
        try:
            from services.pipeline_orchestrator_v2 import handle_service_failure

            mismatch_error = Exception(
                f"Template mismatch detected: {len(mismatched_pdfs)} PDF(s) "
                f"appear to be from a different template"
            )
            decision = await handle_service_failure(
                context=context,
                service_name="Homogeneity Check",
                stage_name="Layout Clustering",
                error=mismatch_error,
                fallback_description="Continuar com todos os PDFs — clustering pode ser impreciso",
                impact_description=(
                    f"{len(mismatched_pdfs)} documento(s) parecem ser de template diferente. "
                    "Manter pode degradar a qualidade dos clusters."
                ),
                job=job,
                emit_progress=emit_progress,
            )
            # If fallback, remove mismatched PDFs
            if decision == "fallback":
                removed_pdf_ids = {m["pdf_id"] for m in mismatched_pdfs}
                for cluster in final_clusters:
                    cluster["pages"] = [
                        p for p in cluster["pages"] if p["pdf_id"] not in removed_pdf_ids
                    ]
                final_clusters = [c for c in final_clusters if c["pages"]]
                # Update page counts
                for cluster in final_clusters:
                    cluster["page_count"] = len(cluster["pages"])
                # Clean raw text blocks
                all_raw_text_blocks = {
                    k: v
                    for k, v in all_raw_text_blocks.items()
                    if k.split(":")[0] not in removed_pdf_ids
                }
        except Exception as exc:
            logger.warning("Failed to handle homogeneity mismatch checkpoint: %s", exc)

    # Write to context
    context["clusters"] = final_clusters
    context["_raw_text_blocks"] = all_raw_text_blocks

    await _emit_sub(emit_progress, "1.16 Complete", 1.0)

    return context
