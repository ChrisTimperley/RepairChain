from __future__ import annotations

__all__ = ("SequenceStrategy",)

import typing as t
from dataclasses import dataclass

from overrides import overrides

from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff


@dataclass
class SequenceStrategy(PatchGenerationStrategy):
    strategies: t.Sequence[PatchGenerationStrategy]

    @overrides
    def run(self) -> list[Diff]:
        candidates: list[Diff] = []
        for strategy in self.strategies:
            candidates += strategy.run()
        return candidates
