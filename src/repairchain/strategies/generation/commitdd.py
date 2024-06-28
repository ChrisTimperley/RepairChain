from __future__ import annotations

import typing as t

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.minimize_diff import DiffMinimizer
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff


class CommitDD(PatchGenerationStrategy):
    diagnosis: Diagnosis

    def build(self, diagnosis: Diagnosis) -> t.Self:
        self.diagnosis = diagnosis

    def run(self) -> list[Diff]:
        minimizer = DiffMinimizer(
            self.diagnosis.project,
            commit_to_diff(self.diagnosis.project.triggering_commit))
        # OK the problem is, we have the slice of the undone commit we need 