"""Pipeline orchestrator models: StageDefinition, BlockDefinition, PipelineDefinition, StageRegistry."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------

class StageDefinition:
    """Represents a single processing stage within a pipeline block."""

    def __init__(
        self,
        stage_number: int,
        name: str,
        block_id: int,
        estimated_duration: float = 1.0,
        execute_fn: Optional[Callable[..., Coroutine[Any, Any, Dict[str, Any]]]] = None,
    ) -> None:
        self.stage_number = stage_number
        self.name = name
        self.block_id = block_id
        self.estimated_duration = estimated_duration
        self._execute_fn = execute_fn

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this stage. Subclasses or injected functions override this."""
        if self._execute_fn is not None:
            return await self._execute_fn(context)
        # Default stub: return empty dict
        await asyncio.sleep(0)
        return {}

    def __repr__(self) -> str:
        return f"<Stage #{self.stage_number} block={self.block_id} name={self.name!r}>"


class BlockDefinition:
    """Represents a logical processing block containing one or more stages."""

    def __init__(self, block_id: int, name: str) -> None:
        self.block_id = block_id
        self.name = name
        self.stages: List[StageDefinition] = []

    def add_stage(self, stage: StageDefinition) -> None:
        self.stages.append(stage)

    def __repr__(self) -> str:
        return f"<Block #{self.block_id} name={self.name!r} stages={len(self.stages)}>"


class PipelineDefinition:
    """Top-level pipeline composed of ordered blocks."""

    def __init__(self, blocks: List[BlockDefinition]) -> None:
        self.blocks = blocks

    @property
    def total_stages(self) -> int:
        return sum(len(b.stages) for b in self.blocks)

    def __repr__(self) -> str:
        return f"<Pipeline blocks={len(self.blocks)} total_stages={self.total_stages}>"


# ---------------------------------------------------------------------------
# Stage Registry
# ---------------------------------------------------------------------------

class StageRegistry:
    """Dynamic registry that holds the canonical pipeline definition.

    Allows adding and removing stages at runtime for future extensibility.
    """

    def __init__(self) -> None:
        self._blocks: Dict[int, BlockDefinition] = {}

    # --- Block management ---------------------------------------------------

    def register_block(self, block_id: int, name: str) -> BlockDefinition:
        block = BlockDefinition(block_id=block_id, name=name)
        self._blocks[block_id] = block
        return block

    def get_block(self, block_id: int) -> Optional[BlockDefinition]:
        return self._blocks.get(block_id)

    # --- Stage management ---------------------------------------------------

    def register_stage(
        self,
        stage_number: int,
        name: str,
        block_id: int,
        estimated_duration: float = 1.0,
        execute_fn: Optional[Callable[..., Coroutine[Any, Any, Dict[str, Any]]]] = None,
    ) -> StageDefinition:
        if block_id not in self._blocks:
            raise ValueError(f"Block {block_id} is not registered. Call register_block first.")
        stage = StageDefinition(
            stage_number=stage_number,
            name=name,
            block_id=block_id,
            estimated_duration=estimated_duration,
            execute_fn=execute_fn,
        )
        self._blocks[block_id].add_stage(stage)
        return stage

    def remove_stage(self, stage_number: int) -> bool:
        """Remove a stage by its global stage number. Returns True if removed."""
        for block in self._blocks.values():
            for i, stage in enumerate(block.stages):
                if stage.stage_number == stage_number:
                    block.stages.pop(i)
                    return True
        return False

    def build_pipeline(self) -> PipelineDefinition:
        """Build a PipelineDefinition from the current registry state."""
        ordered_blocks = [self._blocks[k] for k in sorted(self._blocks.keys())]
        return PipelineDefinition(blocks=ordered_blocks)

    def all_stages(self) -> List[StageDefinition]:
        """Return all stages in global execution order."""
        result: List[StageDefinition] = []
        for block in sorted(self._blocks.values(), key=lambda b: b.block_id):
            result.extend(block.stages)
        return result


