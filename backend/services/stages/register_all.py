"""Bootstrap module — registers all Bloco 2 stage implementations.

Import this module once (e.g., at application startup in main.py) to replace
the stub executors in the default_registry with the real implementations.

Usage:
    from services.stages.register_all import register_bloco2
    register_bloco2()
"""

from __future__ import annotations


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
