from __future__ import annotations

import typing as t

from repairchain.actions.commit_to_diff import commit_to_diff

if t.TYPE_CHECKING:
    import git


def minimize_diff(
    repo: git.Repo,
    triggering_commit: git.Commit,
) -> None:
    triggering_diff = commit_to_diff(triggering_commit)

    # - turn on/off hunks
    # - what is fewest number of hunks that still trigger the bug?
    #   - is this sound?
    # - do delta debugging on a bitvector
    # - transform bitvector into a Diff using Diff.from_file_hunks
    hunks = list(triggering_diff.file_hunks)
    _num_hunks = len(hunks)

    raise NotImplementedError
