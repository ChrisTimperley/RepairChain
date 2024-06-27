from __future__ import annotations

import typing as t
from abc import ABC, abstractmethod

from repairchain.actions.validate import validate
from repairchain.models.diff import Diff
from repairchain.models.patch_outcome import PatchOutcome

if t.TYPE_CHECKING:

    from sourcelocation import FileHunk

    from repairchain.models.project import Project


def split(c: list[int], n: int) -> list[frozenset[int]]:
    """Utility function to split a list of integers into specified number of
    sublists of approximately equal size, as sets.

    Parameters
    ----------
    c : list[int]
      List to split
    n : int
       Number of desired sublists

    Returns
    -------
    list[frozenset[int]]
       c split into n subsets of approximately equal size
    """  # noqa: D205
    subsets = []
    start = 0
    for i in range(n):
        subset = c[start:start + (len(c) - start) // (n - i)]
        if len(subset) > 0:
            subsets.append(frozenset(subset))
        start += len(subset)
    return subsets


class DiffMinimizer(ABC):

    triggering_diff: Diff
    hunks: list[FileHunk]
    project: Project

    def __init__(self, project: Project, triggering_diff: Diff) -> None:
        self.triggering_diff = triggering_diff
        self.project = project
        self.hunks = list(self.triggering_diff.file_hunks)

    def _patch_to_real_diff(self, patch: frozenset[int]) -> Diff:
        filehunks = [self.hunks[index] for index in patch]
        return Diff.from_file_hunks(filehunks)

    @abstractmethod
    def _test(self, patch: frozenset[int]) -> PatchOutcome:
        pass

    def _test_with_cache(self, cache: dict[frozenset[int], PatchOutcome], subset: frozenset[int]) -> PatchOutcome:
        if subset in cache:
            return cache[subset]
        outcome = self._test(subset)
        cache[subset] = outcome
        return outcome

    def minimize_diff(self) -> Diff:
        test_cache: dict[frozenset[int], PatchOutcome] = {}
        c_fail = frozenset(range(len(self.hunks)))

#  FIXME: check, not sure this makes sense with alternative strategies
#        assert self._test_with_cache(test_cache, c_fail) == PatchOutcome.FAILED

        granularity = 2

        # Main loop
        while granularity >= 1:
            subsets = split(list(c_fail), granularity)
            reduced = False
            for subset in subsets:
                complement = c_fail - frozenset(subset)

                if self._test_with_cache(test_cache, complement) == PatchOutcome.FAILED:
                    c_fail = complement
                    granularity = max(granularity - 1, 2)
                    reduced = True
            if not reduced and granularity >= len(c_fail):
                return self._patch_to_real_diff(c_fail)
            granularity = min(granularity * 2, len(c_fail))
        return self._patch_to_real_diff(c_fail)


class MinimizeForFailure(DiffMinimizer):
    """Strategy to find a minimal diff subset that leads to failure."""

    def _test(self, patch: frozenset[int]) -> PatchOutcome:
        asdiff = self._patch_to_real_diff(patch)
        validated = validate(self.project, [asdiff], stop_early=True)
        return PatchOutcome.PASSED if len(validated) > 0 else PatchOutcome.FAILED


class MinimizeForSuccess(DiffMinimizer):
    """Strategy to find a minimal diff subset required for success."""

    def _test(self, patch: frozenset[int]) -> PatchOutcome:
        asdiff = self._patch_to_real_diff(patch)
        validated = validate(self.project, [asdiff], stop_early=True)
        return PatchOutcome.PASSED if len(validated) == 0 else PatchOutcome.FAILED


class SimpleTestDiffMinimizerSuccess(DiffMinimizer):
    """Minimizer that exists strictly to test delta debugging implementation."""

    def _test(self, patch: frozenset[int]) -> PatchOutcome:
        if (3 in patch and 0 in patch):  # noqa: PLR2004
            return PatchOutcome.FAILED
        return PatchOutcome.PASSED


class SimpleTestDiffMinimizerFail(DiffMinimizer):
    """Minimizer that exists strictly to test delta debugging implementation."""

    def __init__(self, triggering_diff: Diff) -> None:
        self.triggering_diff = triggering_diff
        self.hunks = list(self.triggering_diff.file_hunks)

    """
    Strictly for testing, for test outcome observability.
    """
    def assert_pass(self, minimized: Diff) -> bool:
        aslst = list(minimized.file_hunks)
        return len(aslst) == 2 and self.hunks.index(aslst[0]) == 0 and self.hunks.index(aslst[1]) == 3  # noqa: PLR2004

    """
    Hardcodes silly expectation that the minimal patch includes the 0th and 3rd element.
    """
    def _test(self, patch: frozenset[int]) -> PatchOutcome:
        if (3 in patch and 0 in patch):  # noqa: PLR2004
            return PatchOutcome.FAILED
        return PatchOutcome.PASSED
