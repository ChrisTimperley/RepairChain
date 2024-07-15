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
    max_patches: int
    max_patches_for_one_strategy: int

    @classmethod
    def applies(cls, diagnosis: Diagnosis) -> bool:
        return True

    @classmethod
    def build(
        cls,
        diagnosis: Diagnosis,
        strategies: t.Sequence[PatchGenerationStrategy],
    ) -> t.Self:
        # FIXME decide this limit!
        max_patches = 100
        max_patches_for_one_strategy = 20

        return cls(
            diagnosis=diagnosis,
            strategies=strategies,
            max_patches=max_patches,
            max_patches_for_one_strategy=max_patches_for_one_strategy,
        )

    def _run_strategy(self, strategy: PatchGenerationStrategy) -> t.Iterator[Diff]:
        name = strategy.__class__.__name__
        logger.info(f"generating patches with strategy: {name}...")
        num_patches = 0
        try:
            for candidate in strategy.run():
                if num_patches >= self.max_patches_for_one_strategy:
                    logger.warning(
                        f"reached max patches limit for strategy: {name} ({num_patches})",
                    )
                    break
                yield candidate
                num_patches += 1
        except Exception:  # noqa: BLE001
            logger.exception(f"failed to generate patches with strategy: {name}")
        else:
            logger.info(f"generated {num_patches} patches with strategy: {name}")

    @overrides
    def run(self) -> t.Iterator[Diff]:
        num_patches = 0

        for strategy in self.strategies:
            for patch in self._run_strategy(strategy):
                if num_patches >= self.max_patches:
                    logger.warning(
                        f"reached max patches limit ({num_patches}) for all strategies",
                    )
                    break
                yield patch
                num_patches += 1

        logger.info(f"finished generating {num_patches} patches")
