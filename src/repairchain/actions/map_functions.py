from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    import git
    import kaskara.functions

    from repairchain.models.project import Project


def map_functions(
    *,
    project: Project,
    functions: list[kaskara.functions.Function],
    from_version: git.Commit,
    to_version: git.Commit,
    old_function_index: kaskara.functions.ProgramFunctions,
    new_function_index: kaskara.functions.ProgramFunctions,
) -> list[kaskara.functions.Function]:
    raise NotImplementedError
