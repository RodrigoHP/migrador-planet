"""Stage 4 — Field Mapping sub-package.

Story 41.3 — stage4_field_mapping.py decomposed into:
  - constants.py          : shared constants (thresholds, weights, prompts)
  - xsd_integration.py   : Steps 4.1, 4.2, 4.3
  - section_matching.py  : Steps 4.4, 4.5
  - scoring_validation.py: Steps 4.6, 4.7

All symbols are re-exported here for backward compatibility.
"""

from __future__ import annotations

from services.stages.stage4_mapping.constants import (  # noqa: F401
    _BATCH_MATCH_PROMPT,
    _TYPE_FORMAT_COMPAT,
    AMBIGUITY_THRESHOLD,
    GEMINI_FLASH_MODEL,
    HIGH_CONFIDENCE_THRESHOLD,
    SECTION_MATCH_MIN_SCORE,
    THRESHOLD_APPROVED,
    THRESHOLD_REVIEW,
    WEIGHTS,
)
from services.stages.stage4_mapping.scoring_validation import (  # noqa: F401
    _get_anchor_detection,
    _get_field_variability,
    _get_grid_quality,
    _get_layout_stability,
    _get_required_paths,
    _get_vision_agreement,
    _step_4_6_confidence_scoring,
    _step_4_7_consistency_validation,
    _validate_type_format,
)
from services.stages.stage4_mapping.section_matching import (  # noqa: F401
    _extract_sections,
    _fuzzy_batch_match,
    _fuzzy_match_single,
    _get_complex_nodes,
    _get_pair_section,
    _get_xsd_type,
    _group_pairs_by_section,
    _llm_batch_match_scoped,
    _make_mapping_v2,
    _section_xsd_similarity,
    _step_4_4_section_xsd_matching,
    _step_4_5_field_matching,
)
from services.stages.stage4_mapping.xsd_integration import (  # noqa: F401
    _FORMAT_PATTERNS,
    _JS_FUNCTIONS,
    _detect_format,
    _find_nearest_label_block,
    _get_block_bbox,
    _get_block_info,
    _get_block_text,
    _step_4_1_xsd_parsing,
    _step_4_2_pair_validation,
    _step_4_3_format_pre_detection,
)
