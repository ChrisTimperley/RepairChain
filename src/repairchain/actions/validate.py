from __future__ import annotations

__all__ = ("validate", "validate_patch")

import abc
import concurrent.futures
import typing as t
from dataclasses import dataclass, field

from dockerblade.stopwatch import Stopwatch
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
        logger.info(f"validating patch (applied to {self.commit}):\n{candidate}")
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
        timeout: int | None = None,
        stop_early: bool = True,
    ) -> t.Iterator[Diff]:
        """Validates a list of patches and yields the valid ones.

        Arguments:
        ---------
        candidates : list[Diff]
            The list of patches to validate.
        stop_early : bool
            Whether to stop the validation process as soon as a valid patch is found.
        timeout : int | None
            The maximum amount of time to spend validating (in seconds).
            If None, no timeout is set.

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

    @overrides
    def run(
        self,
        candidates: list[Diff],
        *,
        stop_early: bool = True,
        timeout: int | None = None,
    ) -> t.Iterator[Diff]:
        timer = Stopwatch()
        timer.start()

        for candidate in candidates:
            if timeout is not None and timer.duration >= timeout:
                return

            outcome = self.validate(candidate)
            if outcome == PatchOutcome.PASSED:
                yield candidate
                if stop_early:
                    break


@dataclass
class ThreadedPatchValidator(PatchValidator):
    project: Project
    commit: git.Commit | None
    workers: int = field(default=1)

    @overrides
    def run(
        self,
        candidates: list[Diff],
        *,
        timeout: int | None = None,
        stop_early: bool = True,
    ) -> t.Iterator[Diff]:
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.workers,
        )

        future_to_candidate: dict[concurrent.futures.Future[PatchOutcome], Diff] = {}
        for candidate in candidates:
            future = executor.submit(self.validate, candidate)
            future_to_candidate[future] = candidate

        for future in concurrent.futures.as_completed(
            future_to_candidate.keys(),
            timeout=timeout,
        ):
            candidate = future_to_candidate[future]
            outcome = future.result()
            if outcome == PatchOutcome.PASSED:
                yield candidate
                if stop_early:
                    break

        executor.shutdown(cancel_futures=True)


def validate_patch(
    project: Project,
    diff: Diff,
    *,
    commit: git.Commit | None = None,
) -> PatchOutcome:
    """Applies a given patch to a specific version of a project and returns the outcome."""
    validator = SimplePatchValidator(project, commit)
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
    workers = project.settings.workers
    validator = ThreadedPatchValidator(project, commit, workers=workers)
    return list(validator.run(candidates, stop_early=stop_early))
