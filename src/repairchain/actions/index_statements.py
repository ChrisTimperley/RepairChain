from __future__ import annotations

__all__ = ("index_statements",)

import typing as t

if t.TYPE_CHECKING:
    import git
    import kaskara.functions
    import kaskara.statements

    from repairchain.models.project import Project


def index_statements(
    project: Project,
    *,
    version: git.Commit | None = None,
    restrict_to_files: list[str] | None = None,
    restrict_to_functions: list[kaskara.functions.Function] | None = None,
) -> kaskara.statements.ProgramStatements:
    """Produces an index of the statements in a given project.

    If `version` is provided, statements are indexed at that version,
    otherwise, statements are indexed at the current version (i.e., HEAD).
    """
    raise NotImplementedError
