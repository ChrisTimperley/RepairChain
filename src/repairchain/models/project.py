from __future__ import annotations

import enum
import typing as t
from dataclasses import dataclass

import git

if t.TYPE_CHECKING:
    from pathlib import Path


class ProjectKind(str, enum.Enum):
    C = "c"
    KERNEL = "kernel"
    JAVA = "java"


@dataclass
class Project:
    kind: ProjectKind
    repository: git.Repo
    triggering_commit: git.Commit

    @classmethod
    def build(
        cls,
        kind: str,
        repository_path: Path,
        triggering_commit_sha: str,
    ) -> t.Self:
        project_kind = ProjectKind(kind)
        repository = git.Repo(repository_path)
        commit = repository.commit(triggering_commit_sha)
        return cls(
            kind=project_kind,
            repository=repository,
            triggering_commit=commit,
        )
