from __future__ import annotations

__all__ = (
    "commit_to_diff",
    "commit_to_files",
    "get_commit",
)

import difflib
import typing as t

from repairchain.models.diff import Diff, FileDiff

if t.TYPE_CHECKING:
    import git


def get_commit(repo: git.Repo, commit_hash: str) -> git.Commit:
    # Get the commit object
    return repo.commit(commit_hash)


def commit_to_diff(commit: git.Commit) -> Diff:
    """Obtains a diff for a given commit."""
    # NOTE assumption that this wasn't triggered by a merge commit (revisit and relax?)
    diff_index = commit.parents[0].diff(commit) if commit.parents else None
    assert diff_index is not None

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
            fromfile=diff.a_path or "/dev/null",
            tofile=diff.b_path or "/dev/null",
            lineterm="",
        ))
        file_diff = FileDiff.read_next(unified_diff_lines)
        file_diffs.append(file_diff)

    return Diff(file_diffs=file_diffs)


def get_file_contents_at_commit(commit: git.Commit, file_path: str) -> str:
    """Obtains the contents of a file at a specific commit."""
    blob = commit.tree / file_path
    content: str = blob.data_stream.read().decode("utf-8")
    return content


def commit_to_files(commit: git.Commit, diff: Diff) -> dict[str, str]:
    files = diff.files
    files_output: dict[str, str] = {}
    for f in files:
        files_output[f] = get_file_contents_at_commit(commit, f)
    return files_output
