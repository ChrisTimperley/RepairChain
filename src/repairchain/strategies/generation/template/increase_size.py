import typing as t
from dataclasses import dataclass

import kaskara
from overrides import overrides
from sourcelocation.diff import Diff

from repairchain.models.bug_type import Sanitizer
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.sanitizer_report import SanitizerReport
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

"""def get_kfence_declaration(report: SanitizerReport) -> list[kaskara.Statements.Statement]:
    

[ 1234.567890] Allocated by task 123:
[ 1234.567890]  __kmalloc_track_caller+0x1b6/0x210
[ 1234.567890]  kfence_guarded_alloc+0x8e/0x100
[ 1234.567890]  __kmalloc+0x1a6/0x210
[ 1234.567890]  my_function+0x15/0x20
[ 1234.567890]  ? my_task_function+0x50/0x70
[ 1234.567890]  my_task_function+0x50/0x70
[ 1234.567890]  kthread+0x127/0x150
[ 1234.567890]  ? set_kthread_struct+0x50/0x50
[ 1234.567890]  ret_from_fork+0x1f/0x30"""
def get_declarations(report: SanitizerReport) -> list[kaskara.Statements.Statement]:
    match report.sanitizer:
        case Sanitizer.KASAN:
            raise NotImplementedError
        case Sanitizer.KFENCE:
            raise NotImplementedError
        case Sanitizer.ASAN:
            raise NotImplementedError
        case Sanitizer.MEMSAN:
            raise NotImplementedError
        case Sanitizer.UBSAN:
            raise NotImplementedError
        case Sanitizer.JAZZER:
            raise NotImplementedError
        case Sanitizer.UNKNOWN:
            raise NotImplementedError


@dataclass
class IncreaseSizeStrategy(TemplateGenerationStrategy):
    """Suitable for array oob, outofboundsread, out of bounds write.

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.
    """

    diagnosis: Diagnosis
    declarations_to_repair: list[kaskara.Statements.Statement]
    accesses_to_repair: list[kaskara.Statements.Statement]

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # for these, we want to try to increase the size of the thing
        # or POSSIBLY decrease the size of the access.
        # So I need to know the thing that was accessed/where, and where it was declared.
        # then either modify the declaration, or
        return cls(
            diagnosis=diagnosis,
            declarations_to_repair=[],
            accesses_to_repair=[],
        )


    @overrides
    def run(self) -> list[Diff]:

        raise NotImplementedError
