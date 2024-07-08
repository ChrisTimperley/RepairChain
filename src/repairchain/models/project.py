from __future__ import annotations

import contextlib
import enum
import json
import os
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import dockerblade
import git

from repairchain.actions.validate import (
    PatchValidator,
    ThreadedPatchValidator,
)
from repairchain.models.container import ProjectContainer
from repairchain.models.patch_outcome import PatchOutcomeCache
from repairchain.models.sanitizer_report import SanitizerReport

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.settings import Settings


class ProjectKind(enum.StrEnum):
    C = "c"
    KERNEL = "kernel"
    JAVA = "java"


@dataclass
class Project:
    docker_daemon: dockerblade.DockerDaemon
    kind: ProjectKind
    image: str
    repository: git.Repo
    docker_repository_path: Path
    head: git.Commit
    triggering_commit: git.Commit
    build_command: str
    clean_command: str
    regression_test_command: str
    crash_command_template: str
    sanitizer_report: SanitizerReport
    pov_payload: bytes
    settings: Settings
    evaluation_cache: PatchOutcomeCache = field(init=False)
    validator: PatchValidator = field(init=False)

    def __post_init__(self) -> None:
        self.evaluation_cache = PatchOutcomeCache.for_settings(self.settings)
        self.validator = ThreadedPatchValidator.for_project(self)

    @classmethod
    @contextlib.contextmanager
    def load(
        cls,
        path: str | Path,
        settings: Settings,
    ) -> t.Iterator[t.Self]:
        if isinstance(path, str):
            path = Path(path)
        with path.open("r") as file:
            dict_ = json.load(file)
        with cls.from_dict(dict_, settings) as project:
            yield project

    @classmethod
    @contextlib.contextmanager
    def from_dict(
        cls,
        dict_: dict[str, t.Any],
        settings: Settings,
    ) -> t.Iterator[t.Self]:
        kind = ProjectKind(dict_["project-kind"])
        image = dict_["image"]

        repository_paths = dict_["repository-path"]
        assert isinstance(repository_paths, dict)
        local_repository_path = Path(repository_paths["local"])
        docker_repository_path = Path(repository_paths["docker"])

        triggering_commit_sha = dict_["triggering-commit"]

        pov_payload_path = Path(dict_["pov-payload-filename"])

        commands_dict = dict_["commands"]
        assert isinstance(commands_dict, dict)

        regression_test_command = commands_dict["regression-test"]
        crash_command_template = commands_dict["crash-template"]
        build_command = commands_dict["build"]
        clean_command = commands_dict["clean"]

        sanitizer_report_path = Path(dict_["sanitizer-report-filename"])

        with cls.build(
            build_command=build_command,
            crash_command_template=crash_command_template,
            clean_command=clean_command,
            image=image,
            kind=kind,
            regression_test_command=regression_test_command,
            local_repository_path=local_repository_path,
            docker_repository_path=docker_repository_path,
            sanitizer_report_path=sanitizer_report_path,
            triggering_commit_sha=triggering_commit_sha,
            pov_payload_path=pov_payload_path,
            settings=settings,
        ) as project:
            yield project

    @classmethod
    @contextlib.contextmanager
    def build(
        cls,
        *,
        kind: str,
        image: str,
        local_repository_path: Path,
        docker_repository_path: Path,
        triggering_commit_sha: str,
        build_command: str,
        clean_command: str,
        regression_test_command: str,
        crash_command_template: str,
        sanitizer_report_path: Path,
        pov_payload_path: Path,
        settings: Settings,
        docker_url: str | None = None,
    ) -> t.Iterator[t.Self]:
        assert local_repository_path.is_dir()
        assert docker_repository_path.is_absolute()
        assert sanitizer_report_path.is_file()
        assert pov_payload_path.is_file()
        assert "__PAYLOAD_FILE__" in crash_command_template

        if docker_url is None:
            docker_url = os.environ.get("DOCKER_HOST")

        pov_payload = pov_payload_path.read_bytes()

        project_kind = ProjectKind(kind)
        repository = git.Repo(local_repository_path)
        head = repository.head.commit
        commit = repository.commit(triggering_commit_sha)
        sanitizer_report = SanitizerReport.load(sanitizer_report_path)

        with dockerblade.DockerDaemon(url=docker_url) as docker_daemon:
            project = cls(
                docker_daemon=docker_daemon,
                build_command=build_command,
                crash_command_template=crash_command_template,
                clean_command=clean_command,
                docker_repository_path=docker_repository_path,
                head=head,
                image=image,
                kind=project_kind,
                regression_test_command=regression_test_command,
                repository=repository,
                sanitizer_report=sanitizer_report,
                triggering_commit=commit,
                pov_payload=pov_payload,
                settings=settings,
            )
            try:
                yield project
            finally:
                project.evaluation_cache.save()

    @property
    def local_repository_path(self) -> Path:
        return Path(self.repository.working_dir)

    @contextlib.contextmanager
    def provision(
        self,
        *,
        version: git.Commit | None = None,
        diff: Diff | None = None,
    ) -> t.Iterator[ProjectContainer]:
        with ProjectContainer.provision(
            project=self,
            version=version,
            diff=diff,
        ) as container:
            yield container
