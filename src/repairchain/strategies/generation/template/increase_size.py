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

@dataclass
class IncreaseSizeStrategy(TemplateGenerationStrategy):
    """Suitable for array oob, outofboundsread, out of bounds write.

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.

    KASAN has an allocated-stack
    KFENCE should have an allocated-stack
    ASAN does too -- 
    UBSAN does array OOB --- and it doesnt have the allocated stack but it does have the type
    """

    diagnosis: Diagnosis
    declarations_to_repair: list[kaskara.statements.Statement]
    accesses_to_repair: list[kaskara.statements.Statement]

    @classmethod
    def _get_overflow_location(cls, report: SanitizerReport, diagnosis: Diagnosis) -> StackFrame:
        location = report.error_location

        if not location.has_lineno():
            # FIXME: I think this can only happen when things aren't symbolized
            # punting for now
            return location
        if location.has_funcname() and not location.has_filename():  # common
            # a complete location has a filename, funcname, and lineno
            # not uncommon to have a function name but no filename
            # if we have the function name but no line number, can cross check with the
            # commit history, maybe???
            implicated_functions = diagnosis.implicated_functions_at_head
            for function in implicated_functions:
                if function.name == location.funcname:
                    location.filename = function.filename
                    return location
            # if that didn't work, try the nuclear option
            for function in diagnosis.index_at_head.functions:
                if function.name == location.funcname:
                    location.filename = function.filename
                    return location
        return location

    @classmethod
    def _get_potential_declarations(cls, location: StackFrame, diagnosis: Diagnosis) -> None:
        # location is the location of the overflow, should reference at least one variable
        # look for it in the allocation stack
        head_index = diagnosis.index_at_head
        stmts_read = frozenset([])
        for stmt in head_index.statements.at_line(location.file_line):
            stmts_read.union(frozenset(stmt.reads if hasattr(stmt, "reads") else []))
            

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # for these, we want to try to increase the size of the thing
        # or POSSIBLY decrease the size of the access.
        # So I need to know the thing that was accessed/where, and where it was declared.
        # then either modify the declaration, or
        # get the location of the out of bounds read/array access
        report = diagnosis.sanitizer_report
        location = cls._get_overflow_location(report, diagnosis)
        if not location.is_complete():  # FIXME: is it possible for us not to get a location?
            raise NotImplementedError # try to do something to grok the location
            # this will often involve reconstructing the file, since many of the
            # sanitizers report the function name but not the filename
            # so we need to find the file to have a file-line location
        head_index = diagnosis.index_at_head
        assert location is not None
        assert head_index is not None

        file_line = location.file_line
        potential_reads = frozenset([])
        for stmt in head_index.statements.at_line(file_line):
            reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
            potential_reads.union(reads)
        # potential reads should have variables that might 
        # OK the allocated stack tells me about the thread that called it
        # want to cross check the functions in there and the lines specifically 
        # in
        # dealing with asan (and in principle kfence and kasan, setting aside the issue
        # of symbolization) first


        return cls(
            diagnosis=diagnosis,
            declarations_to_repair=[],
            accesses_to_repair=[],
        )

    @overrides
    def run(self) -> list[Diff]:

        raise NotImplementedError
