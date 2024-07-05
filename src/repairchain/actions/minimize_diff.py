from __future__ import annotations

import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from loguru import logger
from overrides import overrides

from repairchain.actions.validate import (
    PatchValidator,
    SimplePatchValidator,
)
from repairchain.models.diff import Diff
from repairchain.models.patch_outcome import PatchOutcome
from repairchain.util import split

if t.TYPE_CHECKING:
    import git
    from sourcelocation import FileHunk

    from repairchain.models.project import Project


@dataclass
class DiffMinimizer(ABC):
    """Minimizes the hunks within a diff with respect to a criterion specified by the DiffMinizer subclass."""
    triggering_diff: Diff
    validator: PatchValidator
    hunks: list[FileHunk] = field(init=False)

    @classmethod
    def build(
        cls,
        triggering_diff: Diff,
        project: Project,
        commit: git.Commit | None = None,
    ) -> t.Self:
        validator = SimplePatchValidator(project, commit)
        return cls(
            triggering_diff=triggering_diff,
            validator=validator,
        )

    def __post_init__(self) -> None:
        self.hunks = list(self.triggering_diff.file_hunks)

    def _minimization_to_diff(self, minimization: frozenset[int]) -> Diff:
        as_hunks = [self.hunks[index] for index in minimization]
        return Diff.from_file_hunks(as_hunks)

    @abstractmethod
    def check_outcome(self, outcome: PatchOutcome) -> bool:
        """Determines whether a given minimization is valid based on the outcome of the test."""
        ...

    def test(self, minimization: frozenset[int]) -> bool:
        """Determines whether a given minimization satisfies the criterion of this minimizer."""
        logger.debug(f"testing minimization: {minimization}")
        as_hunks = [self.hunks[index] for index in minimization]
        as_diff = Diff.from_file_hunks(as_hunks)

        outcome = self.validator.validate(as_diff)
        if outcome == PatchOutcome.FAILED_TO_BUILD:
            logger.debug(f"minimization failed to build: {minimization}")
            return False

        logger.debug(f"minimization outcome: {outcome}")
        is_valid = self.check_outcome(outcome)
        if is_valid:
            logger.debug(f"minimization is valid: {minimization}")
        else:
            logger.debug(f"minimization is invalid: {minimization}")
        return is_valid

    def minimize(self) -> Diff:
        num_hunks = len(self.hunks)
        logger.debug(f"minimizing diff with {num_hunks} hunks")
        c_fail = frozenset(range(num_hunks))

        # FIXME this should probably be higher?
        granularity = 2
        while granularity >= 1:
            subsets = split(list(c_fail), granularity)
            reduced = False
            for subset in subsets:
                complement = c_fail - frozenset(subset)

                # is this a valid subset?
                if not self.test(complement):
                    c_fail = complement
                    # FIXME granularity will never be lower than 2?
                    granularity = max(granularity - 1, 2)
                    reduced = True

            # this seems wrong?
            if not reduced and granularity >= len(c_fail):
                return self._minimization_to_diff(c_fail)

            granularity = min(granularity * 2, len(c_fail))

        return self._minimization_to_diff(c_fail)


class MinimizeForFailure(DiffMinimizer):
    """Strategy to find a minimal diff subset that leads to failure."""

    @overrides
    def check_outcome(self, outcome: PatchOutcome) -> bool:
        """Valid minimizations must fail the tests."""
        assert outcome != PatchOutcome.FAILED_TO_BUILD
        return outcome == PatchOutcome.FAILED


class MinimizeForSuccess(DiffMinimizer):
    """Strategy to find a minimal diff subset required for success."""

    @overrides
    def check_outcome(self, outcome: PatchOutcome) -> bool:
        """Valid minimizations must pass the tests."""
        assert outcome != PatchOutcome.FAILED_TO_BUILD
        return outcome == PatchOutcome.PASSED
