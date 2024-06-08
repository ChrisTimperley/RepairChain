from __future__ import annotations

__all__ = ("commit_to_diff",)

import difflib
import typing as t

from repairchain.models.diff import Diff, FileDiff

if t.TYPE_CHECKING:
    import git


def commit_to_diff(commit: git.Commit) -> Diff:
    """Obtains a diff for a given commit."""
    # NOTE assumption that this wasn't triggered by a merge commit (revisit and relax?)
    diff_index = commit.diff(commit.parents[0])

    file_diffs: list[FileDiff] = []

    for diff in diff_index:
        a_data: list[str]
        b_data: list[str]

        if diff.a_blob and diff.b_blob:
            a_data = diff.a_blob.data_stream.read().decode("utf-8").splitlines()
            b_data = diff.b_blob.data_stream.read().decode("utf-8").splitlines()
        elif diff.a_blob:
            a_data = diff.a_blob.data_stream.read().decode("utf-8").splitlines()
            b_data = []
        elif diff.b_blob:
            a_data = []
            b_data = diff.b_blob.data_stream.read().decode("utf-8").splitlines()
        else:
            continue

        unified_diff_lines = list(difflib.unified_diff(
            a_data,
            b_data,
            fromfile=diff.a_path if diff.a_path else "/dev/null",
            tofile=diff.b_path if diff.b_path else "/dev/null",
            lineterm="",
        ))
        file_diff = FileDiff.read_next(unified_diff_lines)
        file_diffs.append(file_diff)

    return Diff(file_diffs=file_diffs)
