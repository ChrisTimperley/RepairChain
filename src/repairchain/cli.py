from __future__ import annotations

from repairchain.actions import commit_to_diff
from repairchain.strategies.llms.context import create_context
from repairchain.strategies.llms.yolo import yolo


def cli(repo_url: str, commit_hash: str) -> None:
    repo = commit_to_diff.clone_repository(repo_url)
    commit = commit_to_diff.get_commit(repo, commit_hash)
    diff = commit_to_diff.commit_to_diff(commit)
    files = commit_to_diff.commit_to_files(commit, diff)
    prompt = create_context(files, diff)
    yolo(prompt)
