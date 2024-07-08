from __future__ import annotations

__all__ = ("DeleteStatementsStrategy",)

import typing as t
from dataclasses import dataclass

from overrides import overrides

from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


@dataclass
class DeleteStatementsStrategy(PatchGenerationStrategy):
    project: Project
    diagnosis: Diagnosis

    @overrides
    def run(self) -> list[Diff]:
        # TODO filter statements by parent function
        raise NotImplementedError
