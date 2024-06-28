from __future__ import annotations
from abc import ABC, abstractmethod

import typing as t

from repairchain.actions.validate import validate
from repairchain.models.diff import Diff
from repairchain.models.patch_outcome import PatchOutcome

if t.TYPE_CHECKING:

    from sourcelocation import FileHunk

    from repairchain.models.project import Project


class DiffMinimizer(ABC):

    triggering_diff: Diff
    hunks: list[FileHunk]
    project: Project

    def __init__(self, project: Project, triggering_diff: Diff) -> DiffMinimizer.t:
        self.triggering_diff = triggering_diff
        self.project = project
        self.hunks = list(self.triggering_diff.file_hunks)

    @staticmethod
    def split(c: frozenset[int], n: int) -> list[list[int]]:
        subsets = []
        start = 0
        for i in range(n):
            subset = c[start:start + (len(c) - start) // (n - i)]
            if len(subset) > 0:
                subsets.append(frozenset(subset))
            start += len(subset)
        return subsets

    def _patch_to_real_diff(self, patch: frozenset[int]) -> Diff:
        filehunks = [self.hunks[index] for index in patch]
        return Diff.from_file_hunks(filehunks)

    @abstractmethod
    def test(self, patch: frozenset[int]) -> PatchOutcome:
        pass

    def _test_with_cache(self, cache: dict[list[int], PatchOutcome], subset: list[int]) -> PatchOutcome:
        if subset in cache:
            return cache[subset]
        outcome = self.test(subset)
        cache[subset] = outcome
        return outcome

    def minimize_diff(self) -> Diff:
        test_cache = {}
        hunks = list(self.triggering_diff.file_hunks)
        c_fail = frozenset(range(len(hunks)))

        assert self._test_with_cache(test_cache, c_fail) == PatchOutcome.FAILED

        granularity = 2

    # Main loop
        while granularity >= 1:
            subsets = DiffMinimizer.split(list(c_fail), granularity)
            reduced = False
            for subset in subsets:
                complement = c_fail - frozenset(subset)

                if self._test_with_cache(test_cache, complement) == PatchOutcome.FAILED:
                    c_fail = complement
                    granularity = max(granularity - 1, 2)
                    reduced = True
            if not reduced and granularity >= len(c_fail):
                return c_fail
            granularity = min(granularity * 2, len(c_fail))
        return c_fail


class SimpleTestDiffMinimizer(DiffMinimizer):

    def test(self, patch: frozenset[int]) -> PatchOutcome:
        if (3 in patch and 0 in patch):  # noqa: PLR2004
            return PatchOutcome.FAILED
        return PatchOutcome.PASSED


class TestForFailure(DiffMinimizer):

    def test(self, patch: frozenset[int]) -> PatchOutcome:
        asdiff = self._patch_to_real_diff(patch)
        validated = validate(self.project, [asdiff], stop_early=True)
        return len(validated) > 0


class TestForSuccess(DiffMinimizer):

    def test(self, patch: frozenset[int]) -> PatchOutcome:
        asdiff = self._patch_to_real_diff(patch)
        validated = validate(self.project, [asdiff], stop_early=True)
        return len(validated) == 0
