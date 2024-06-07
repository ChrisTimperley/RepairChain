from __future__ import annotations

import typing as t

import git

if t.TYPE_CHECKING:
    from pathlib import Path


def minimize_changes(
    repo_path: Path,
    triggering_commit_hash: str,
) -> None:
    repo = git.Repo(repo_path)
    commit = repo.commit(triggering_commit_hash)
    # NOTE assumption that this wasn't triggered by a merge commit (revisit and relax?)
    triggering_diff_index = commit.diff(commit.parents[0])
    print(triggering_diff_index)

    # NOTE we probably want to ignore "rename" and "changed in the type" diffs
    # and restrict ourselves to "added", "deleted", and "modified" diffs

    # TODO steal Diff/Hunk data structure from Darjeeling
    raise NotImplementedError
