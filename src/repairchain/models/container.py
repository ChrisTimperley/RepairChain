from __future__ import annotations

__all__ = ("ProjectContainer",)

import contextlib
import typing as t
from dataclasses import dataclass

if t.TYPE_CHECKING:
    import dockerblade
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


@dataclass
class ProjectContainer:
    project: Project
    _dockerblade: dockerblade.Container
    _shell: dockerblade.Shell

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
        ) as dockerblade_container:
            shell = dockerblade_container.shell()
            container = cls(
                project=project,
                _dockerblade=dockerblade_container,
                _shell=shell,
            )
            if version:
                container.checkout(version=version, clean_before=True)
            if diff:
                container.patch(diff)
            if version or diff:
                container.build()
            yield container

    def clean(self) -> None:
        """Runs the equivalent of `make clean` inside the container."""
        project = self.project
        self._shell.check_call(
            project.clean_command,
            cwd=str(project.docker_repository_path),
        )

    def patch(self, patch: Diff) -> None:
        raise NotImplementedError

    def checkout(
        self,
        version: git.Commit,
        *,
        clean_before: bool = True,
    ) -> None:
        if clean_before:
            self.clean()

        command = f"git checkout {version.hexsha}"
        self._shell.check_call(
            command,
            cwd=str(self.project.docker_repository_path),
        )

    # TODO raise a special error in the event of a build failure
    def build(self) -> None:
        command = self.project.build_command
        self._shell.check_call(command)
