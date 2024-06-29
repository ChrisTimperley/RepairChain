from __future__ import annotations

import os
import tempfile
import typing as t
from contextlib import chdir
from dataclasses import dataclass

import git

from repairchain.actions.commit_to_diff import commit_to_diff

# from repairchain.actions.minimize_diff import MinimizeForSuccess, SimpleTestDiffMinimizerSuccess
from repairchain.actions.minimize_diff import SimpleTestDiffMinimizerSuccess
from repairchain.models.diff import Diff
from repairchain.models.project import Project  # noqa: TCH001
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis


@dataclass
class CommitDD(PatchGenerationStrategy):
    diagnosis: Diagnosis
    project: Project

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> CommitDD:
        return cls(diagnosis=diagnosis, project=diagnosis.project)

    # FIXME: check that the branch actually exists
    def _cleanup_branch(self, repo: git.Repo, primary_branch: str, branch_name: str) -> None:
        try:
            repo.git.checkout(primary_branch)
            repo.git.branch("-D", branch_name)
        except git.exc.GitCommandError:
            return

    def run(self) -> list[Diff]:
        project = self.diagnosis.project
        commit = project.triggering_commit
        repo = project.repository

        sha = commit.hexsha
        reverse_diff_str = project.repository.git.diff(sha, sha + "^", unified=True)
        reverse_diff = Diff.from_unidiff(reverse_diff_str)
        # FIXME: this is for testing
        # minimizer = MinimizeForSuccess(project, reverse_diff)
        minimizer = SimpleTestDiffMinimizerSuccess(project, reverse_diff)
        minimized = minimizer.minimize_diff()

        # OK the problem is, we have the slice of the undone commit we need, now we need it to apply
        # to the program at the current commit
        # start by figuring out where we're starting...
        primary_branch = project.repository.active_branch.name

        # branch from the broken commit...
        commit_sha = project.triggering_commit.hexsha  # Replace with the actual commit SHA
        new_branch_name = "branch-" + str(commit_sha[:8])  # Replace with your desired new branch name
        self._cleanup_branch(repo, primary_branch, new_branch_name)

        repo.git.branch(new_branch_name, project.triggering_commit)
        repo.git.checkout(new_branch_name)
        # make a commit with the minimized undo
        diffstr = str(minimized)
        with tempfile.NamedTemporaryFile(mode='w', delete=True, encoding="locale") as temp_diff_file:
            temp_diff_file.write(diffstr)
            temp_diff_file_path = temp_diff_file.name
            repo_path = os.path.abspath(project.local_repository_path)

            with chdir(repo_path):
                # FIXME: try with patch instead, with apologies to dornja
                os.system(f'patch -p1 -i {temp_diff_file_path}')


        # repo.git.apply(temp_diff_file_path)


        # FIXME: error handle git, fix the tests while we're at it to pick the correct hunks to properly test this
        repo.git.add(A=True)
        repo.index.commit("undo what we did")

        repo.git.rebase(primary_branch)

        # sure hope that worked
        # FIXME: add error handling

        # now, get the head commit, which should undo the badness, turn that into a diff
        undoing_diff = commit_to_diff(project.repository.active_branch.commit)
        self._cleanup_branch(repo, primary_branch, new_branch_name)
        return [undoing_diff]
