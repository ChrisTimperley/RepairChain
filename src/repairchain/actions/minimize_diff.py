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

    inputs = set(range(0,len(hunks)))
    granularity = 2

    assert test(inputs) == PatchOutcome.FAILED 

    while granularity >= 1:
        subsets = split(list(inputs), granularity)
        reduced = False

        for subset in subsets:
            complement = inputs.difference(set(subset))
            if test(complement) == PatchOutcome.FAILED:
                inputs = complement
                reduced = True
                break

        if not reduced:
            if granularity == 1:
                break  # Cannot reduce further, minimal failure-inducing input found
            granularity = max(granularity // 2, 1)
    
    return inputs