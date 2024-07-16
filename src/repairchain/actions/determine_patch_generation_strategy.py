from __future__ import annotations

from repairchain.strategies.generation.llm.superyolo_llm import SuperYoloLLMStrategy
from repairchain.strategies.generation.llm.yolo_llm import YoloLLMStrategy
from repairchain.strategies.generation.template.increase_size import IncreaseSizeStrategy
from repairchain.strategies.generation.template.init_mem import InitializeMemoryStrategy
from repairchain.strategies.generation.template.integer_overflow import IntegerOverflowStrategy

__all__ = (
    "choose_all_patch_strategies",
    "choose_minimal_reversion_strategies",
    "choose_template_strategies",
    "choose_yolo_strategies",
)

import typing as t

from loguru import logger

from repairchain.strategies.generation.reversion import MinimalPatchReversion
from repairchain.strategies.generation.template.bounds_check import BoundsCheckStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.strategies.generation import PatchGenerationStrategy
    from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

AVAILABLE_TEMPLATES: list[type[TemplateGenerationStrategy]] = [
    BoundsCheckStrategy,
    IncreaseSizeStrategy,
    InitializeMemoryStrategy,
    IntegerOverflowStrategy,
]


def _build_yolo_strategies_with_kaskara_indices(
    diagnosis: Diagnosis,
) -> list[PatchGenerationStrategy]:
    strategies: list[PatchGenerationStrategy] = []

    # and try:
    # (a) use all files in context and ask for multiple patches at once (preferred)
    # (b) use a single file as context and ask for one patch at a time
    for use_patches_per_file_strategy in (True, False):
        strategy = YoloLLMStrategy.build(
            diagnosis=diagnosis,
            model="oai-gpt-4o",
            use_patches_per_file_strategy=use_patches_per_file_strategy,
        )
        strategies.append(strategy)

    # limited claude use since it has issues with JSON
    yolo_claude35 = YoloLLMStrategy.build(
        diagnosis=diagnosis,
        model="claude-3.5-sonnet",
        use_patches_per_file_strategy=True,
    )
    strategies.append(yolo_claude35)

    # super-yolo has a different prompt and may give diversity
    super_yolo = SuperYoloLLMStrategy.build(
        diagnosis=diagnosis,
        model="oai-gpt-4o",
        whole_file=False,
    )
    strategies.append(super_yolo)

    return strategies


def _build_yolo_strategies_without_kaskara_indices(
    diagnosis: Diagnosis,
) -> list[PatchGenerationStrategy]:
    strategies: list[PatchGenerationStrategy] = []
    for model in ("oai-gpt-4o", "claude-3.5-sonnet"):
        # vary:
        # (a) try to generate the entire file
        # (b) unified diffs as patches
        for whole_file in (True, False):
            strategy = SuperYoloLLMStrategy.build(
                diagnosis=diagnosis,
                model=model,
                whole_file=whole_file,
            )
            strategies.append(strategy)

    return strategies


def choose_yolo_strategies(diagnosis: Diagnosis) -> list[PatchGenerationStrategy]:
    if not diagnosis.project.settings.enable_yolo_repair:
        logger.info("skipping yolo repair strategy (disabled)")
        return []

    logger.info("choosing yolo repair strategies...")

    if diagnosis.is_complete():
        logger.info("using yolo repair strategy with full kaskara indices")
        return _build_yolo_strategies_with_kaskara_indices(diagnosis)

    logger.warning("using super yolo repair strategy (diagnosis is incomplete)")
    return _build_yolo_strategies_without_kaskara_indices(diagnosis)


def choose_minimal_reversion_strategies(diagnosis: Diagnosis) -> list[PatchGenerationStrategy]:
    if not diagnosis.project.settings.enable_reversion_repair:
        logger.info("skipping reversion repair strategy (disabled)")
        return []

    logger.info("using reversion repair strategy")
    strategy = MinimalPatchReversion.build(diagnosis)
    return [strategy]


def choose_template_strategies(diagnosis: Diagnosis) -> list[PatchGenerationStrategy]:
    if not diagnosis.project.settings.enable_template_repair:
        logger.info("skipping template repair strategy (disabled)")
        return []

    strategies: list[PatchGenerationStrategy] = []
    for template in AVAILABLE_TEMPLATES:
        if template.applies(diagnosis):
            strategy = template.build(diagnosis)
            strategies.append(strategy)
    return strategies


def choose_all_patch_strategies(diagnosis: Diagnosis) -> list[PatchGenerationStrategy]:
    logger.info("choosing patch generation strategies...")
    strategies: list[PatchGenerationStrategy] = []
    strategies += choose_minimal_reversion_strategies(diagnosis)
    strategies += choose_yolo_strategies(diagnosis)
    strategies += choose_template_strategies(diagnosis)
    return strategies
