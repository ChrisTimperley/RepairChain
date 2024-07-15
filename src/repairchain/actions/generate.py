from __future__ import annotations

__all__ = ("generate",)

import typing as t

from repairchain.actions.determine_patch_generation_strategy import determine_patch_generation_strategy
from repairchain.actions.diagnose import diagnose

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


def generate(project: Project) -> list[Diff]:
    """Generates a list of candidate patches for the given project."""
    diagnosis = diagnose(project)
    patch_generator = determine_patch_generation_strategy(diagnosis)
    return list(patch_generator.run())
