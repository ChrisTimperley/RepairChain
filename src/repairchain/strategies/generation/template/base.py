__all__ = ("TemplateGenerationStrategy",)

import kaskara
import kaskara.functions
from sourcelocation.fileline import FileLine
from sourcelocation.location import FileLocation, Location

from repairchain.actions.commit_to_diff import get_file_contents_at_commit
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.sanitizer_report import SanitizerReport
from repairchain.models.stack_trace import StackFrame
from repairchain.strategies.generation.base import PatchGenerationStrategy


class TemplateGenerationStrategy(PatchGenerationStrategy):
    """Base class for all template-based patch generation strategies."""

    def _fn_to_text(self, diagnosis: Diagnosis, fn: kaskara.functions.Function) -> str:
        # You can get the range of the function and then plug that into ProjectSources
        project = diagnosis.project
        filename = fn.location.filename
        source_version = project.sources.source(filename)
        return source_version.read_chars(fn.location.location_range)

    @classmethod
    def _get_error_location(cls, report: SanitizerReport, diagnosis: Diagnosis) -> StackFrame:
        location = report.error_location
        assert location is not None
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
        return location

    @classmethod
    def _get_potential_declarations(cls,
                                    vars_of_interest: frozenset[str],
                                    report: SanitizerReport,
                                    diagnosis: Diagnosis) -> list[tuple[kaskara.statements.Statement,
                                                                        kaskara.functions.Function, FileLine,
                                                                        str]]:
        # location is the location of the overflow, should reference at least one variable
        # look for it in the allocation stack
        # array - take whatever's in the bracket and mod it with the size
        head_index = diagnosis.index_at_head
        assert head_index is not None

        allocated_stack = report.alloc_stack_trace
        declaring_stmts: list[tuple[kaskara.statements.Statement,
                                    kaskara.functions.Function, FileLine,
                                    str]] = []

        for frame in allocated_stack.frames:
            if frame.is_complete():
                # these are both true if the if check is true
                assert frame.filename is not None
                assert frame.lineno is not None
                baseloc = Location(frame.lineno, frame.offset if frame.offset is not None else 0)
                as_loc = FileLocation(frame.filename, baseloc)
                fn = head_index.functions.encloses(as_loc)
                # FIXME: need kaskara to index on demand for this to work.
                assert fn is not None
                file_contents = get_file_contents_at_commit(
                    diagnosis.project.repository.active_branch.commit,
                    fn.filename,
                )
                stmts = [(stmt, fn, frame.file_line, file_contents)
                          for stmt in head_index.statements
                            if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and
                            len(vars_of_interest.intersection(stmt.declares)) > 0
                        ]
                declaring_stmts.extend(stmts)
        if len(declaring_stmts) == 0:
            raise NotImplementedError  # try something else.  UBSan especially is going to be a problem here
        return declaring_stmts
