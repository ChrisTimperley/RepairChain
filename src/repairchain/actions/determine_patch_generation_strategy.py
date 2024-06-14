from __future__ import annotations

__all__ = ("determine_patch_generation_strategy",)

import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.strategies.generation import PatchGenerationStrategy


def determine_patch_generation_strategy(
    diagnosis: Diagnosis,
) -> PatchGenerationStrategy:
    print("determining patch generation strategy...")
    raise NotImplementedError
