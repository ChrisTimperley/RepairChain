from __future__ import annotations

import typing as t

from repairchain.actions.commit_to_diff import commit_to_diff

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff


def subset_from_bitvector(elements, bitvector):
    subset = []
    index = 0
    while bitvector > 0:
        if bitvector & 1:
            subset.append(elements[index])
        bitvector >>= 1
        index += 1
    return subset


def test(elements, bitvector):
    subset = subset_from_bitvector(elements, bitvector)
    # make some dummy test here so I can check that it's working
    raise NotImplemented
    
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
    _num_hunks = len(hunks)
    hunks_bitvec = (1 << _num_hunks) - 1

    n = _num_hunks    
    granularity = 1

    while granularity < n:
        progress = False
        subset = 0

        while subset < granularity:
            next_try = 0

            for i in range(n):
                if (i // (n // granularity)) % 2 == subset:
                    next_try |= (1 << i)

            next_try &= hunks_bitvec

            if next_try and not test(next_try):
                hunks_bitvec = next_try
                n = hunks_bitvec.bit_length()
                granularity = max(granularity - 1, 1)
                progress = True
                break

            subset += 1

        if not progress:
            granularity *= 2

    return subset_from_bitvector(hunks,hunks_bitvec)

