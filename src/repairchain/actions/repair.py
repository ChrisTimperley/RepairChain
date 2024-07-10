from __future__ import annotations

import typing as t

from repairchain.actions.generate import generate
from repairchain.actions.validate import validate

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


def repair(
    project: Project,
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    """Repairs the given project and yields valid patches.

    If `stop_early` is True, the repair process will stop as soon as a valid patch is found.
    """
    candidates = generate(project)
    yield from validate(
        project,
        candidates,
        stop_early=stop_early,
    )
