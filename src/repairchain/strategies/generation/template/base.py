__all__ = ("TemplateGenerationStrategy",)

from repairchain.strategies.generation.base import PatchGenerationStrategy


class TemplateGenerationStrategy(PatchGenerationStrategy):
    """Base class for all template-based patch generation strategies."""
