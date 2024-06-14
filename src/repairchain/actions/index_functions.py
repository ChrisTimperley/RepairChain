from __future__ import annotations

__all__ = ("index_functions",)

import typing as t

if t.TYPE_CHECKING:
    import git
    import kaskara.functions

    from repairchain.models.project import Project


# NOTE we should only bother indexing implicated files
def index_functions(
    project: Project,
    *,
    version: git.Commit | None = None,
) -> kaskara.functions.ProgramFunctions:
    """Produces an index of the functions in a given project.

    If `version` is provided, the functions are indexed at that version,
    otherwise, the functions are indexed at the current version (i.e., HEAD).
    """
    raise NotImplementedError
