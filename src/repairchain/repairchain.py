from __future__ import annotations

__all__ = ("run",)

import typing as t

from repairchain.actions.repair import repair

if t.TYPE_CHECKING:
    from pathlib import Path

    from repairchain.models.project import Project


def run(
    project: Project,
    *,
    save_patches_to_dir: Path,
    stop_early: bool = True,
) -> None:
    patches = repair(project, stop_early=stop_early)

    # TODO format the repairs and write them to a specified file (for VERSATIL)
    print(f"saving patches to {save_patches_to_dir}...")
    print(patches)
    raise NotImplementedError
