from __future__ import annotations

import typing as t

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.models.patch_outcome import PatchOutcome

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff


def split(c: frozenset[int], n: int) -> list[list[int]]:
    subsets = []
    start = 0
    for i in range(n):
        subset = c[start:start + (len(c) - start) // (n - i)]
        if len(subset) > 0:
            subsets.append(frozenset(subset))
        start += len(subset)
    return subsets


# this is just for testing; need to connect to actual validation.
def test(patch: set) -> PatchOutcome:
    if (3 in patch and 0 in patch):  # noqa: PLR2004
        return PatchOutcome.FAILED
    return PatchOutcome.PASSED


def test_with_cache(cache: dict[list[int], PatchOutcome], subset: list[int]) -> PatchOutcome:
    if subset in cache:
        return cache[subset]
    outcome = test(subset)
    cache[subset] = outcome
    return outcome


def minimize_diff(
    repo: git.Repo,
    triggering_commit: git.Commit,
) -> Diff:
    triggering_diff = commit_to_diff(triggering_commit)

    test_cache = {}
    hunks = list(triggering_diff.file_hunks)
    c_fail = frozenset(range(len(hunks)))

    assert test_with_cache(test_cache, c_fail) == PatchOutcome.FAILED

    granularity = 2
    # Main loop
    while granularity >= 1:
        subsets = split(list(c_fail), granularity)
        reduced = False
        for subset in subsets:
            complement = c_fail - frozenset(subset)

            if test_with_cache(test_cache, complement) == PatchOutcome.FAILED:
                c_fail = complement
                granularity = max(granularity - 1, 2)
                reduced = True
        if not reduced:
            if granularity >= len(c_fail):
                return c_fail
            granularity = min(granularity * 2, len(c_fail))
    return c_fail
