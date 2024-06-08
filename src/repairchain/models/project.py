from __future__ import annotations

import typing as t
from dataclasses import dataclass

import git

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Project:
    repository: git.Repo
    triggering_commit: git.Commit

    @classmethod
    def build(
        cls,
        repository_path: Path,
        triggering_commit_sha: str,
    ) -> t.Self:
        repository = git.Repo(repository_path)
        commit = repository.commit(triggering_commit_sha)
        return cls(
            repository=repository,
            triggering_commit=commit,
        )
