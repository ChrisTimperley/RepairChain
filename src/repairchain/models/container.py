from __future__ import annotations

__all__ = ("ProjectContainer",)

import contextlib
import typing as t
from dataclasses import dataclass
from pathlib import Path

import dockerblade
from loguru import logger

from repairchain.errors import BuildFailure
from repairchain.models.sanitizer_report import (
    Sanitizer,
    SanitizerReport,
)

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


@dataclass
class ProjectContainer:
    project: Project
    _dockerblade: dockerblade.Container
    _shell: dockerblade.Shell
    _filesystem: dockerblade.FileSystem

    @classmethod
    @contextlib.contextmanager
    def provision(
        cls,
        project: Project,
        version: git.Commit | None = None,
        diff: Diff | None = None,
    ) -> t.Iterator[t.Self]:
        """Constructs a ready-to-use container for the project at a given version with an optional patch.

        Arguments:
        ---------
        project: Project
            The project to build the container for.
        version: git.Commit | None
            The version of the project to build the container for.
            If :code:`None` is given, the container is built for the current version (i.e., HEAD).
        diff: Diff | None
            The patch to apply to the project, if any.
        """
        with project.docker_daemon.provision(
            image=project.image,
            command="/bin/sh",
        ) as dockerblade_container:
            shell = dockerblade_container.shell()
            filesystem = dockerblade_container.filesystem()
            container = cls(
                project=project,
                _dockerblade=dockerblade_container,
                _shell=shell,
                _filesystem=filesystem,
            )
            if version:
                container.checkout(version=version, clean_before=True)
            if diff:
                container.patch(diff)
            if version or diff:
                container.build()
            yield container

    @property
    def id_(self) -> str:
        return self._dockerblade.id

    def clean(self) -> None:
        """Runs the equivalent of `make clean` inside the container."""
        project = self.project
        self._shell.check_call(
            project.clean_command,
            cwd=str(project.docker_repository_path),
        )

    def patch(self, patch: Diff) -> None:
        """Attempts to apply a given patch to the project inside the container.

        Arguments:
        ---------
        patch: Diff
            The patch to apply to the project.

        Raises:
        ------
        BuildFailure
            If the patch cannot be applied.
        """
        container_patch_filename = self._filesystem.mktemp(suffix=".diff")
        patch_contents = str(patch)
        try:
            self._filesystem.put(container_patch_filename, patch_contents)
            self._filesystem.patch(
                context=str(self.project.docker_repository_path),
                diff=str(patch),
            )
        except dockerblade.exceptions.CalledProcessError as err:
            message = "patch failed to apply"
            raise BuildFailure(
                message=message,
                returncode=err.returncode,
            ) from err

    def checkout(
        self,
        version: git.Commit,
        *,
        clean_before: bool = True,
    ) -> None:
        logger.trace(f"checking out version: {version.hexsha}")

        if clean_before:
            self.clean()

        command = f"git checkout {version.hexsha}"
        self._shell.check_call(
            command,
            cwd=str(self.project.docker_repository_path),
        )

    def build(
        self,
        *,
        prefix: str | None = None,
        cwd: str = "/",
    ) -> None:
        """Attempts to build the project inside the container.

        Arguments:
        ---------
        prefix: str | None
            The prefix to prepend to the build command.
            If :code:`None` is given, the project's build command is used as is.
        cwd: str
            The directory to run the build command in.

        Raises:
        ------
        BuildFailure
            If the build fails.
        """
        time_limit = self.project.settings.build_time_limit
        command = self.project.build_command
        if prefix is not None:
            command = f"{prefix} {command}"
        try:
            self._shell.check_output(
                command,
                text=True,
                time_limit=time_limit,
                cwd=cwd,
            )
        except dockerblade.exceptions.CalledProcessError as err:
            assert err.output is not None  # noqa: PT017
            if isinstance(err.output, bytes):  # noqa: SIM108
                output = err.output.decode("utf-8")
            else:
                output = err.output
            raise BuildFailure(
                message=output,
                returncode=err.returncode,
            ) from err

    def exists(self, path: str | Path) -> bool:
        """Checks if a given path exists inside the container.

        Arguments:
        ---------
        path : str | Path
            The path to check.

        Returns:
        -------
        bool
            :code:`True` if the path exists, :code:`False` otherwise.
        """
        if isinstance(path, Path):
            path = str(path)
        return self._filesystem.exists(path)

    def run_regression_tests(self, *, jobs: int = 1) -> bool:
        """Runs the project's regression tests and returns whether they pass.

        Arguments:
        ---------
        jobs: int
            The number of jobs to use (i.e., NPROC_VAL) for running the tests.

        Returns:
        -------
        bool
            :code:`True` if the regression tests pass, :code:`False` otherwise.
        """
        time_limit = self.project.settings.regression_time_limit
        command = self.project.regression_test_command
        env = {"NPROC_VAL": str(jobs)}
        try:
            self._shell.check_call(
                command,
                time_limit=time_limit,
                environment=env,
            )
        except dockerblade.exceptions.CalledProcessError:
            return False
        return True

    def run_pov(self, payload: bytes | None = None) -> bool:
        """Runs the PoV and checks if no sanitizers are encountered.

        Arguments:
        ---------
        payload: bytes | None
            The payload to use for the PoV.
            If :code:`None` is given, the provided PoV for the project is used instead.

        Returns:
        -------
        bool
            :code:`True` if no sanitizers are encountered, :code:`False` otherwise.
        """
        time_limit = self.project.settings.pov_time_limit
        if payload is None:
            payload = self.project.pov_payload

        container_payload_filename = self._filesystem.mktemp(suffix=".payload")
        self._filesystem.put(container_payload_filename, payload)

        crash_command_template = self.project.crash_command_template
        crash_command = crash_command_template.replace(
            "__PAYLOAD_FILE__",
            container_payload_filename,
        )
        # ensure that the PoV execution uses no more than one core
        env = {"NPROC_VAL": "1"}
        outcome = self._shell.run(
            crash_command,
            stdout=True,
            stderr=True,
            text=True,
            time_limit=time_limit,
            environment=env,
        )
        return self._check_pov_outcome(outcome)

    def _check_pov_outcome(self, outcome: dockerblade.CompletedProcess) -> bool:
        """Checks the outcome of a PoV execution.

        Arguments:
        ---------
        outcome: dockerblade.CompletedProcess
            The outcome of the PoV execution.

        Returns:
        -------
        bool
            :code:`True` if no sanitizers were triggered, :code:`False` otherwise.
        """
        assert isinstance(outcome.output, str)
        logger.trace(f"checking PoV output: {outcome.output}")
        detected_sanitizer = SanitizerReport._find_sanitizer(outcome.output)
        logger.trace(f"detected sanitizer: {detected_sanitizer}")
        return detected_sanitizer is Sanitizer.UNKNOWN
