from __future__ import annotations

__all__ = ("validate", "validate_patch")

import abc
import typing as t
from dataclasses import dataclass

from loguru import logger
from overrides import overrides

from repairchain.errors import BuildFailure
from repairchain.models.patch_outcome import PatchOutcome

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


class PatchValidator(abc.ABC):
    """Validates patches against a specific project version."""
    project: Project
    commit: git.Commit | None

    # TODO allow a container to be optionally provided?
    # that would allow for container recycling
    def validate(self, candidate: Diff) -> PatchOutcome:
        """Validates a single patch and returns the outcome."""
        logger.info(f"validating patch: {candidate}")
        try:
            with self.project.provision(
                version=self.commit,
                diff=candidate,
            ) as container:
                if not container.run_pov():
                    return PatchOutcome.FAILED

                if not container.run_regression_tests():
                    return PatchOutcome.FAILED

                return PatchOutcome.PASSED

        except BuildFailure:
            return PatchOutcome.FAILED_TO_BUILD

    @abc.abstractmethod
    def run(
        self,
        candidates: list[Diff],
        *,
        stop_early: bool = True,
    ) -> t.Iterator[Diff]:
        """Validates a list of patches and yields the valid ones.

        Arguments:
        ---------
        candidates : list[Diff]
            The list of patches to validate.
        stop_early : bool
            Whether to stop the validation process as soon as a valid patch is found.

        Yields:
        ------
        Diff
            A valid patch.
        """
        raise NotImplementedError


@dataclass
class SimplePatchValidator(PatchValidator):
    project: Project
    commit: git.Commit | None

    @classmethod
    def build(
        cls,
        project: Project,
        commit: git.Commit | None = None,
    ) -> SimplePatchValidator:
        return cls(project, commit)

    @overrides
    def run(
        self,
        candidates: list[Diff],
        *,
        stop_early: bool = True,
    ) -> t.Iterator[Diff]:
        for candidate in candidates:
            outcome = self.validate(candidate)
            if outcome == PatchOutcome.PASSED:
                yield candidate
                if stop_early:
                    break


@dataclass
class ThreadedPatchValidator(PatchValidator):
    project: Project
    commit: git.Commit | None
    workers: int

    @classmethod
    def build(
        cls,
        project: Project,
        commit: git.Commit | None = None,
        *,
        workers: int = 1,
    ) -> ThreadedPatchValidator:
        return cls(
            project=project,
            commit=commit,
            workers=workers,
        )

    @overrides
    def run(
        self,
        candidates: list[Diff],
        *,
        stop_early: bool = True,
    ) -> t.Iterator[Diff]:
        # executor = concurrent.futures.ThreadPoolExecutor()
        raise NotImplementedError


def validate_patch(
    project: Project,
    diff: Diff,
    *,
    commit: git.Commit | None = None,
) -> PatchOutcome:
    """Applies a given patch to a specific version of a project and returns the outcome."""
    validator = SimplePatchValidator.build(project, commit)
    return validator.validate(diff)


def validate(
    project: Project,
    candidates: list[Diff],
    *,
    commit: git.Commit | None = None,
    stop_early: bool = False,
) -> list[Diff]:
    """Validates the generated patches and returns a list of valid patches.

    If `stop_early` is True, the validation process will stop as soon as a valid patch is found.
    """
    validator = SimplePatchValidator.build(project, commit)
    return list(validator.run(candidates, stop_early=stop_early))
