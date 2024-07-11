from __future__ import annotations

__all__ = (
    "PatchValidator",
    "SimplePatchValidator",
    "ThreadedPatchValidator",
    "validate",
)

import abc
import concurrent.futures
import math
import typing as t
from dataclasses import dataclass, field

from dockerblade.stopwatch import Stopwatch
from loguru import logger
from overrides import overrides

from repairchain.errors import BuildFailure
from repairchain.models.patch_outcome import (
    PatchOutcome,
    PatchOutcomeCache,
)

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


class PatchValidator(abc.ABC):
    """Validates patches against a specific project version."""
    project: Project
    cache: PatchOutcomeCache

    def _validate(
        self,
        candidate: Diff,
        commit: git.Commit,
    ) -> PatchOutcome:
        try:
            with self.project.provision(
                version=commit,
                diff=candidate,
            ) as container:
                if not container.run_pov():
                    return PatchOutcome.FAILED

                if not container.run_regression_tests():
                    return PatchOutcome.FAILED

                return PatchOutcome.PASSED

        except BuildFailure:
            return PatchOutcome.FAILED_TO_BUILD

    def validate(
        self,
        candidate: Diff,
        commit: git.Commit | None,
    ) -> PatchOutcome:
        """Validates a single patch and returns the outcome."""
        if commit is None:
            commit = self.project.head
        logger.info(f"validating patch (applied to {commit}):\n{candidate}")

        outcome = self.cache.fetch(commit, candidate)
        if outcome is not None:
            logger.debug(f"cache hit: {outcome}")
            return outcome

        outcome = self._validate(candidate, commit)
        self.cache.store(commit, candidate, outcome)
        return outcome

    @abc.abstractmethod
    def run(
        self,
        candidates: list[Diff],
        *,
        commit: git.Commit | None = None,
        timeout: int | None = None,
        stop_early: bool = True,
    ) -> t.Iterator[tuple[Diff, PatchOutcome]]:
        """Validates a list of patches and yields their outcomes.

        Arguments:
        ---------
        candidates : list[Diff]
            The list of patches to validate.
        stop_early : bool
            Whether to stop the validation process as soon as a valid patch is found.
        timeout : int | None
            The maximum amount of time to spend validating (in seconds).
            If None, no timeout is set.
        commit: git.Commit | None
            The commit to which the patches should be applied.
            If None, the project's head commit is used.

        Yields:
        ------
        tuple[Diff, PatchOutcome]
            A tuple containing the patch and its outcome.

        Raises:
        ------
        TimeoutError
            If the validation process exceeds the specified timeout.
        """
        raise NotImplementedError


@dataclass
class SimplePatchValidator(PatchValidator):
    project: Project
    cache: PatchOutcomeCache

    @overrides
    def run(
        self,
        candidates: list[Diff],
        *,
        commit: git.Commit | None = None,
        timeout: int | None = None,
        stop_early: bool = True,
    ) -> t.Iterator[tuple[Diff, PatchOutcome]]:
        timer = Stopwatch()
        timer.start()

        for candidate in candidates:
            if timeout is not None and timer.duration >= timeout:
                message = f"validation process exceeded the specified timeout ({timeout}s)"
                raise TimeoutError(message)

            outcome = self.validate(candidate, commit)
            yield candidate, outcome
            if outcome == PatchOutcome.PASSED and stop_early:
                break


@dataclass
class ThreadedPatchValidator(PatchValidator):
    project: Project
    cache: PatchOutcomeCache
    workers: int = field(default=1)

    @classmethod
    def for_project(cls, project: Project) -> ThreadedPatchValidator:
        return cls(
            cache=project.evaluation_cache,
            project=project,
            workers=project.settings.workers,
        )

    @overrides
    def run(
        self,
        candidates: list[Diff],
        *,
        commit: git.Commit | None = None,
        timeout: int | None = None,
        stop_early: bool = True,
    ) -> t.Iterator[tuple[Diff, PatchOutcome]]:
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.workers,
        )

        future_to_candidate: dict[concurrent.futures.Future[PatchOutcome], Diff] = {}
        for candidate in candidates:
            future = executor.submit(self.validate, candidate, commit)
            future_to_candidate[future] = candidate

        try:
            for future in concurrent.futures.as_completed(
                future_to_candidate.keys(),
                timeout=timeout,
            ):
                candidate = future_to_candidate[future]
                outcome = future.result()
                yield candidate, outcome
                if outcome == PatchOutcome.PASSED and stop_early:
                    break
        finally:
            executor.shutdown(cancel_futures=True)


def validate(
    project: Project,
    candidates: list[Diff],
    *,
    commit: git.Commit | None = None,
    stop_early: bool = False,
) -> t.Iterator[Diff]:
    """Validates the generated patches and returns a list of valid patches.

    If `stop_early` is True, the validation process will stop as soon as a valid patch is found.
    """
    validator = project.validator
    time_left = math.floor(project.time_left)
    for candidate, outcome in validator.run(
        candidates,
        commit=commit,
        stop_early=stop_early,
        timeout=int(time_left),
    ):
        if outcome == PatchOutcome.PASSED:
            yield candidate
            if stop_early:
                break
