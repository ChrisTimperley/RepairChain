import typing as t
from dataclasses import dataclass

import kaskara
from overrides import overrides
from sourcelocation.diff import Diff

from repairchain.actions.commit_to_diff import get_file_contents_at_commit
from repairchain.models.bug_type import Sanitizer
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.sanitizer_report import SanitizerReport
from repairchain.models.stack_trace import StackFrame
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy


def get_declarations(report: SanitizerReport) -> list[kaskara.statements.Statement]:
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


def is_valid(location: StackFrame | None) -> bool:
    raise NotImplementedError

@dataclass
class IncreaseSizeStrategy(TemplateGenerationStrategy):
    """Suitable for array oob, outofboundsread, out of bounds write.

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.
    """

    diagnosis: Diagnosis
    declarations_to_repair: list[kaskara.statements.Statement]
    accesses_to_repair: list[kaskara.statements.Statement]

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # for these, we want to try to increase the size of the thing
        # or POSSIBLY decrease the size of the access.
        # So I need to know the thing that was accessed/where, and where it was declared.
        # then either modify the declaration, or
        # get the location of the out of bounds read/array access
        report = diagnosis.sanitizer_report
        location = report.error_location
        if not is_valid(location):  # FIXME: is it possible for us not to get a location?
            pass # do something to grok the location
            # this will often involve reconstructing the file, since many of the
            # sanitizers report the function name but not the filename
            # so we need to find the file to have a file-line location
        head_index = diagnosis.index_at_head
        assert location is not None
        assert head_index is not None
        
        file_line = location.file_line
        for stmt in head_index.statements.at_line(file_line):
            reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])

        return cls(
            diagnosis=diagnosis,
            declarations_to_repair=[],
            accesses_to_repair=[],
        )

    @overrides
    def run(self) -> list[Diff]:

        raise NotImplementedError
