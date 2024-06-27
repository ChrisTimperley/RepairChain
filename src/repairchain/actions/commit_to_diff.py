from __future__ import annotations

from pathlib import Path

__all__ = ("commit_to_diff","clone_repository","get_commit","commit_to_files")

import difflib
import typing as t

import git

from repairchain.models.diff import Diff, FileDiff

# NOTE why is the import being done with this check?
if t.TYPE_CHECKING:
    import git

# NOTE we may want to clone the repository only once; can we use the /tmp directory?
# FIXME we may want to ensure that we have permissions to clone the repository and/or add key
def clone_repository(repo_url: str, clone_dir: str ="/tmp/repo") -> git.Repo:
     # Create a Path object from the clone_dir string
    clone_dir_path = Path(clone_dir)

    # Clone the repository if it doesn't exist
    if not clone_dir_path.exists():
        return git.Repo.clone_from(repo_url, clone_dir_path)

    return git.Repo(clone_dir_path)

def get_commit(repo: git.Repo, commit_hash: str) -> git.Commit:
    # Get the commit object
    return repo.commit(commit_hash)

def commit_to_diff(commit: git.Commit) -> Diff:
    """Obtains a diff for a given commit."""
    # NOTE assumption that this wasn't triggered by a merge commit (revisit and relax?)
    diff_index = commit.parents[0].diff(commit) if commit.parents else None

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

# Function to get file contents at a specific commit
def get_file_contents_at_commit(commit: git.Commit, file_path: str) -> str:
    # Get the blob object for the file
    blob = commit.tree / file_path

    # Read the contents of the file
    return blob.data_stream.read().decode("utf-8")

def commit_to_files(commit: git.Commit, diff: Diff) -> dict[str,str]:
    files = diff.files
    files_output: dict[str,str] = {}
    for f in files:
        files_output[f] = get_file_contents_at_commit(commit, f)
    return files_output

