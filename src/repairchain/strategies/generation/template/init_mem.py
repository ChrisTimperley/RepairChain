
import typing as t
from dataclasses import dataclass

import kaskara
from overrides import overrides
from sourcelocation.diff import Diff

from repairchain.models.diagnosis import Diagnosis
from repairchain.models.sanitizer_report import StackTrace
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy


@dataclass
class InitializeMemoryStrategy(TemplateGenerationStrategy):
    diagnosis: Diagnosis
    functions_to_repair: list[kaskara.functions.Function]
    stack_trace: StackTrace

    @classmethod
    @overrides
    def applies(cls, diagnosis: Diagnosis) -> bool:
        return False

    @classmethod
    @overrides
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        raise NotImplementedError

    @overrides
    def run(self) -> list[Diff]:
        raise NotImplementedError
