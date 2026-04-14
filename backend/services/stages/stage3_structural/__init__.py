"""Stage 3 — Structural Analysis sub-package.

Story 41.3 — stage3_structural_analysis.py decomposed into:
  - constants.py          : shared regex patterns
  - multi_example_analysis.py : Step 3.1 — statistical + NER classification
  - visual_analysis.py    : Step 3.2 — GPT-4o Vision region detection
  - classification.py     : Step 3.3 — semantic classification + label-value pairing
  - section_utils.py      : zone/section splitting + bbox/assignment helpers
  - semantic_utils.py     : semantic name extraction + XSD binding
  - tree_builder.py       : Step 3.4 — hierarchy tree construction

All symbols are re-exported here for backward compatibility.
"""

from __future__ import annotations

from services.stages.stage3_structural.classification import (  # noqa: F401
    _find_adjacent_value,
    _find_position_match,
    _get_visual_zone,
    _get_zone_by_threshold,
    _run_3_3,
)
from services.stages.stage3_structural.constants import (  # noqa: F401
    _COMPILED_DYNAMIC_PATTERNS,
    _DYNAMIC_PATTERNS,
)
from services.stages.stage3_structural.multi_example_analysis import (  # noqa: F401
    _get_nlp,
    _run_3_1,
    _smart_classify,
)
from services.stages.stage3_structural.repeated_sections import (  # noqa: F401
    collect_repeated_block_ids,
    detect_repeated_sections,
)
from services.stages.stage3_structural.section_utils import (  # noqa: F401
    _assign_images_to_sections,
    _assign_tables_to_sections,
    _assign_visual_elements_to_sections,
    _barcode_bboxes_from_tree,
    _bbox_contains,
    _build_visual_table_from_blocks,
    _classify_image_area_heuristic,
    _extract_barcode_value,
    _get_horizontal_separators,
    _line_inside_any_barcode,
    _split_by_drawn_lines,
    _split_by_gap,
    _zones_from_thresholds,
    _zones_from_visual_regions,
)
from services.stages.stage3_structural.semantic_utils import (  # noqa: F401
    _apply_suggested_bindings,
    _extract_semantic_name,
    _get_conditional_pdfs,
    _infer_section_name,
    _levenshtein_similarity,
    _normalize_text,
    _section_variant,
    _suggest_xsd_binding,
)
from services.stages.stage3_structural.tree_builder import (  # noqa: F401
    _build_tree,
    _run_3_4,
)
from services.stages.stage3_structural.visual_analysis import (  # noqa: F401
    _VISUAL_ANALYSIS_PROMPT,
    VALID_REGION_TYPES,
    _fallback_visual_analysis,
    _parse_visual_response,
    _run_3_2,
    _summarize_extraction,
)

__all__ = [
    # constants
    "_DYNAMIC_PATTERNS",
    "_COMPILED_DYNAMIC_PATTERNS",
    # multi_example_analysis
    "_get_nlp",
    "_smart_classify",
    "_run_3_1",
    # visual_analysis
    "_VISUAL_ANALYSIS_PROMPT",
    "VALID_REGION_TYPES",
    "_summarize_extraction",
    "_parse_visual_response",
    "_fallback_visual_analysis",
    "_run_3_2",
    # classification
    "_get_visual_zone",
    "_get_zone_by_threshold",
    "_find_position_match",
    "_find_adjacent_value",
    "_run_3_3",
    # section_utils
    "_zones_from_visual_regions",
    "_zones_from_thresholds",
    "_split_by_drawn_lines",
    "_split_by_gap",
    "_get_horizontal_separators",
    "_extract_barcode_value",
    "_barcode_bboxes_from_tree",
    "_line_inside_any_barcode",
    "_bbox_contains",
    "_assign_images_to_sections",
    "_assign_tables_to_sections",
    "_assign_visual_elements_to_sections",
    "_classify_image_area_heuristic",
    "_build_visual_table_from_blocks",
    # semantic_utils
    "_normalize_text",
    "_levenshtein_similarity",
    "_suggest_xsd_binding",
    "_apply_suggested_bindings",
    "_extract_semantic_name",
    "_infer_section_name",
    "_section_variant",
    "_get_conditional_pdfs",
    # repeated_sections (Story 48.4)
    "detect_repeated_sections",
    "collect_repeated_block_ids",
    # tree_builder
    "_run_3_4",
    "_build_tree",
]
