from __future__ import annotations

import abc
import typing as t
from dataclasses import dataclass

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy


class TemplateGenerationStrategy(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def build(cls) -> t.Self:
        raise NotImplementedError

    @abc.abstractmethod
    def generate(self) -> list[Diff]:
        raise NotImplementedError


class BoundsCheckStrategy(abc.ABC):
    @classmethod
    def build(cls) -> t.Self:
        raise NotImplementedError

    def generate(self) -> list[Diff]:
        raise NotImplementedError

@dataclass
class TemplateBasedRepair(PatchGenerationStrategy):
    diagnosis: Diagnosis
    generators: list[TemplateGenerationStrategy]

    @classmethod
    def build(
            cls,
            diagnosis: Diagnosis,
    ) -> TemplateBasedRepair:
        generators: list[TemplateGenerationStrategy] = []
        match diagnosis.bug_type:
            case BugType.OUT_OF_BOUNDS_READ | BugType.OUT_OF_BOUNDS_WRITE:
                pass

        return cls(
            diagnosis=diagnosis,
            generators=generators
        )
