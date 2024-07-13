from __future__ import annotations

__all__ = ("TemplateGenerationStrategy",)

import abc
import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.functions
from loguru import logger
from sourcelocation.location import FileLocation, Location

from repairchain.actions.commit_to_diff import get_file_contents_at_commit
from repairchain.models.diagnosis import Diagnosis
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    from sourcelocation.fileline import FileLine

    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.sanitizer_report import SanitizerReport
    from repairchain.models.stack_trace import StackFrame


@dataclass
class TemplateGenerationStrategy(PatchGenerationStrategy):
    report: SanitizerReport
    """Base class for all template-based patch generation strategies."""

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
            assert implicated_functions is not None
            for function in implicated_functions:
                if function.name == location.funcname:
                    location.filename = function.filename
                    return location
            # if that didn't work, try the nuclear option
            index = diagnosis.index_at_head
            assert index is not None
            for function in index.functions:
                if function.name == location.funcname:
                    location.filename = function.filename
                    return location
        if location.has_funcname and location.has_filename:
            return location
        return None

    def _get_potential_declarations(self,
                                    vars_of_interest: frozenset[str]) -> list[tuple[kaskara.statements.Statement,
                                                                        kaskara.functions.Function, FileLine,
                                                                        str]]:
        # location is the location of the overflow, should reference at least one variable
        # look for it in the allocation stack
        # array - take whatever's in the bracket and mod it with the size
        head_index = self.diagnosis.index_at_head
        assert head_index is not None

        allocated_stack = self.report.alloc_stack_trace
        declaring_stmts: list[tuple[kaskara.statements.Statement,
                                    kaskara.functions.Function, FileLine,
                                    str]] = []

        if allocated_stack is not None:
            for frame in allocated_stack.frames:
                if frame.filename is not None and frame.lineno is not None:
                    baseloc = Location(frame.lineno, frame.offset if frame.offset is not None else 0)
                    as_loc = FileLocation(frame.filename, baseloc)
                    fn = head_index.functions.encloses(as_loc)
                    # FIXME: need kaskara to index on demand for this to work.
                    assert fn is not None
                    file_contents = get_file_contents_at_commit(
                        self.diagnosis.project.repository.active_branch.commit,
                        fn.filename,
                    )
                    if frame.file_line is not None:
                        stmts = [(stmt, fn, frame.file_line, file_contents)
                                  for stmt in head_index.statements
                                    if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and
                                    len(vars_of_interest.intersection(stmt.declares)) > 0
                                ]
                        declaring_stmts.extend(stmts)
            if len(declaring_stmts) == 0:
                logger.info("No declaring statements found. returning empty list.")
        return declaring_stmts

    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> TemplateGenerationStrategy:
        """Builds a new instance of this strategy for the given diagnosis."""
        raise NotImplementedError
