from __future__ import annotations

__all__ = ("PatchGenerationStrategy",)

import abc
import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff


class PatchGenerationStrategy(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        raise NotImplementedError

    @abc.abstractmethod
    def run(self) -> list[Diff]:
        raise NotImplementedError
