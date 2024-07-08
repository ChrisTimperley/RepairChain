from __future__ import annotations

from repairchain.strategies.generation.llm.simple_yolo import SimpleYolo
from repairchain.strategies.generation.llm.summarize_code import ReportSummary

__all__ = ("determine_patch_generation_strategy",)

import typing as t

from loguru import logger

# from repairchain.strategies.generation.reversion import MinimalPatchReversion
from repairchain.strategies.generation.sequence import SequenceStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.strategies.generation import PatchGenerationStrategy


def determine_patch_generation_strategy(
    diagnosis: Diagnosis,
) -> PatchGenerationStrategy:
    logger.info("determining patch generation strategy...")

    summary = ReportSummary()
    print(summary._get_llm_code_report(diagnosis))

    # TODO add settings to enable and disable certain strategies
    yolo = SimpleYolo.build(diagnosis)
    # reversion = MinimalPatchReversion.build(diagnosis)
    strategies = [yolo]

    strategy = SequenceStrategy(strategies)
    logger.info(f"determined patch generation strategy: {strategy}")
    return strategy
