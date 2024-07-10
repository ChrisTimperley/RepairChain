from __future__ import annotations

from repairchain.strategies.generation.llm.yolo_llm import YoloLLMStrategy
from repairchain.strategies.generation.template.strategy import TemplateBasedRepair

__all__ = ("determine_patch_generation_strategy",)

import typing as t

from loguru import logger

from repairchain.strategies.generation.reversion import MinimalPatchReversion
from repairchain.strategies.generation.sequence import SequenceStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.strategies.generation import PatchGenerationStrategy


def determine_patch_generation_strategy(
    diagnosis: Diagnosis,
) -> PatchGenerationStrategy:
    logger.info("determining patch generation strategy...")

    # TODO add settings to enable and disable certain strategies
    reversion = MinimalPatchReversion.build(diagnosis)  # noqa: F841
    yolo = YoloLLMStrategy.build(diagnosis)  # noqa: F841
    templates = TemplateBasedRepair.build(diagnosis)
    strategies = [templates]

    strategy = SequenceStrategy(strategies)
    logger.info(f"determined patch generation strategy: {strategy}")
    return strategy
