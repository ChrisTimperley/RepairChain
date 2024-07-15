from __future__ import annotations

__all__ = ("generate",)

import typing as t

from repairchain.actions.determine_patch_generation_strategy import choose_all_patch_strategies
from repairchain.actions.diagnose import diagnose
from repairchain.strategies.generation.sequence import SequenceStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project


def generate(project: Project) -> list[Diff]:
    """Generates a complete list of all candidate patches for the given project."""
    diagnosis = diagnose(project)
    strategies = choose_all_patch_strategies(diagnosis)
    generator = SequenceStrategy.build(
        diagnosis=diagnosis,
        strategies=strategies,
    )
    return list(generator.run())
