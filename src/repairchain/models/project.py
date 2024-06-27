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
    build_command: str
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

        commands_dict = dict_["commands"]
        assert isinstance(commands_dict, dict)

        regression_test_command = commands_dict["regression-test"]
        crash_command = commands_dict["crash"]
        build_command = commands_dict["build"]

        sanitizer_report_path = Path(dict_["sanitizer-report-file"])

        return cls.build(
            build_command=build_command,
            crash_command=crash_command,
            image=image,
            kind=kind,
            regression_test_command=regression_test_command,
            repository_path=repository_path,
            sanitizer_report_path=sanitizer_report_path,
            triggering_commit_sha=triggering_commit_sha,
        )

    @classmethod
    def build(
        cls,
        *,
        kind: str,
        image: str,
        repository_path: Path,
        triggering_commit_sha: str,
        build_command: str,
        regression_test_command: str,
        crash_command: str,
        sanitizer_report_path: Path,
    ) -> t.Self:
        project_kind = ProjectKind(kind)
        repository = git.Repo(repository_path)
        head = repository.head.commit
        commit = repository.commit(triggering_commit_sha)
        sanitizer_report = SanitizerReport.load(sanitizer_report_path)
        return cls(
            build_command=build_command,
            crash_command=crash_command,
            head=head,
            image=image,
            kind=project_kind,
            regression_test_command=regression_test_command,
            repository=repository,
            sanitizer_report=sanitizer_report,
            triggering_commit=commit,
        )
