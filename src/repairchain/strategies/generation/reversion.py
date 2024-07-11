from __future__ import annotations

import subprocess
import tempfile
import typing as t
from contextlib import suppress
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

    def _cleanup(
        self,
        repo: git.Repo,
        restore_to_commit: git.Commit,
        restore_to_branch: str | None,
        temporary_rebase_branch: str,
    ) -> None:
        """Restores the initial state of the Git repo prior to running this strategy."""
        with suppress(git.exc.GitCommandError):
            repo.git.rebase("--abort")
        with suppress(git.exc.GitCommandError):
            repo.git.merge("--abort")
        with suppress(git.exc.GitCommandError):
            repo.git.clean("-xdf")
        with suppress(git.exc.GitCommandError):
            if not repo.head.is_detached and repo.active_branch.name == restore_to_branch:
                repo.git.branch("-D", temporary_rebase_branch)

        try:
            if restore_to_branch:
                logger.debug(f"restoring to branch: {restore_to_branch}")
                repo.git.checkout(restore_to_branch)
            else:
                logger.debug(f"restoring to commit: {restore_to_commit.hexsha}")
                repo.git.checkout(restore_to_commit)
        except git.exc.GitCommandError:
            logger.exception("git command failed during reversion cleanup")

        with suppress(git.exc.GitCommandError):
            logger.debug(f"deleting temporary rebase branch: {temporary_rebase_branch}")
            if any(branch.name == temporary_rebase_branch for branch in repo.branches):  # type: ignore[attr-defined]
                repo.git.branch("-D", temporary_rebase_branch)

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
        minimized_hunks = dd_minimize(to_minimize, tester, time_limit=self.project.time_left)
        minimized = Diff.from_file_hunks(minimized_hunks)

        # we have the slice of the undone commit we need, now we need it to
        # apply to the program at its _current_ commit.  We:
        # (1) branch at the triggering commit,
        # (2) apply the change (using patch, not git.apply, because the former works
        # and the latter often doesn't for some reason),
        # (3) rebase the change on top of the main branch, and then
        # (4) getting the last commit as a diff.
        head_is_detached = repo.head.is_detached
        restore_to_commit = repo.head.commit
        restore_to_branch: str | None = None

        if head_is_detached:
            logger.warning("head is detached; will rebase on the detached commit")
        if not head_is_detached:
            restore_to_branch = repo.active_branch.name
            logger.info(f"head is not detached; will rebase on the active branch: {restore_to_branch}")

        # branch from the triggering commit...
        commit_sha = triggering_commit.hexsha
        temporary_rebase_branch = f"REPAIRCHAIN-rebase-{commit_sha[:8]}"
        self._cleanup(
            repo=repo,
            restore_to_commit=restore_to_commit,
            restore_to_branch=restore_to_branch,
            temporary_rebase_branch=temporary_rebase_branch,
        )

        try:
            repo_path = Path.resolve(self.project.local_repository_path)
            repo.git.branch(temporary_rebase_branch, triggering_commit)
            repo.git.checkout(temporary_rebase_branch)

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
                    str(temp_patch_path),
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

            if head_is_detached:
                repo.git.rebase(restore_to_commit)
            else:
                repo.git.rebase(restore_to_branch)

            # grab the head commit, which should undo the badness, turn that into a diff
            return commit_to_diff(self.project.repository.active_branch.commit)

        except subprocess.CalledProcessError:
            logger.exception("failed to apply patch")
        except git.exc.GitCommandError:
            logger.exception("failed to create branch or rebase")
        finally:
            self._cleanup(
                repo=repo,
                restore_to_commit=restore_to_commit,
                restore_to_branch=restore_to_branch,
                temporary_rebase_branch=temporary_rebase_branch,
            )

        return None

    def run(self) -> list[Diff]:
        minimal_diff = self._find_minimal_diff()
        return [minimal_diff] if minimal_diff else []
