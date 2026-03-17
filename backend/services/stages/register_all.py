"""Bootstrap module — registers all stage implementations.

Import this module once (e.g., at application startup in main.py) to replace
the stub executors in the default_registry with the real implementations.

Usage:
    from services.stages.register_all import register_bloco1, register_bloco2, register_bloco3
    register_bloco1()
    register_bloco2()
    register_bloco3()
"""

from __future__ import annotations


def register_bloco1(registry=None) -> None:
    """Register all Bloco 1 (Aquisição) stages in the given registry.

    Currently registers the XSD Parsing stage (stage 28).
    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import xsd_parser

    xsd_parser.register(registry)


def register_bloco2(registry=None) -> None:
    """Register all Bloco 2 stages in the given registry.

    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import (
        text_extraction,
        text_reconstruction,
        font_extraction,
        image_extraction,
        grid_detection,
    )

    text_extraction.register(registry)
    text_reconstruction.register(registry)
    font_extraction.register(registry)
    image_extraction.register(registry)
    grid_detection.register(registry)


def register_bloco3(registry=None) -> None:
    """Register all Bloco 3 (Layout Discovery) stages in the given registry.

    Registers stages 7–11: Skeleton Builder, Page Clustering,
    Representative Selection, Fingerprint Generation, Registry Lookup.
    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import (
        skeleton_builder,
        page_clustering,
        representative_selection,
        fingerprint_generation,
        registry_lookup,
    )

    skeleton_builder.register(registry)
    page_clustering.register(registry)
    representative_selection.register(registry)
    fingerprint_generation.register(registry)
    registry_lookup.register(registry)


def register_bloco4(registry=None) -> None:
    """Register all Bloco 4 (Layout Intelligence) stages in the given registry.

    Registers stages 12–16: Layout Alignment, Multi-Example Analysis,
    Stability Classification, Variant Detection, Intelligence Normalization.
    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import (
        layout_alignment,
        multi_example_analysis,
        stability_classification,
        variant_detection,
        intelligence_normalization,
    )

    layout_alignment.register(registry)
    multi_example_analysis.register(registry)
    stability_classification.register(registry)
    variant_detection.register(registry)
    intelligence_normalization.register(registry)


def register_bloco5(registry=None) -> None:
    """Register all Bloco 5 (Tables) stages in the given registry.

    Registers stages 17–18: Table Detection, Table Structuring.
    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import (
        table_detection,
        table_structuring,
    )

    table_detection.register(registry)
    table_structuring.register(registry)


def register_bloco6_semantic(registry=None) -> None:
    """Register the Semantic Analysis stage (Stage 19) from Bloco 6.

    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import semantic_analysis

    semantic_analysis.register(registry)


def register_bloco6_vision(registry=None) -> None:
    """Register Vision AI stages (20-22) from Bloco 6.

    Registers:
        Stage 20 — Visual Segmentation
        Stage 21 — Visual Interpretation
        Stage 22 — Self-Check

    If *registry* is None, the module-level default_registry is used.
    """
    if registry is None:
        from models.pipeline import default_registry
        registry = default_registry

    from services.stages import (
        visual_segmentation,
        visual_interpretation,
        vision_self_check,
    )

    visual_segmentation.register(registry)
    visual_interpretation.register(registry)
    vision_self_check.register(registry)


def register_all(registry=None) -> None:
    """Register stages from all implemented blocks. Convenience wrapper."""
    register_bloco1(registry)
    register_bloco2(registry)
    register_bloco3(registry)
    register_bloco4(registry)
    register_bloco5(registry)
    register_bloco6_semantic(registry)
    register_bloco6_vision(registry)
