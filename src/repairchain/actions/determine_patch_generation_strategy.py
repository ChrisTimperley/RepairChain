from __future__ import annotations

from repairchain.strategies.generation.llm.superyolo_llm import SuperYoloLLMStrategy
from repairchain.strategies.generation.llm.yolo_llm import YoloLLMStrategy
from repairchain.strategies.generation.template.increase_size import IncreaseSizeStrategy
from repairchain.strategies.generation.template.init_mem import InitializeMemoryStrategy
from repairchain.strategies.generation.template.integer_overflow import IntegerOverflowStrategy

__all__ = ("determine_patch_generation_strategy",)

import typing as t

from loguru import logger

from repairchain.strategies.generation.reversion import MinimalPatchReversion
from repairchain.strategies.generation.sequence import SequenceStrategy
from repairchain.strategies.generation.template.bounds_check import BoundsCheckStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.strategies.generation import PatchGenerationStrategy

available_templates = [BoundsCheckStrategy,
                       IncreaseSizeStrategy,
                       InitializeMemoryStrategy,
                       IntegerOverflowStrategy]


def _build_yolo_strategies_with_kaskara_indices(
    diagnosis: Diagnosis,
) -> list[PatchGenerationStrategy]:
    strategies: list[PatchGenerationStrategy] = []

    # try different models
    # - note that claude has some issues with JSON format and needs to requery
    for model in ("oai-gpt-4o", "claude-3.5-sonnet"):
        # and try:
        # (a) use all files in context and ask for multiple patches at once (preferred)
        # (b) use a single file as context and ask for one patch at a time
        for use_patches_per_file_strategy in (True, False):
            strategy = YoloLLMStrategy.build(
                diagnosis=diagnosis,
                model=model,
                use_patches_per_file_strategy=use_patches_per_file_strategy,
            )
            strategies.append(strategy)

    # gpt4-turbo is much more expensive, so we only try one strategy
    yolo_gpt4_turbo = YoloLLMStrategy.build(
        diagnosis=diagnosis,
        model="oai-gpt-4-turbo",
        use_patches_per_file_strategy=True,
    )
    strategies.append(yolo_gpt4_turbo)

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


def _determine_yolo_strategies(
    diagnosis: Diagnosis,
) -> list[PatchGenerationStrategy]:
    if diagnosis.is_complete():
        logger.info("using yolo repair strategy with full kaskara indices")
        return _build_yolo_strategies_with_kaskara_indices(diagnosis)

    logger.warning("using super yolo repair strategy (diagnosis is incomplete)")
    return _build_yolo_strategies_without_kaskara_indices(diagnosis)


def determine_patch_generation_strategy(
    diagnosis: Diagnosis,
) -> PatchGenerationStrategy:
    logger.info("determining patch generation strategy...")
    settings = diagnosis.project.settings
    strategies: list[PatchGenerationStrategy] = []

    if settings.enable_reversion_repair:
        logger.info("using reversion repair strategy")
        strategies.append(MinimalPatchReversion.build(diagnosis))
    else:
        logger.info("skipping reversion repair strategy (disabled)")

    if settings.enable_yolo_repair:
        logger.info("using yolo repair strategies")
        strategies += _determine_yolo_strategies(diagnosis)
    else:
        logger.info("skipping yolo repair strategy (disabled)")

    if settings.enable_template_repair:
        logger.info("attempting template repair strategies")
        strategies += [tstrat.build(diagnosis) for tstrat in AVAILABLE_TEMPLATES if tstrat.applies(diagnosis)]
    else:
        logger.info("skipping template repair strategy (disabled)")

    strategy = SequenceStrategy(diagnosis, strategies)
    logger.info(f"determined patch generation strategy: {strategy}")
    return strategy
