from __future__ import annotations

import subprocess
import tempfile
import typing as t
from dataclasses import dataclass
from pathlib import Path

import git
from loguru import logger

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.models.diff import Diff
from repairchain.models.patch_outcome import PatchOutcome
from repairchain.strategies.generation.base import PatchGenerationStrategy
from repairchain.util import dd_minimize

if t.TYPE_CHECKING:
    from sourcelocation.diff import FileHunk

    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.project import Project


@dataclass
class MinimalPatchReversion(PatchGenerationStrategy):
    diagnosis: Diagnosis
    project: Project

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> MinimalPatchReversion:
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
        repo = self.project.repository
        triggering_commit = self.project.triggering_commit
        triggering_commit_parent = triggering_commit.parents[0]

        # compute a diff that reverses the changes introduces by the triggering commit
        reverse_diff = Diff.from_unidiff(
            repo.git.diff(triggering_commit, triggering_commit_parent, unified=True),
        ).strip(1)

        def tester(hunks: t.Sequence[FileHunk]) -> bool:
            as_diff = Diff.from_file_hunks(list(hunks))
            outcome = self.project.validator.validate(
                candidate=as_diff,
                commit=triggering_commit,
            )
            return outcome == PatchOutcome.PASSED

        to_minimize = list(reverse_diff.file_hunks)
        minimized_hunks = dd_minimize(to_minimize, tester)
        minimized = Diff.from_file_hunks(minimized_hunks)

        # we have the slice of the undone commit we need, now we need it to
        # apply to the program at its _current_ commit.  We:
        # (1) branch at the triggering commit,
        # (2) apply the change (using patch, not git.apply, because the former works
        # and the latter often doesn't for some reason),
        # (3) rebase the change on top of the main branch, and then
        # (4) getting the last commit as a diff.
        primary_branch = repo.active_branch.name

        # branch from the broken commit...
        commit_sha = triggering_commit.hexsha
        new_branch_name = f"branch-{commit_sha[:8]}"
        self._cleanup_branch(repo, primary_branch, new_branch_name)

        try:
            repo_path = Path.resolve(self.project.local_repository_path)
            repo.git.branch(new_branch_name, triggering_commit)
            repo.git.checkout(new_branch_name)

            # make a commit consisting of only the minimized undo
            temp_patch_path = Path(tempfile.mkstemp(suffix=".diff")[1])
            try:
                with temp_patch_path.open("w", encoding="utf-8") as temp_patch_file:
                    temp_patch_file.write(str(minimized))

                command_args = [
                    "patch",
                    "-u",
                    "-p0",
                    "-i",
                    temp_patch_path,
                    "-d",
                    str(repo_path),
                ]
                logger.debug(f"applying patch: {command_args}")
                subprocess.run(
                    command_args,
                    check=True,
                    stdin=subprocess.DEVNULL,
                )

            finally:
                temp_patch_path.unlink()

            repo.git.add(A=True)
            repo.index.commit("undo minimal changes")
            repo.git.rebase(primary_branch)

            # grab the head commit, which should undo the badness, turn that into a diff
            return commit_to_diff(self.project.repository.active_branch.commit)

        except subprocess.CalledProcessError:
            logger.exception("failed to apply patch")
        except git.exc.GitCommandError:
            logger.exception("failed to create branch or rebase")
        finally:
            self._cleanup_branch(repo, primary_branch, new_branch_name)

        return None

    def run(self) -> list[Diff]:
        minimal_diff = self._find_minimal_diff()
        return [minimal_diff] if minimal_diff else []
