from __future__ import annotations

__all__ = ("SequenceStrategy",)

import typing as t
from dataclasses import dataclass

from loguru import logger
from overrides import overrides

from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff


@dataclass
class SequenceStrategy(PatchGenerationStrategy):
    strategies: t.Sequence[PatchGenerationStrategy]

    @classmethod
    def applies(cls, diagnosis: Diagnosis) -> bool:
        return True

    @overrides
    def run(self) -> t.Iterator[Diff]:
        for strategy in self.strategies:
            num_patches_generated_by_strategy = 0
            try:
                name = strategy.__class__.__name__
                logger.info(f"generating patches with strategy: {name}...")
                for candidate in strategy.run():
                    yield candidate
                    num_patches_generated_by_strategy += 1
            except Exception:  # noqa: BLE001
                logger.exception(f"failed to generate patches with strategy: {name}")
            else:
                logger.info(f"generated {num_patches_generated_by_strategy} patches with strategy: {name}")
