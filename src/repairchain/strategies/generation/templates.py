from __future__ import annotations

import abc
import itertools
import typing as t
from dataclasses import dataclass

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.diff import Diff
from repairchain.models.sanitizer_report import SanitizerReport
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    import kaskara.functions


class TemplateGenerationStrategy(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        raise NotImplementedError

    @abc.abstractmethod
    def generate(self) -> list[Diff]:
        raise NotImplementedError


def function_in_trace(stack_trace: list[SanitizerReport.StackTrace], f: kaskara.functions.Function) -> bool: 
    return any(stack_trace_ele.fname == f.name for stack_trace_ele in stack_trace)

@dataclass
class BoundsCheckStrategy(TemplateGenerationStrategy):
    funcs: list[kaskara.functions.Function]

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        report = diagnosis.project.sanitizer_report
        implicated_functions = diagnosis.implicated_functions_at_head
        condensed_trace = list(itertools.chain(*report.stack_trace.values()))
        localized_functions = [f for f in implicated_functions if function_in_trace(condensed_trace, f)] 
        return cls(funcs=localized_functions)

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
                generators.append(BoundsCheckStrategy.build(diagnosis))
            case _:
                raise NotImplementedError

        return cls(
            diagnosis=diagnosis,
            generators=generators
        )
