from __future__ import annotations

import typing as t
from dataclasses import dataclass

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

    def replacements_to_diff(
        self,
        replacements: list[Replacement],
        version: git.Commit | None = None,
    ) -> Diff:
        raise NotImplementedError
