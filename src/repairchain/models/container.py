from __future__ import annotations

__all__ = ("ProjectContainer",)

import contextlib
import typing as t
from dataclasses import dataclass

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
        container_patch_filename = self._filesystem.mktemp(suffix=".diff")
        patch_contents = str(patch)
        self._filesystem.put(container_patch_filename, patch_contents)
        self._filesystem.patch(
            context=str(self.project.docker_repository_path),
            diff=str(patch),
        )

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

    def build(self) -> None:
        """Attempts to build the project inside the container.

        Raises
        ------
        BuildFailure
            If the build fails.
        """
        command = self.project.build_command
        try:
            self._shell.check_output(command, text=True)
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

    def run_regression_tests(self) -> bool:
        """Runs the project's regression tests and returns whether they pass."""
        command = self.project.regression_test_command
        try:
            self._shell.check_call(command)
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
        if payload is None:
            payload = self.project.pov_payload

        container_payload_filename = self._filesystem.mktemp(suffix=".payload")
        self._filesystem.put(container_payload_filename, payload)

        crash_command_template = self.project.crash_command_template
        crash_command = crash_command_template.replace(
            "__PAYLOAD_FILE__",
            container_payload_filename,
        )

        # TODO inject time limit!
        outcome = self._shell.run(
            crash_command,
            stdout=True,
            stderr=True,
            text=True,
        )

        # TODO we're going to have to detect time limits
        # outcome.duration >= time_limit
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
        logger.debug(f"checking PoV output: {outcome.output}")
        detected_sanitizer = SanitizerReport._find_sanitizer(outcome.output)
        logger.debug(f"detected sanitizer: {detected_sanitizer}")
        return detected_sanitizer is Sanitizer.UNKNOWN
