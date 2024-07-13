from __future__ import annotations

__all__ = ("PatchGenerationStrategy",)

import abc
import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff


class PatchGenerationStrategy(abc.ABC):

    @abc.abstractmethod
    def run(self) -> list[Diff]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def applies(cls, diagnosis: Diagnosis) -> bool:
        raise NotImplementedError
