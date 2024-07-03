from __future__ import annotations

__all__ = ("validate", "validate_patch")

import typing as t

from loguru import logger

from repairchain.errors import BuildFailure
from repairchain.models.patch_outcome import PatchOutcome

if t.TYPE_CHECKING:
    import git

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


def validate_patch(
    project: Project,
    diff: Diff,
    *,
    commit: git.Commit | None = None,
) -> PatchOutcome:
    """Applies a given patch to a specific version of a project and returns the outcome."""
    logger.info(f"validating patch: {diff}")
    try:
        with project.provision(version=commit, diff=diff) as container:
            if not container.run_pov():
                return PatchOutcome.FAILED

            if not container.run_regression_tests():
                return PatchOutcome.FAILED

            return PatchOutcome.PASSED

    except BuildFailure:
        return PatchOutcome.FAILED_TO_BUILD


def validate(
    project: Project,
    candidates: list[Diff],
    *,
    commit: git.Commit | None = None,
    stop_early: bool = False,
) -> list[Diff]:
    """Validates the generated patches and returns a list of valid patches.

    If `stop_early` is True, the validation process will stop as soon as a valid patch is found.
    """
    # FIXME do this in parallel!
    repairs: list[Diff] = []

    for candidate in candidates:
        outcome = validate_patch(
            project=project,
            diff=candidate,
            commit=commit,
        )
        logger.info(f"patch outcome: {outcome}")
        if outcome == PatchOutcome.PASSED:
            repairs.append(candidate)
            if stop_early:
                break

    return repairs
