from __future__ import annotations

import enum
import typing as t
from dataclasses import dataclass

import git

from repairchain.models.sanitizer_report import SanitizerReport

if t.TYPE_CHECKING:
    from pathlib import Path


class ProjectKind(str, enum.Enum):
    C = "c"
    KERNEL = "kernel"
    JAVA = "java"


@dataclass
class Project:
    kind: ProjectKind
    image: str
    repository: git.Repo
    head: git.Commit
    triggering_commit: git.Commit
    regression_test_command: str
    crash_command: str
    sanitizer_report: SanitizerReport

    @classmethod
    def build(
        cls,
        kind: str,
        image: str,
        repository_path: Path,
        triggering_commit_sha: str,
        regression_test_command: str,
        crash_command: str,
    ) -> t.Self:
        project_kind = ProjectKind(kind)
        repository = git.Repo(repository_path)
        head = repository.head.commit
        commit = repository.commit(triggering_commit_sha)
        sanitizer_report = SanitizerReport(sanitizer="ASAN")  # FIXME: placeholder
        return cls(
            kind=project_kind,
            image=image,
            repository=repository,
            head=head,
            triggering_commit=commit,
            regression_test_command=regression_test_command,
            crash_command=crash_command,
            sanitizer_report=sanitizer_report,
        )
