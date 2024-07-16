from __future__ import annotations

import typing as t

from loguru import logger

from repairchain.actions.determine_patch_generation_strategy import (
    choose_minimal_reversion_strategies,
    choose_template_strategies,
    choose_yolo_strategies_early,
    choose_yolo_strategies_late,
)
from repairchain.actions.diagnose import diagnose
from repairchain.actions.validate import validate
from repairchain.strategies.generation.sequence import SequenceStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project
    from repairchain.strategies.generation.base import PatchGenerationStrategy


def _repair_with_strategy_picker(
    diagnosis: Diagnosis,
    picker: t.Callable[[Diagnosis], list[PatchGenerationStrategy]],
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    project = diagnosis.project
    strategies = picker(diagnosis)
    if not strategies:
        return

    generator = SequenceStrategy.build(
        diagnosis=diagnosis,
        strategies=strategies,
    )
    candidates = list(generator.run())
    yield from validate(project, candidates, stop_early=stop_early)


def _repair_with_minimal_reversion(
    diagnosis: Diagnosis,
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    yield from _repair_with_strategy_picker(
        diagnosis,
        choose_minimal_reversion_strategies,
        stop_early=stop_early,
    )


def _repair_with_yolo_early(
    diagnosis: Diagnosis,
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    yield from _repair_with_strategy_picker(
        diagnosis,
        choose_yolo_strategies_early,
        stop_early=stop_early,
    )


def _repair_with_yolo_late(
    diagnosis: Diagnosis,
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    yield from _repair_with_strategy_picker(
        diagnosis,
        choose_yolo_strategies_late,
        stop_early=stop_early,
    )


def _repair_with_templates(
    diagnosis: Diagnosis,
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    yield from _repair_with_strategy_picker(
        diagnosis,
        choose_template_strategies,
        stop_early=stop_early,
    )


def repair(
    project: Project,
    *,
    stop_early: bool = True,
) -> t.Iterator[Diff]:
    """Repairs the given project and yields valid patches.

    If `stop_early` is True, the repair process will stop as soon as a valid patch is found.
    """
    settings = project.settings
    diagnosis = diagnose(project)

    def _run() -> t.Iterator[Diff]:
        if settings.enable_yolo_repair:
            logger.info("attempting to repair via (early) YOLO...")
            yield from _repair_with_yolo_early(diagnosis, stop_early=stop_early)
            logger.info("finished attempting to repair via (early) YOLO")

        if settings.enable_reversion_repair:
            logger.info("attempting to repair via minimal reversion...")
            yield from _repair_with_minimal_reversion(diagnosis, stop_early=stop_early)
            logger.info("finished attempting to repair via minimal reversion")

        if settings.enable_yolo_repair:
            logger.info("attempting to repair via (late) YOLO...")
            yield from _repair_with_yolo_late(diagnosis, stop_early=stop_early)
            logger.info("finished attempting to repair via (late) YOLO")

        if settings.enable_template_repair:
            logger.info("attempting to repair via templates...")
            yield from _repair_with_templates(diagnosis, stop_early=stop_early)
            logger.info("finished attempting to repair via templates")

    for patch in _run():
        yield patch
        if stop_early:
            return
