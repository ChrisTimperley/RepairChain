from __future__ import annotations

from repairchain.util import statements_in_function

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

    from sourcelocation.fileline import FileLine

    from repairchain.indexer import KaskaraIndexer
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.sanitizer_report import SanitizerReport
    from repairchain.models.stack_trace import StackFrame
    from repairchain.sources import ProjectSources


@dataclass
class TemplateGenerationStrategy(PatchGenerationStrategy):
    """Base class for all template-based patch generation strategies."""
    report: SanitizerReport
    index: kaskara.analysis.Analysis | None

    def _set_index(self, locations: list[StackFrame]) -> None:
        sources: ProjectSources = self.diagnosis.project.sources
        indexer: KaskaraIndexer = self.diagnosis.project.indexer
        head_commit = self.diagnosis.project.head

        filenames = [
            f.filename for f in locations if f.filename is not None and sources.exists(f.filename, head_commit)
        ]
        if not filenames:
            logger.warning("Skipping index in TemplateGeneration, no files to index.")
            return
        self.index = indexer.run(version=self.diagnosis.project.head,
                                 restrict_to_files=list(set(filenames)))

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

    def _one_frame_potential_definitions(self,
                                          varname: str,
                                          frame_line: FileLine,
                                          ) -> list[kaskara.statements.Statement]:
        if self.index is None:
            logger.warning("Unexpected empty index in template generation.")
            return []
        defining_stmts: list[kaskara.statements.Statement] = []
        for stmt in self.index.statements.at_line(frame_line):
            if not isinstance(stmt, kaskara.clang.analysis.ClangStatement):
                continue
            stmt_kind = stmt.kind
            if stmt_kind != "DeclStmt" or stmt_kind != "BinaryOperator":
                continue
            if varname in stmt.writes or varname in stmt.declares:
                defining_stmts.append(stmt)
        return defining_stmts

    def _get_potential_definitions(self,
                                    varname: str) -> list[kaskara.statements.Statement]:
        if self.index is None:
            logger.warning("Unexpected empty index in template generation.")
            return []

        allocated_stack = self.report.alloc_stack_trace

        defining_stmts: list[kaskara.statements.Statement] = []

        for frame in allocated_stack.frames:
            if frame.filename is None or frame.lineno is None or frame.file_line is None:
                continue
            baseloc = Location(frame.lineno, frame.offset if frame.offset is not None else 0)
            as_loc = FileLocation(frame.filename, baseloc)
            fn = self.index.functions.encloses(as_loc)
            if fn is None:
                continue
            defining_stmts += self._one_frame_potential_definitions(varname, frame.file_line)

        if len(defining_stmts) == 0:
            logger.warning("No declaring statements found. returning empty list.")
        return defining_stmts

    def _one_stack_frame_potential_declarations(self,
                                          varname: str,
                                          frame_line: FileLine,
                                          ) -> list[kaskara.statements.Statement]:
        if self.index is None:
            logger.warning("Unexpected empty index in template generation.")
            return []
        declaring_stmts: list[kaskara.statements.Statement] = []
        for stmt in self.index.statements.at_line(frame_line):
            if not isinstance(stmt, kaskara.clang.analysis.ClangStatement):
                continue
            stmt_kind = stmt.kind
            if stmt_kind != "DeclStmt":
                continue
            if varname in stmt.writes or varname in stmt.declares:
                declaring_stmts.append(stmt)
        return declaring_stmts

    def _one_function_potential_declarations(self,
                                          varname: str,
                                          location: StackFrame,
                                          ) -> list[kaskara.statements.Statement]:
        if self.index is None or location.lineno is None or location.filename is None:
            logger.warning("Unexpected empty index or diagnosis in template generation.")
            return []

        baseloc = Location(location.lineno, location.offset if location.offset is not None else 0)
        as_loc = FileLocation(location.filename, baseloc)
        fn = self.index.functions.encloses(as_loc)
        if fn is None:
            return []

        declaring_stmts: list[kaskara.statements.Statement] = []
        stmts_in_fn = statements_in_function(self.index, fn)
        for stmt in stmts_in_fn:
            if stmt.location.location_range.start.line > location.lineno:
                continue
            if not isinstance(stmt, kaskara.clang.analysis.ClangStatement):
                continue
            stmt_kind = stmt.kind
            if stmt_kind != "DeclStmt":
                continue
            if varname in stmt.writes or varname in stmt.declares:
                declaring_stmts.append(stmt)
        return declaring_stmts

    def _get_potential_declarations(self,
                                    error_location: StackFrame,
                                    varname: str) -> list[kaskara.statements.Statement]:
        if self.index is None:
            logger.warning("Unexpected empty index in template generation.")
            return []

        declaring_stmts: list[kaskara.statements.Statement] = []

        # try the fucntion where the erro triggerd first
        if error_location.file_line is not None:
            declaring_stmts += self._one_stack_frame_potential_declarations(varname, error_location.file_line)

        for frame in self.report.alloc_stack_trace:
            if frame.filename is None or frame.lineno is None or frame.file_line is None:
                continue
            baseloc = Location(frame.lineno, frame.offset if frame.offset is not None else 0)
            as_loc = FileLocation(frame.filename, baseloc)
            fn = self.index.functions.encloses(as_loc)
            if fn is None:
                continue
            declaring_stmts += self._one_stack_frame_potential_declarations(varname, frame.file_line)

        if len(declaring_stmts) == 0:
            logger.warning("No declaring statements found. returning empty list.")
        return declaring_stmts

    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        """Builds a new instance of this strategy for the given diagnosis."""
        raise NotImplementedError
