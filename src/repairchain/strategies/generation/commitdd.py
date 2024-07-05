from __future__ import annotations

import subprocess
import tempfile
import typing as t
from dataclasses import dataclass
from pathlib import Path

import git
from loguru import logger

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.minimize_diff import MinimizeForSuccess
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.project import Project


@dataclass
class CommitDD(PatchGenerationStrategy):
    diagnosis: Diagnosis
    project: Project

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> CommitDD:
        return cls(diagnosis=diagnosis, project=diagnosis.project)

    # performs cleanup, intended for the temporary branch created to rebase. is
    # also called before creating the temporary branch, mostly because in
    # testing, CLG created/failed to clean it up a lot.
    # silently swallows git command errors, most likely a failure to delete the
    # branch in question (such as if it doesn't exist).
    # CLG has thought about this and believes it's the desired outcome.
    def _cleanup_branch(self, repo: git.Repo, primary_branch: str, branch_name: str) -> None:
        try:
            repo.git.checkout(primary_branch)
            repo.git.branch("-D", branch_name)
        except git.exc.GitCommandError:
            return

    def _find_minimal_diff(self) -> Diff | None:
        project = self.diagnosis.project
        repo = project.repository

        # compute a reverse diff between the triggering commit and HEAD
        sha = project.triggering_commit.hexsha
        reverse_diff = Diff.from_unidiff(project.repository.git.diff(sha, sha + "^", unified=True))

        minimizer = MinimizeForSuccess.build(
            project=project,
            commit=project.triggering_commit,
            triggering_diff=reverse_diff,
        )
        minimized = minimizer.minimize()

        # we have the slice of the undone commit we need, now we need it to
        # apply to the program at its _current_ commit.  We:
        # (1) branch at the triggering commit,
        # (2) apply the change (using patch, not git.apply, because the former works
        # and the latter often doesn't for some reason),
        # (3) rebase the change on top of the main branch, and then
        # (4) getting the last commit as a diff.
        primary_branch = repo.active_branch.name

        # branch from the broken commit...
        commit_sha = project.triggering_commit.hexsha
        new_branch_name = f"branch-{commit_sha[:8]}"
        self._cleanup_branch(repo, primary_branch, new_branch_name)

        try:
            repo.git.branch(new_branch_name, project.triggering_commit)
            repo.git.checkout(new_branch_name)

            # make a commit consisting of only the minimized undo
            with tempfile.NamedTemporaryFile(mode="w", delete=True, encoding="utf-8") as temp_diff_file:
                temp_diff_file.write(str(minimized))
                temp_diff_file_path = temp_diff_file.name
                temp_diff_file.close()
                repo_path = Path.resolve(project.local_repository_path)

                command_args = ["patch", "-p1", "-i", temp_diff_file_path]
                result = subprocess.run(command_args, cwd=repo_path, check=False)
                if result.returncode == 0:
                    repo.git.add(A=True)
                    repo.index.commit("undo minimal changes")
                    repo.git.rebase(primary_branch)

                    # grab the head commit, which should undo the badness, turn that into a diff
                    return commit_to_diff(project.repository.active_branch.commit)

                logger.error("failed to apply patch")

        except git.exc.GitCommandError:
            logger.exception("failed to create branch or rebase")
        finally:
            self._cleanup_branch(repo, primary_branch, new_branch_name)

        return None

    def run(self) -> list[Diff]:
        minimal_diff = self._find_minimal_diff()
        return [minimal_diff] if minimal_diff else []