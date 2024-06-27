from __future__ import annotations

import typing as t

from repairchain.models.patch_outcome import PatchOutcome
from repairchain.actions.commit_to_diff import commit_to_diff

if t.TYPE_CHECKING:
    import git

from repairchain.models.diff import Diff


def split(c, n):
    subsets = []
    start = 0
    for i in range(n):
        subset = c[start:start + (len(c) - start) // (n - i)]
        if len(subset) > 0:
            subsets.append(set(subset))
        start = start + len(subset)
    return subsets


def test(patch : set) -> PatchOutcome:
    if (3 in patch or 0 in patch): 
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

    c_fail = set(range(0,len(hunks)))
    c_pass = set([])
    granularity = 2
    offset = 0 

    assert test(c_fail) == PatchOutcome.FAILED 

    # Main loop
    while True:
        delta = c_fail - c_pass
        if len(delta) < granularity:
            return c_fail
        deltas = split(list(delta), granularity)

        reduction_found = False
        j = 0

        while j < granularity:
            i = (j + offset) % granularity
            next_c_pass = c_pass | deltas[i]
            next_c_fail = c_fail - deltas[i]

            if granularity == 2 and test(next_c_pass) == PatchOutcome.FAILED:
                c_fail = next_c_pass
                offset = i  # was offset = 0 in original dd()
                reduction_found = True
                break
            elif test(next_c_fail) == PatchOutcome.FAILED:
                c_fail = next_c_fail
                granularity = max(granularity - 1, 2)
                offset = i
                reduction_found = True
                break
            else:
                j += 1  # choose next subset

        if not reduction_found:
            if granularity >= len(delta):
                return c_fail
            granularity = min(granularity * 2, len(delta))