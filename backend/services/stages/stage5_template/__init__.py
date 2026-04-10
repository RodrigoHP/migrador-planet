"""Stage 5 — Template Generation sub-package.

Story 41.3 — stage5_template_generation.py decomposed into:
  - html_helpers.py       : constants, barcode, bbox, color/font utils, field/table HTML helpers
  - html_tree.py          : _tree_to_html, _step_5_1_tree_driven_html
  - css_generation.py     : _step_5_2_css_from_extraction
  - coverage_overlay.py   : _step_5_3_coverage, _step_5_4_overlay_items, anchors
  - variation_matrix.py   : _step_5_5_variation_matrix
  - result_assembly.py    : _step_5_6_pipeline_result, _step_5_7_persist, helpers

All symbols are re-exported here for backward compatibility.
"""

from __future__ import annotations

from services.stages.stage5_template.coverage_overlay import (  # noqa: F401
    _add_table_container_overlays,
    _count_mapped_charts,
    _count_mapped_tables,
    _count_nodes_by_type,
    _generate_anchors,
    _get_page_dimensions,
    _step_5_3_coverage,
    _step_5_4_overlay_items,
)
from services.stages.stage5_template.css_generation import (  # noqa: F401
    _step_5_2_css_from_extraction,
)
from services.stages.stage5_template.html_helpers import (  # noqa: F401
    _A4_HEIGHT_PTS,
    _A4_WIDTH_PTS,
    _BASE_CSS_RESET,
    _SCALE_X,
    _SCALE_Y,
    _barcode_to_svg_content,
    _bbox_to_absolute_style,
    _color_int_to_hex,
    _font_class_with_style,
    _generate_field_html,
    _generate_table_html,
    _is_array_field,
    _node_is_array,
    _sanitize_font_class,
    _sanitize_name,
)
from services.stages.stage5_template.html_tree import (  # noqa: F401
    _step_5_1_tree_driven_html,
    _tree_to_html,
)
from services.stages.stage5_template.result_assembly import (  # noqa: F401
    _build_page_config,
    _convert_tree_to_css_coords,
    _extract_visual_data,
    _get_document_type,
    _normalize_confidence,
    _serialise_parsed_documents,
    _step_5_6_pipeline_result,
    _step_5_7_persist,
)
from services.stages.stage5_template.variation_matrix import (  # noqa: F401
    _step_5_5_variation_matrix,
)
