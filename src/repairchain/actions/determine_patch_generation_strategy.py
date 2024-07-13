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
        if diagnosis_is_complete:
            logger.info("using yolo repair strategy")
            yolo_gpt4o = YoloLLMStrategy.build(diagnosis)
            yolo_gpt4o._set_model("oai-gpt-4o")
            strategies.append(yolo_gpt4o)
            yolo_claude35 = YoloLLMStrategy.build(diagnosis)
            yolo_claude35._set_model("claude-3.5-sonnet")
            strategies.append(yolo_claude35)
        else:
            logger.warning("using super yolo repair strategy (diagnosis is incomplete)")
            superyolo_gpt4o_files = SuperYoloLLMStrategy.build(diagnosis)
            superyolo_gpt4o_files.whole_file = True
            strategies.append(superyolo_gpt4o_files)

            superyolo_gpt4o_diffs = SuperYoloLLMStrategy.build(diagnosis)
            strategies.append(superyolo_gpt4o_diffs)

            superyolo_claude35_files = SuperYoloLLMStrategy.build(diagnosis)
            superyolo_claude35_files._set_model("claude-3.5-sonnet")
            superyolo_claude35_files.whole_file = True
            strategies.append(superyolo_claude35_files)

            superyolo_claude35_diffs = SuperYoloLLMStrategy.build(diagnosis)
            superyolo_claude35_diffs._set_model("claude-3.5-sonnet")
            strategies.append(superyolo_claude35_diffs)

    else:
        logger.info("skipping yolo repair strategy (disabled)")

    if settings.enable_template_repair:
        logger.info("attempting template repair strategies")
        strategies += [tstrat.build(diagnosis) for tstrat in available_templates if tstrat.applies(diagnosis)]
    else:
        logger.info("skipping template repair strategy (disabled)")

    strategy = SequenceStrategy(diagnosis, strategies)
    logger.info(f"determined patch generation strategy: {strategy}")
    return strategy
