from __future__ import annotations

__all__ = ("TemplateBasedRepair",)

import typing as t
from dataclasses import dataclass

from repairchain.models.bug_type import BugType
from repairchain.strategies.generation.base import PatchGenerationStrategy
from repairchain.strategies.generation.template.bounds_check import BoundsCheckStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff
    from repairchain.strategies.generation.template.base import TemplateGenerationStrategy


@dataclass
class TemplateBasedRepair(PatchGenerationStrategy):
    diagnosis: Diagnosis
    generators: list[TemplateGenerationStrategy]

    @classmethod
    def build(
        cls,
        diagnosis: Diagnosis,
    ) -> TemplateBasedRepair:
        generators: list[TemplateGenerationStrategy] = []
        match diagnosis.bug_type:
            case BugType.OUT_OF_BOUNDS_READ | BugType.OUT_OF_BOUNDS_WRITE:
                generators.append(BoundsCheckStrategy.build(diagnosis))
            case _:
                raise NotImplementedError

        return cls(
            diagnosis=diagnosis,
            generators=generators,
        )

    def run(self) -> list[Diff]:
        diffs: list[Diff] = []
        for g in self.generators:
            diffs += g.run()
        return diffs
