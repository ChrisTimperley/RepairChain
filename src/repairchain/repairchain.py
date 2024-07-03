from __future__ import annotations

__all__ = ("generate", "run")

import typing as t

from loguru import logger

from repairchain.actions.generate import generate as _generate
from repairchain.actions.repair import repair
from repairchain.actions.validate import validate as _validate
from repairchain.models.diff import Diff

if t.TYPE_CHECKING:
    from pathlib import Path

    from repairchain.models.project import Project


def generate(
    project: Project,
    save_candidates_to_directory: Path,
) -> None:
    save_candidates_to_directory.mkdir(exist_ok=True, parents=True)
    candidates = _generate(project)
    for candidate_no, candidate in enumerate(candidates):
        candidate_path = save_candidates_to_directory / f"{candidate_no}.diff"
        with candidate_path.open("w") as file:
            file.write(str(candidate))


def validate(
    project: Project,
    candidates_directory: Path,
    save_patches_to_dir: Path,
    *,
    stop_early: bool = True,
) -> None:
    save_patches_to_dir.mkdir(exist_ok=True, parents=True)

    assert candidates_directory.is_dir()

    candidates: list[Diff] = []

    for candidate_path in candidates_directory.iterdir():
        if not candidate_path.is_file():
            continue
        if candidate_path.suffix != ".diff":
            continue

        with candidate_path.open("r") as file:
            content = file.read()

        candidate = Diff.from_unidiff(content)
        candidates.append(candidate)

    patches = _validate(
        project=project,
        candidates=candidates,
        stop_early=stop_early,
    )

    for patch_no, patch in enumerate(patches):
        patch_filename = save_patches_to_dir / f"{patch_no}.diff"
        diff_content = str(patch)
        with patch_filename.open("w") as file:
            file.write(diff_content)


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
