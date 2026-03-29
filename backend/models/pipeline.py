"""Pipeline orchestrator models: PipelineDefinition."""

from __future__ import annotations

from typing import List


class PipelineDefinition:
    """Top-level pipeline composed of ordered blocks."""

    def __init__(self, blocks: List) -> None:
        self.blocks = blocks

    @property
    def total_stages(self) -> int:
        return sum(len(b.stages) for b in self.blocks)

    def __repr__(self) -> str:
        return f"<Pipeline blocks={len(self.blocks)} total_stages={self.total_stages}>"
