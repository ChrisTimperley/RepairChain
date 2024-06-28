from __future__ import annotations

import typing as t

from sourcelocation import FileHunk
from sourcelocation.diff import ContextLine, DeletedLine, HunkLine, InsertedLine

from repairchain.actions.commit_to_diff import commit_to_diff, commit_to_files
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
        project = self.diagnosis.project

        minimizer = DiffMinimizer(project, commit_to_diff(project.triggering_commit))
        # OK the problem is, we have the slice of the undone commit we need, now we need it to apply
        # to the program at the current commit
        # OK I need each file at head
        commit_sha = project.triggering_commit.binsha  # Replace with the actual commit SHA
        new_branch_name = "branch-" + str(commit_sha) # Replace with your desired new branch name
        project.repository.git.branch(new_branch_name, project.triggering_commit)
        project.repository.git.checkout(new_branch_name)

        # for d in minimizer.minimize_diff():
        #    for fd in d.file_diffs:
