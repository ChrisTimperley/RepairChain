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
from dockerblade import Stopwatch
from loguru import logger

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.validate import (
    PatchValidator,
    ThreadedPatchValidator,
)
from repairchain.indexer import KaskaraIndexer
from repairchain.models.container import ProjectContainer
from repairchain.models.patch_outcome import PatchOutcomeCache
from repairchain.sources import ProjectSources

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.settings import Settings


class ProjectKind(enum.StrEnum):
    C = "c"
    KERNEL = "kernel"
    JAVA = "java"


@dataclass
class Project:
    docker_daemon: dockerblade.DockerDaemon = field(repr=False)
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
    sanitizer_output: str
    pov_payload: bytes = field(repr=False)
    settings: Settings
    evaluation_cache: PatchOutcomeCache = field(init=False, repr=False)
    validator: PatchValidator = field(init=False, repr=False)
    indexer: KaskaraIndexer = field(init=False, repr=False)
    sources: ProjectSources = field(init=False, repr=False)
    _time_elapsed: Stopwatch = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._time_elapsed = Stopwatch()
        self._time_elapsed.start()
        self.sources = ProjectSources.for_project(self)
        self.evaluation_cache = PatchOutcomeCache.for_settings(self.settings)
        self.validator = ThreadedPatchValidator.for_project(self)
        self.indexer = KaskaraIndexer.for_project(self, self.sources)

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
        with cls.from_dict(dict_, settings, path.parent.absolute()) as project:
            yield project

    @classmethod
    @contextlib.contextmanager
    def from_dict(
        cls,
        dict_: dict[str, t.Any],
        settings: Settings,
        directory: Path,
    ) -> t.Iterator[t.Self]:
        if not directory.is_dir():
            message = f"directory does not exist: {directory}"
            raise ValueError(message)

        if not directory.is_absolute():
            message = f"directory is not absolute: {directory}"
            raise ValueError(message)

        kind = ProjectKind(dict_["project-kind"])
        image = dict_["image"]

        repository_paths = dict_["repository-path"]
        assert isinstance(repository_paths, dict)
        local_repository_path = Path(repository_paths["local"])
        if not local_repository_path.is_absolute():
            local_repository_path = directory / local_repository_path

        docker_repository_path = Path(repository_paths["docker"])

        triggering_commit_sha = dict_["triggering-commit"]

        pov_payload_path = Path(dict_["pov-payload-filename"])
        if not pov_payload_path.is_absolute():
            pov_payload_path = directory / pov_payload_path

        commands_dict = dict_["commands"]
        assert isinstance(commands_dict, dict)

        regression_test_command = commands_dict["regression-test"]
        crash_command_template = commands_dict["crash-template"]
        build_command = commands_dict["build"]
        clean_command = commands_dict["clean"]

        sanitizer_report_path = Path(dict_["sanitizer-report-filename"])
        if not sanitizer_report_path.is_absolute():
            sanitizer_report_path = directory / sanitizer_report_path

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
        assert local_repository_path.is_absolute()
        assert docker_repository_path.is_absolute()
        assert sanitizer_report_path.is_absolute()
        assert sanitizer_report_path.is_file()
        assert pov_payload_path.is_absolute()
        assert pov_payload_path.is_file()
        assert "__PAYLOAD_FILE__" in crash_command_template

        if docker_url is None:
            docker_url = os.environ.get("DOCKER_HOST")

        pov_payload = pov_payload_path.read_bytes()

        project_kind = ProjectKind(kind)
        repository = git.Repo(local_repository_path)
        head = repository.head.commit
        commit = repository.commit(triggering_commit_sha)

        if not commit.parents:
            message = f"triggering commit ({commit}) is the initial commit"
            raise ValueError(message)

        with sanitizer_report_path.open("r") as file:
            sanitizer_output = file.read()

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
                sanitizer_output=sanitizer_output,
                triggering_commit=commit,
                pov_payload=pov_payload,
                settings=settings,
            )
            try:
                yield project
            finally:
                project.indexer.save_cache()
                project.evaluation_cache.save()

    @property
    def local_repository_path(self) -> Path:
        return Path(self.repository.working_dir)

    @property
    def time_limit(self) -> int:
        """Returns the time limit in seconds."""
        return self.settings.time_limit

    @property
    def time_elapsed(self) -> float:
        """Returns the time elapsed in seconds."""
        return self._time_elapsed.duration

    @property
    def original_implicated_diff(self) -> Diff:
        """Returns the (unminimized) implicated diff."""
        return commit_to_diff(self.triggering_commit)

    @property
    def time_left(self) -> float:
        """Returns the time left in seconds."""
        assert self.settings.time_limit is not None
        return max(self.settings.time_limit - self.time_elapsed, 0)

    def sanity_check(self) -> None:
        """Ensures that this project is valid."""
        workers = self.settings.workers
        with self.provision(build_jobs=workers) as container:
            logger.info("running sanity check")
            assert container.run_regression_tests(jobs=workers)
            assert not container.run_pov()

    @contextlib.contextmanager
    def provision(
        self,
        *,
        version: git.Commit | None = None,
        diff: Diff | None = None,
        build_jobs: int = 1,
    ) -> t.Iterator[ProjectContainer]:
        with ProjectContainer.provision(
            project=self,
            version=version,
            diff=diff,
            build_jobs=build_jobs,
        ) as container:
            yield container
