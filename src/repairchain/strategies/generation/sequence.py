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
    @overrides
    def applies(cls, _: Diagnosis) -> bool:
        return True

    @overrides
    def run(self) -> list[Diff]:
        candidates: list[Diff] = []

        for strategy in self.strategies:
            try:
                name = strategy.__class__.__name__
                logger.info(f"generating patches with strategy: {name}...")
                generated_patches = strategy.run()
                candidates += generated_patches
            except Exception:  # noqa: BLE001
                logger.exception(f"failed to generate patches with strategy: {name}")
            else:
                logger.info(f"generated {len(generated_patches)} patches with strategy: {name}")

        return candidates
