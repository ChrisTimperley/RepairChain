from __future__ import annotations

import typing as t

from repairchain.actions.commit_to_diff import commit_to_diff

# from repairchain.actions.minimize_diff import MinimizeForSuccess, SimpleTestDiffMinimizerSuccess
from repairchain.actions.minimize_diff import SimpleTestDiffMinimizerSuccess
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis


class CommitDD(PatchGenerationStrategy):
    diagnosis: Diagnosis

    def build(self, diagnosis: Diagnosis) -> t.Self:
        self.diagnosis = diagnosis

    def run(self) -> list[Diff]:
        project = self.diagnosis.project
        commit = project.triggering_commit
        repo = project.repository

        sha = commit.hexsha
        reverse_diff_str = project.repository.git.diff(sha, sha + "^", R=True, unified=True)
        reverse_diff = Diff.from_unidiff(reverse_diff_str)
        # FIXME: this is for testing
        # minimizer = MinimizeForSuccess(project, reverse_diff)
        minimizer = SimpleTestDiffMinimizerSuccess(project, reverse_diff)
        minimized = minimizer.minimize_diff(reverse_diff)

        # OK the problem is, we have the slice of the undone commit we need, now we need it to apply
        # to the program at the current commit
        # start by figuring out where we're starting...
        primary_branch = project.repository.active_branch.name

        # branch from the broken commit...
        commit_sha = project.triggering_commit.hexsha  # Replace with the actual commit SHA
        new_branch_name = "branch-" + str(commit_sha)  # Replace with your desired new branch name

        repo.git.branch(new_branch_name, project.triggering_commit)
        repo.git.checkout(new_branch_name)

        # make a commit with the minimized undo
        diffstr = str(minimized)
        repo.git.apply(diffstr)
        repo.git.add(A=True)
        repo.git.index.commit("undo what we did")

        repo.git.rebase(primary_branch)

        # sure hope that worked
        # FIXME: add error handling

        # now, get the head commit, which should undo the badness, turn that into a diff
        undoing_diff = commit_to_diff(project.repository.active_branch.commit)
        repo.git.checkout(primary_branch)

        #  close the branch I made, for tidiness
        repo.git.branch("-D", new_branch_name)
        return undoing_diff
