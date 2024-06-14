from __future__ import annotations

import typing as t

from repairchain.actions.determine_patch_generation_strategy import determine_patch_generation_strategy
from repairchain.actions.diagnose import diagnose
from repairchain.actions.validate import validate

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


def repair(
    project: Project,
    *,
    stop_early: bool = True,
) -> list[Diff]:
    """Repairs the given project and returns a list of valid patches.

    If `stop_early` is True, the repair process will stop as soon as a valid patch is found.
    """
    diagnosis = diagnose(project)
    patch_generator = determine_patch_generation_strategy(diagnosis)
    candidates = patch_generator.run()
    return validate(
        project,
        candidates,
        stop_early=stop_early,
    )
