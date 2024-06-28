from __future__ import annotations

import typing as t

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.models.patch_outcome import PatchOutcome

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff


def split(c: set[int], n: int) -> list[list[int]]:
    subsets = []
    start = 0
    for i in range(n):
        subset = c[start:start + (len(c) - start) // (n - i)]
        if len(subset) > 0:
            subsets.append(set(subset))
        start += len(subset)
    return subsets


# this is just for testing; need to connect to actual validation.
def test(patch: set) -> PatchOutcome:
    if (3 in patch and 0 in patch):  # noqa: PLR2004
        return PatchOutcome.FAILED
    return PatchOutcome.PASSED


def minimize_diff(
    repo: git.Repo,
    triggering_commit: git.Commit,
) -> Diff:
    triggering_diff = commit_to_diff(triggering_commit)

    # - turn on/off hunks
    # - what is fewest number of hunks that still trigger the bug?
    #   - is this sound?
    # - do delta debugging on a bitvector
    # - transform bitvector into a Diff using Diff.from_file_hunks
    hunks = list(triggering_diff.file_hunks)
    c_fail = set(range(len(hunks)))

    assert test(c_fail) == PatchOutcome.FAILED

    granularity = 2
    # Main loop
    while granularity >= 1:
        subsets = split(list(c_fail), granularity)
        reduced = False
        for subset in subsets:
            complement = c_fail - set(subset)
            if test(complement) == PatchOutcome.FAILED:
                c_fail = complement
                granularity = max(granularity - 1, 2)
                reduced = True
        if not reduced:
            if granularity >= len(c_fail):
                return c_fail
            granularity = min(granularity * 2, len(c_fail))
    return c_fail
