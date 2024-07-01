from __future__ import annotations
from dataclasses import dataclass

from repairchain.models.diagnosis import Diagnosis
from repairchain.strategies.generation.base import PatchGenerationStrategy

@dataclass
class TemplateBasedRepair(PatchGenerationStrategy):
    diagnosis: Diagnosis

    @classmethod
    def build(
            cls,
            diagnosis: Diagnosis,
    ) -> TemplateBasedRepair:
        return cls(
            diagnosis=diagnosis,
        )
    
    