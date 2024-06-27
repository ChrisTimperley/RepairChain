from __future__ import annotations

import typing as t

from repairchain.models.patch_outcome import PatchOutcome
from repairchain.actions.commit_to_diff import commit_to_diff

if t.TYPE_CHECKING:
    import git

from repairchain.models.diff import Diff

def test(patch : set) -> PatchOutcome:
    if (3 in patch and 0 in patch): 
        return PatchOutcome.FAILED
    return PatchOutcome.PASSED

def split(elems, n):
    assert 1 <= n <= len(elems)

    k, m = divmod(len(elems), n)
    try:
        subsets = list(elems[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
                       for i in range(n))
    except TypeError:
        # Convert to list and back
        subsets = list(type(elems)(
                    list(elems)[i * k + min(i, m):(i + 1) * k + min(i + 1, m)])
                       for i in range(n))

    assert len(subsets) == n
    assert sum(len(subset) for subset in subsets) == len(elems)
    assert all(len(subset) > 0 for subset in subsets)

    return subsets


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
    c_pass = set([])
    c_fail = set(range(0,len(hunks)))
    granularity = 2
    offset = 0
    # Main loop
    while True:
        delta = c_fail - c_pass
        if len(delta) < granularity:
            return list(delta)

        deltas = split(delta, granularity)
        reduction_found = False
        j = 0

        while j < granularity:
            i = (j + offset) % granularity
            next_c_pass = c_pass | deltas[i]
            next_c_fail = c_fail - deltas[i]

            if granularity == 2 and test(next_c_pass) == PatchOutcome.PASSED:
                c_fail = next_c_pass
                offset = i  # was offset = 0 in original dd()
                reduction_found = True
                break
            elif test(next_c_fail) == PatchOutcome.FAILED:
                c_fail = next_c_fail
                n = max(granularity - 1, 2)
                offset = i
                reduction_found = True
                break
            else:
                j += 1  # choose next subset

        if not reduction_found:
            if granularity >= len(delta):
                return delta 

        granularity = min(granularity * 2, len(delta))
