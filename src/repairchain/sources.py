from __future__ import annotations

import typing as t
from dataclasses import dataclass
from pathlib import Path

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project
    from repairchain.models.replacement import Replacement


@dataclass
class ProjectSources:
    project: Project

    @classmethod
    def for_project(cls, project: Project) -> ProjectSources:
        return cls(project)

    def source(
        self,
        filename: Path | str,
        version: git.Commit | None = None,
    ) -> str:
        """Retrieves the contents of a given a file.

        Arguments:
        ---------
        filename: Path | str
            The path to the file to retrieve, relative to the root of
            the repository.
        version: git.Commit | None
            The version of the file to retrieve.
            If None, the HEAD is used.

        Returns:
        -------
        str
            The contents of the file.

        Raises:
        ------
        ValueError
            If the given filename is not a relative path.
        FileNotFoundError
            If the file does not exist in the repository (version).
        """
        if version is None:
            version = self.project.head

        if isinstance(filename, str):
            filename = Path(filename)

        if not filename.is_absolute():
            message = f"filename must be a relative path: {filename}"
            raise ValueError(message)

        raise NotImplementedError

    def replacements_to_diff(
        self,
        replacements: list[Replacement],
        version: git.Commit | None = None,
    ) -> Diff:
        raise NotImplementedError
