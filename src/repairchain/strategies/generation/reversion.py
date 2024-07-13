from __future__ import annotations

import contextlib
import enum
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


class ConflictStrategy(enum.StrEnum):
    ours = "ours"
    theirs = "theirs"


@dataclass
class MinimalPatchReversion(PatchGenerationStrategy):
    diagnosis: Diagnosis
    project: Project

    @classmethod
    def applies(cls, diagnosis: Diagnosis) -> bool:  # noqa: ARG003
        return True

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> MinimalPatchReversion:
        return cls(diagnosis=diagnosis, project=diagnosis.project)

    @property
    def triggering_commit(self) -> git.Commit:
        return self.project.triggering_commit

    @property
    def triggering_commit_parent(self) -> git.Commit:
        return self.triggering_commit.parents[0]

    def _cleanup(self, restore_to: str) -> None:
        """Restores the initial state of the Git repo prior to running this strategy."""
        repo = self.project.repository
        temporary_rebase_branch = self.temporary_rebase_branch
        with suppress(git.exc.GitCommandError):
            repo.git.rebase("--abort")
        with suppress(git.exc.GitCommandError):
            repo.git.merge("--abort")
        with suppress(git.exc.GitCommandError):
            repo.git.clean("-xdf")
        with suppress(git.exc.GitCommandError):
            if not repo.head.is_detached and repo.active_branch.name == restore_to:
                repo.git.branch("-D", temporary_rebase_branch)

        try:
            logger.debug(f"restoring to: {restore_to}")
            repo.git.checkout(restore_to)
        except git.exc.GitCommandError:
            logger.exception(f"failed to restore git repo to: {restore_to}")

        with suppress(git.exc.GitCommandError):
            logger.debug(f"deleting temporary rebase branch: {temporary_rebase_branch}")
            if any(branch.name == temporary_rebase_branch for branch in repo.branches):  # type: ignore[attr-defined]
                repo.git.branch("-D", temporary_rebase_branch)

    def _compute_reverse_diff(self) -> Diff:
        """Computes a diff that reverses the changes introduced by the triggering commit."""
        unidiff = self.project.repository.git.diff(
            self.triggering_commit,
            self.triggering_commit_parent,
            unified=True,
        )
        return Diff.from_unidiff(unidiff).strip(1)

    def _minimize_reverse_diff(self, reverse_diff: Diff) -> Diff:
        """Minimizes the reverse diff to the smallest possible diff that still undoes the triggering commit."""
        num_hunks = len(list(reverse_diff.file_hunks))
        if num_hunks == 1:
            logger.warning("only one hunk in reverse diff; skipping minimization")
            return reverse_diff

        workers = self.project.settings.workers
        logger.debug(f"using {workers} workers for build/regression steps during minimization")

        def tester(hunks: t.Sequence[FileHunk]) -> bool:
            as_diff = Diff.from_file_hunks(list(hunks))
            outcome = self.project.validator.validate(
                candidate=as_diff,
                commit=self.triggering_commit,
                workers=workers,
            )
            return outcome == PatchOutcome.PASSED

        to_minimize = list(reverse_diff.file_hunks)
        minimized_hunks = dd_minimize(to_minimize, tester, time_limit=self.project.time_left)
        return Diff.from_file_hunks(minimized_hunks)

    @contextlib.contextmanager
    def _write_diff_to_file(self, diff: Diff) -> t.Iterator[Path]:
        """Writes the given diff to a temporary file and yields the path to that file."""
        temp_patch_path = Path(tempfile.mkstemp(suffix=".diff")[1])
        contents = str(diff)
        try:
            with temp_patch_path.open("w", encoding="utf-8") as temp_patch_file:
                temp_patch_file.write(contents)
            yield temp_patch_path
        finally:
            temp_patch_path.unlink()

    def _apply_patch(self, patch: Diff) -> None:
        # make a commit consisting of only the minimized undo
        repo_path = Path.resolve(self.project.local_repository_path)
        with self._write_diff_to_file(patch) as temp_patch_path:
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

    @property
    def temporary_rebase_branch(self) -> str:
        commit_sha = self.triggering_commit.hexsha
        return f"REPAIRCHAIN-rebase-{commit_sha[:8]}"

    @contextlib.contextmanager
    def reset_repo_after(self, restore_to: str) -> t.Iterator[None]:
        try:
            yield
        finally:
            self._cleanup(restore_to)

    def _rebase_patch_onto_head(
        self,
        minimal_changes: Diff,
        rebase_onto: str,
        conflict_strategy: ConflictStrategy | None = None,
    ) -> Diff | None:
        """Transforms a commit that transforms the minimal reversion diff into one that applies to HEAD."""
        repo = self.project.repository
        triggering_commit = self.project.triggering_commit

        try:
            repo.git.branch(self.temporary_rebase_branch, triggering_commit)
            repo.git.checkout(self.temporary_rebase_branch)
            self._apply_patch(minimal_changes)
        except subprocess.CalledProcessError:
            logger.exception("failed to apply minimal changes")
            return None

        repo.git.add(update=True)
        repo.index.commit("undo minimal changes")

        match conflict_strategy:
            case ConflictStrategy.ours | ConflictStrategy.theirs:
                command = ["git", "rebase", "-s", "recursive", "-X", conflict_strategy.value, rebase_onto]
                try:
                    repo.git.execute(command)
                except git.exc.GitCommandError as e:
                    logger.error(f"failed to rebase minimal changes ({conflict_strategy} conflict strategy): {e}")
                    return None

            case None:
                try:
                    repo.git.rebase(rebase_onto)
                except git.exc.GitCommandError as e:
                    logger.error(f"failed to rebase minimal changes (no conflict strategy): {e}")
                    return None

        # transform the rebased reversion commit into a diff
        return commit_to_diff(self.project.repository.active_branch.commit)

    def run(self) -> list[Diff]:
        repo = self.project.repository
        reverse_diff = self._compute_reverse_diff()
        reverse_diff = self._minimize_reverse_diff(reverse_diff)

        # we have the slice of the undone commit we need, now we need it to
        # apply to the program at its _current_ commit.  We:
        # (1) branch at the triggering commit,
        # (2) apply the change  via patch
        # (3) rebase the change on top of the main branch or HEAD commit, and then
        # (4) getting the last commit as a diff
        restore_to: str
        if repo.head.is_detached:
            logger.warning("head is detached; will rebase on the detached commit")
            restore_to = repo.head.commit.hexsha
        else:
            restore_to = repo.active_branch.name
            logger.info(f"head is not detached; will rebase on the active branch: {restore_to}")

        self._cleanup(restore_to)

        with (
            suppress(subprocess.CalledProcessError, git.exc.GitCommandError),
            self.reset_repo_after(restore_to),
        ):
            patch_with_no_conflict_strategy = self._rebase_patch_onto_head(reverse_diff, restore_to)
            if patch_with_no_conflict_strategy:
                return [patch_with_no_conflict_strategy]

        # try again with different conflict strategies
        patches: list[Diff] = []

        with (
            suppress(subprocess.CalledProcessError, git.exc.GitCommandError),
            self.reset_repo_after(restore_to),
        ):
            diff_with_ours = self._rebase_patch_onto_head(
                reverse_diff,
                restore_to,
                conflict_strategy=ConflictStrategy.ours,
            )
            if diff_with_ours:
                patches.append(diff_with_ours)

        with (
            suppress(subprocess.CalledProcessError, git.exc.GitCommandError),
            self.reset_repo_after(restore_to),
        ):
            diff_with_theirs = self._rebase_patch_onto_head(
                reverse_diff,
                restore_to,
                conflict_strategy=ConflictStrategy.theirs,
            )
            if diff_with_theirs:
                patches.append(diff_with_theirs)

        return patches
