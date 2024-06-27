from __future__ import annotations

from repairchain.strategies.generation.base import PatchGenerationStrategy

import abc
import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff


class CommitDD(PatchGenerationStrategy): 
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        raise NotImplementedError

    @abc.abstractmethod
    def run(self) -> list[Diff]:
        raise NotImplementedError
