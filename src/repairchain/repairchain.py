from __future__ import annotations

__all__ = (
    "diagnose",
    "generate",
    "run",
    "validate",
)

import typing as t

from loguru import logger

from repairchain.actions.diagnose import diagnose as _diagnose
from repairchain.actions.generate import generate as _generate
from repairchain.actions.repair import repair
from repairchain.actions.validate import validate as _validate
from repairchain.models.diff import Diff
from repairchain.util import add_prefix_to_diff

if t.TYPE_CHECKING:
    from pathlib import Path

    from repairchain.models.project import Project


def diagnose(
    project: Project,
    save_to_file: Path,
) -> None:
    save_to_file.parent.mkdir(exist_ok=True, parents=True)
    diagnosis = _diagnose(project)
    diagnosis.save(save_to_file)


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

    for patch_no, patch in enumerate(_validate(
        project=project,
        candidates=candidates,
        stop_early=stop_early,
    )):
        patch_filename = save_patches_to_dir / f"{patch_no}.diff"
        diff_content = str(add_prefix_to_diff(patch))
        with patch_filename.open("w") as file:
            file.write(diff_content)


def run(
    project: Project,
    *,
    save_patches_to_dir: Path,
    stop_early: bool = True,
) -> None:
    settings = project.settings

    if settings.log_to_file:
        log_level = settings.log_level
        settings.log_to_file.parent.mkdir(exist_ok=True, parents=True)

        logger.enable("kaskara")
        if log_level == "TRACE":
            logger.enable("dockerblade")
            logger.enable("sourcelocation")

        logger.add(
            sink=settings.log_to_file,
            level=log_level,
        )

    save_patches_to_dir.mkdir(exist_ok=True, parents=True)

    num_patches_found = 0
    for patch_no, patch in enumerate(repair(project, stop_early=stop_early)):
        num_patches_found += 1
        patch_filename = save_patches_to_dir / f"{patch_no}.diff"
        logger.info(f"patch found: {patch_filename}")
        diff_content = str(add_prefix_to_diff(patch))
        with patch_filename.open("w") as file:
            file.write(diff_content)

        if stop_early:
            logger.info("stopping patch generation early")
            break

    if num_patches_found == 0:
        logger.info("no patches found")
