from __future__ import annotations

__all__ = ("TemplateGenerationStrategy",)

import abc
import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.functions
from loguru import logger
from sourcelocation.location import FileLocation, Location

from repairchain.models.diagnosis import Diagnosis
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:

    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.sanitizer_report import SanitizerReport
    from repairchain.models.stack_trace import StackFrame


@dataclass
class TemplateGenerationStrategy(PatchGenerationStrategy):
    """Base class for all template-based patch generation strategies."""
    report: SanitizerReport
    index: kaskara.analysis.Analysis | None

    def _fn_to_text(self, fn: kaskara.functions.Function) -> str:
        # You can get the range of the function and then plug that into ProjectSources
        project = self.diagnosis.project
        filename = fn.location.filename
        source_version = project.sources.source(filename)
        return source_version.read_chars(fn.location.location_range)

    @classmethod
    def _get_error_location(cls, diagnosis: Diagnosis) -> StackFrame | None:
        location = diagnosis.sanitizer_report.error_location
        if location is None or not location.has_lineno:
            # FIXME: I think the latter can only happen when things aren't symbolized
            # punting for now
            return None

        if location.has_funcname and not location.has_filename:  # common
            # a complete location has a filename, funcname, and lineno
            # not uncommon to have a function name but no filename
            # if we have the function name but no line number, can cross check with the
            # commit history, maybe???
            implicated_functions = diagnosis.implicated_functions_at_head
            if implicated_functions is None:
                logger.warning("unexpectedly incomplete diagnosis in template generation error location")
                return None

            for function in implicated_functions:
                if function.name == location.funcname:
                    location.filename = function.filename
                    return location
            # if that didn't work, try the nuclear option
            index = diagnosis.index_at_head
            if index is None:
                logger.warning("unexpectedly incomplete diagnosis in template generation error location")
                return None

            for function in index.functions:
                if function.name == location.funcname:
                    location.filename = function.filename
                    return location
        if location.has_funcname and location.has_filename:
            return location
        return None

    def _get_potential_declarations(self,
                                    varname: str) -> list[kaskara.statements.Statement]:
        if self.index is None:
            logger.warning("Unexpected empty index in template generation.")
            return []

        allocated_stack = self.report.alloc_stack_trace
        if allocated_stack is None:
            return []

        declaring_stmts: list[kaskara.statements.Statement] = []

        for frame in allocated_stack.frames:
            if frame.filename is None or frame.lineno is None or frame.file_line is None:
                continue
            baseloc = Location(frame.lineno, frame.offset if frame.offset is not None else 0)
            as_loc = FileLocation(frame.filename, baseloc)
            fn = self.index.functions.encloses(as_loc)
            if fn is None:
                continue
            declaring_stmts += [
                    stmt for stmt in self.index.statements
                    if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and
                    varname in stmt.declares
                ]
        if len(declaring_stmts) == 0:
            logger.info("No declaring statements found. returning empty list.")
        return declaring_stmts

    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> TemplateGenerationStrategy:
        """Builds a new instance of this strategy for the given diagnosis."""
        raise NotImplementedError
