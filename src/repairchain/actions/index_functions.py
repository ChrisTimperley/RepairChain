from __future__ import annotations

__all__ = ("index_functions",)

import typing as t

from dockerblade.stopwatch import Stopwatch
from loguru import logger

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

    stopwatch = Stopwatch()
    logger.info(f"indexing functions for project version: {version}")
    stopwatch.start()

    if restrict_to_files is None:
        restrict_to_files = []

    with KaskaraIndexer.build(
        project=project,
        version=version,
        restrict_to_files=restrict_to_files,
    ) as indexer:
        analysis = indexer.run()

    time_taken = stopwatch.duration
    logger.info(f"indexed {len(analysis.functions)} functions (took {time_taken:.2f}s)")
    return analysis.functions
