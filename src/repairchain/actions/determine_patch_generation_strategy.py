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


def determine_patch_generation_strategy(
    diagnosis: Diagnosis,
) -> PatchGenerationStrategy:
    logger.info("determining patch generation strategy...")
    settings = diagnosis.project.settings
    strategies: list[PatchGenerationStrategy] = []

    diagnosis_is_complete = diagnosis.is_complete()

    if settings.enable_reversion_repair:
        logger.info("using reversion repair strategy")
        strategies.append(MinimalPatchReversion.build(diagnosis))
    else:
        logger.info("skipping reversion repair strategy (disabled)")

    if settings.enable_yolo_repair:
        # FIXME this should be more precise
        if diagnosis_is_complete:
            logger.info("using yolo repair strategy")
            # strategies that use all files in context and ask for multiple patches at once
            # this is the preferred model
            yolo_gpt4o = YoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="oai-gpt-4o",
                use_patches_per_file_strategy=False,
            )
            strategies.append(yolo_gpt4o)

            # claude has some issues with JSON format and needs to requery
            yolo_claude35 = YoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="claude-3.5-sonnet",
                use_patches_per_file_strategy=False,
            )
            strategies.append(yolo_claude35)

            # strategies that use single file as context and ask for one patch at a time
            # trying gpt4_turbo to diversify -- more expensive than gpt4o so only one strategy
            yolo_gpt4_turbo = YoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="oai-gpt-4-turbo",
                use_patches_per_file_strategy=True,
            )
            strategies.append(yolo_gpt4_turbo)

            # claude
            yolo_claude35_simple = YoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="claude-3.5-sonnet",
                use_patches_per_file_strategy=True,
            )
            strategies.append(yolo_claude35_simple)

            # gpt4o
            yolo_gpt4o_simple = YoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="oai-gpt-4o",
                use_patches_per_file_strategy=True,
            )
            strategies.append(yolo_gpt4o_simple)
        else:
            logger.warning("using super yolo repair strategy (diagnosis is incomplete)")

            # strategies that try to generate the entire file
            superyolo_gpt4o_files = SuperYoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="oai-gpt-4o",
                whole_file=True,
            )
            strategies.append(superyolo_gpt4o_files)

            superyolo_claude35_files = SuperYoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="claude-3.5-sonnet",
                whole_file=True,
            )
            strategies.append(superyolo_claude35_files)

            # strategies that use unified diffs as patches
            superyolo_gpt4o_diffs = SuperYoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="oai-gpt-4o",
                whole_file=False,
            )
            strategies.append(superyolo_gpt4o_diffs)

            superyolo_claude35_diffs = SuperYoloLLMStrategy.build(
                diagnosis=diagnosis,
                model="claude-3.5-sonnet",
                whole_file=False,
            )
            strategies.append(superyolo_claude35_diffs)

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
