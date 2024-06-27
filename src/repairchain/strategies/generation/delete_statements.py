from __future__ import annotations

__all__ = ("DeleteStatementsStrategy",)

import typing as t
from dataclasses import dataclass

from repairchain.actions.index_statements import index_statements
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


@dataclass
class DeleteStatementsStrategy(PatchGenerationStrategy):
    project: Project
    diagnosis: Diagnosis

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> DeleteStatementsStrategy:
        return cls(
            project=diagnosis.project,
            diagnosis=diagnosis,
        )

    def run(self) -> list[Diff]:
        implicated_statements = index_statements(
            project=self.project,
            version=self.project.head,
            restrict_to_functions=self.diagnosis.implicated_functions,
        )
        print(implicated_statements)
        raise NotImplementedError
