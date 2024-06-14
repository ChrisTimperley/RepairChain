from __future__ import annotations

__all__ = ("validate",)

import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


def validate(
    project: Project,
    candidates: list[Diff],
    *,
    stop_early: bool = False,
) -> list[Diff]:
    """Validates the generated patches and returns a list of valid patches.

    If `stop_early` is True, the validation process will stop as soon as a valid patch is found.
    """
    raise NotImplementedError
