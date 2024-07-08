from __future__ import annotations

__all__ = ("index_functions",)

import typing as t

from repairchain.indexer import KaskaraIndexer

if t.TYPE_CHECKING:
    import git
    import kaskara.functions

    from repairchain.models.project import Project


def index_functions(
    project: Project,
    *,
    version: git.Commit | None = None,
    restrict_to_files: list[str] | None = None,
) -> kaskara.functions.ProgramFunctions:
    if version is None:
        version = project.head

    if restrict_to_files is None:
        restrict_to_files = []

    indexer = KaskaraIndexer(project)
    analysis = indexer.run(
        version=version,
        restrict_to_files=restrict_to_files,
    )
    return analysis.functions
