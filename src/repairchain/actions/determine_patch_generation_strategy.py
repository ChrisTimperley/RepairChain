from __future__ import annotations

__all__ = ("determine_patch_generation_strategy",)

import typing as t

from loguru import logger

from repairchain.models.bug_type import BugType
from repairchain.strategies.generation.llm.yolo_llm import YoloLLMStrategy
from repairchain.strategies.generation.reversion import MinimalPatchReversion
from repairchain.strategies.generation.sequence import SequenceStrategy
from repairchain.strategies.generation.template.bounds_check import BoundsCheckStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.strategies.generation import PatchGenerationStrategy


def determine_patch_generation_strategy(
    diagnosis: Diagnosis,
) -> PatchGenerationStrategy:
    logger.info("determining patch generation strategy...")
    settings = diagnosis.project.settings
    strategies: list[PatchGenerationStrategy] = []

    if settings.enable_reversion_repair:
        strategies.append(MinimalPatchReversion.build(diagnosis))

    if settings.enable_yolo_repair:
        yolo_gpt4o = YoloLLMStrategy.build(diagnosis)
        yolo_gpt4o._set_model("oai-gpt-4o")
        # strategies.append(yolo_gpt4o)
        yolo_claude35 = YoloLLMStrategy.build(diagnosis)
        yolo_claude35._set_model("claude-3.5-sonnet")
        strategies.append(yolo_claude35)

    if settings.enable_template_repair:
        match diagnosis.bug_type:
            case BugType.OUT_OF_BOUNDS_READ | BugType.OUT_OF_BOUNDS_WRITE:
                strategies.append(BoundsCheckStrategy.build(diagnosis))
            case _:
                logger.warning(f"no templates available for bug type: {diagnosis.bug_type}")

    strategy = SequenceStrategy(strategies)
    logger.info(f"determined patch generation strategy: {strategy}")
    return strategy
