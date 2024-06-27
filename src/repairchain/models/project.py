from __future__ import annotations

import enum
import json
import typing as t
from dataclasses import dataclass
from pathlib import Path

import git

from repairchain.models.sanitizer_report import SanitizerReport


class ProjectKind(enum.StrEnum):
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
    def load(cls, path: str | Path) -> t.Self:
        if isinstance(path, str):
            path = Path(path)
        with path.open("r") as file:
            dict_ = json.load(file)
        return cls.from_dict(dict_)

    @classmethod
    def from_dict(cls, dict_: dict[str, t.Any]) -> t.Self:
        kind = ProjectKind(dict_["project-kind"])
        image = dict_["image"]
        repository_path = Path(dict_["repository-path"])
        triggering_commit_sha = dict_["triggering-commit"]
        regression_test_command = dict_["regression-test-command"]
        crash_command = dict_["crash"]
        return cls.build(
            kind=kind,
            image=image,
            repository_path=repository_path,
            triggering_commit_sha=triggering_commit_sha,
            regression_test_command=regression_test_command,
            crash_command=crash_command,
        )

    @classmethod
    def build(
        cls,
        *,
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
