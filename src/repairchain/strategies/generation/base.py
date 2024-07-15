from __future__ import annotations

from dataclasses import dataclass

__all__ = ("PatchGenerationStrategy",)

import abc
import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff


@dataclass
class PatchGenerationStrategy(abc.ABC):
    diagnosis: Diagnosis

    def describe(self) -> str:
        return self.__class__.__name__

    @abc.abstractmethod
    def run(self) -> t.Iterator[Diff]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def applies(cls, diagnosis: Diagnosis) -> bool:
        raise NotImplementedError
