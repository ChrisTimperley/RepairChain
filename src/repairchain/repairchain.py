from __future__ import annotations

__all__ = ("generate", "run")

import typing as t

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
from loguru import logger

from repairchain.actions.generate import generate as _generate
from repairchain.actions.repair import repair

if t.TYPE_CHECKING:
    from pathlib import Path

    from repairchain.models.project import Project


def generate(
    project: Project,
    save_candidates_to: Path,
) -> None:
    save_candidates_to.parent.mkdir(exist_ok=True, parents=True)
    candidates = _generate(project)
    output = [LiteralScalarString(candidate) for candidate in candidates]
    with save_candidates_to.open("w") as file:
        yaml = YAML()
        yaml.indent(sequence=0, offset=2)
        yaml.dump(output, file)


def run(
    project: Project,
    *,
    save_patches_to_dir: Path,
    stop_early: bool = True,
) -> None:
    save_patches_to_dir.mkdir(exist_ok=True, parents=True)

    patches = repair(project, stop_early=stop_early)

    if not patches:
        logger.info("no patches found")
        return

    logger.info(f"saving {len(patches)} patches to {save_patches_to_dir}...")
    for patch_no, patch in enumerate(patches):
        patch_filename = save_patches_to_dir / f"patch_{patch_no}.diff"
        diff_content = str(patch)
        with patch_filename.open("w") as file:
            file.write(diff_content)
    logger.info("saved patches")
