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
    if restrict_to_files is None:
        restrict_to_files = []

    with KaskaraIndexer.build(
        project=project,
        version=version,
        restrict_to_files=restrict_to_files,
    ) as indexer:
        analysis = indexer.run()
        return analysis.functions
