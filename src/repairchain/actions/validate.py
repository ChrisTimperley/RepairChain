from __future__ import annotations

__all__ = ("validate", "validate_patch")

import typing as t

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.patch_outcome import PatchOutcome
    from repairchain.models.project import Project


def validate_patch(
    project: Project,
    commit: git.Commit,
    diff: Diff,
) -> PatchOutcome:
    """Applies a given patch to a specific version of a project and returns the outcome."""
    raise NotImplementedError


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
