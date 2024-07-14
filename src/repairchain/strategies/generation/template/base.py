from __future__ import annotations

__all__ = ("TemplateGenerationStrategy",)

import abc
import typing as t

from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis


class TemplateGenerationStrategy(PatchGenerationStrategy):
    """Base class for all template-based patch generation strategies."""
    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> TemplateGenerationStrategy:
        """Builds a new instance of this strategy for the given diagnosis."""
        raise NotImplementedError