# ---------------------------------------------------------------------------
# Default pipeline registry (28 stages across 8 blocks)
# ---------------------------------------------------------------------------

def build_default_registry() -> StageRegistry:
    """Construct the default 8-block / 28-stage registry with stub executors."""
    registry = StageRegistry()

    # Block 1 — Aquisição (1 stage)
    registry.register_block(1, "Aquisição")
    registry.register_stage(1, "Upload & Storage", block_id=1, estimated_duration=0.5)

    # Block 2 — PDF Parsing (5 stages)
    registry.register_block(2, "PDF Parsing")
    registry.register_stage(2, "Text Extraction", block_id=2, estimated_duration=2.0)
    registry.register_stage(3, "Text Reconstruction", block_id=2, estimated_duration=1.5)
    registry.register_stage(4, "Font Extraction → CSS", block_id=2, estimated_duration=1.0)
    registry.register_stage(5, "Image Extraction", block_id=2, estimated_duration=2.0)
    registry.register_stage(6, "Grid Detection", block_id=2, estimated_duration=1.5)

    # Block 3 — Layout Discovery (5 stages)
    registry.register_block(3, "Layout Discovery")
    registry.register_stage(7, "Skeleton Builder", block_id=3, estimated_duration=1.5)
    registry.register_stage(8, "Page Clustering", block_id=3, estimated_duration=1.0)
    registry.register_stage(9, "Representative Selection", block_id=3, estimated_duration=0.5)
    registry.register_stage(10, "Fingerprint Generation", block_id=3, estimated_duration=1.0)
    registry.register_stage(11, "Registry Lookup", block_id=3, estimated_duration=0.5)

    # Block 4 — Layout Intelligence (5 stages)
    registry.register_block(4, "Layout Intelligence")
    registry.register_stage(12, "Layout Alignment", block_id=4, estimated_duration=1.5)
    registry.register_stage(13, "Multi-Example Analysis", block_id=4, estimated_duration=2.0)
    registry.register_stage(14, "Stability Classification", block_id=4, estimated_duration=1.0)
    registry.register_stage(15, "Variant Detection", block_id=4, estimated_duration=1.0)
    registry.register_stage(16, "Normalization", block_id=4, estimated_duration=0.5)

    # Block 5 — Tables (2 stages)
    registry.register_block(5, "Tables")
    registry.register_stage(17, "Table Detection", block_id=5, estimated_duration=1.5)
    registry.register_stage(18, "Table Structuring", block_id=5, estimated_duration=2.0)

    # Block 6 — Semantic + Vision (4 stages)
    registry.register_block(6, "Semantic + Vision")
    registry.register_stage(19, "Semantic Analysis", block_id=6, estimated_duration=2.5)
    registry.register_stage(20, "Visual Segmentation", block_id=6, estimated_duration=2.0)
    registry.register_stage(21, "Visual Interpretation", block_id=6, estimated_duration=2.0)
    registry.register_stage(22, "Self-Check", block_id=6, estimated_duration=1.0)

    # Block 7 — Matching (2 stages)
    registry.register_block(7, "Matching")
    registry.register_stage(23, "Field Matching", block_id=7, estimated_duration=1.5)
    registry.register_stage(24, "Format Detection", block_id=7, estimated_duration=1.0)

    # Block 8 — Validation (4 stages)
    registry.register_block(8, "Validation")
    registry.register_stage(25, "Confidence Scoring", block_id=8, estimated_duration=1.0)
    registry.register_stage(26, "Layout Consistency", block_id=8, estimated_duration=1.0)
    registry.register_stage(27, "Template Draft", block_id=8, estimated_duration=2.0)
    registry.register_stage(28, "Pipeline Result", block_id=8, estimated_duration=0.5)

    return registry


# Module-level singleton used by the executor and routers
default_registry: StageRegistry = build_default_registry()
