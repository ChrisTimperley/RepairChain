import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.functions
from loguru import logger
from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.location import FileLocation

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.project import ProjectKind
from repairchain.models.replacement import Replacement
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

TEMPLATE_DECREASE_VAR1 = """
{varname} = {varname} - 1;
{stmt_code}
"""

TEMPLATE_DECREASE_VAR2 = """
{varname} = 0;
{stmt_code}
"""


@dataclass
class IncreaseSizeStrategy(TemplateGenerationStrategy):
    """Suitable for array oob, outofboundsread, out of bounds write.

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.

    Note for review: a better version is coming this evening.
    KASAN has an allocated-stack
    KFENCE should have an allocated-stack
    ASAN does too --
    UBSAN does array OOB --- and it doesnt have the allocated stack but it does have the type
    """
    llm: LLM

    def _get_variables_written(
        self,
        stmt: kaskara.statements.Statement,
    ) -> frozenset[str]:
        if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and hasattr(stmt, "writes"):
            return frozenset(stmt.writes)
        return frozenset()

    def _get_variables_read(
        self,
        stmt: kaskara.statements.Statement,
    ) -> frozenset[str]:
        if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and hasattr(stmt, "read"):
            return frozenset(stmt.read)
        return frozenset()

    @classmethod
    @overrides
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # for these, we want to try to increase the size of the thing
        # or POSSIBLY decrease the size of the access; focusing on the first for now
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            index=None,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    def _generate_new_declarations(
        self,
        stmt: kaskara.statements.Statement,
        varname: str,
    ) -> t.Iterator[Diff]:
        # this statement should be a declaration statement, so all we need to do
        # is get a new one and replace it
        helper = CodeHelper(self.llm)
        if self.index is None:
            logger.warning("Unexpected incomplete diagnosis in bounds check template.")
            return

        stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
        fn = self.index.functions.encloses(stmt_loc)
        if fn is None:  # I believe this is possible for global decls
            return
        fn_src = self._fn_to_text(fn)
        output = helper.help_with_memory_allocation(fn_src, stmt.content, varname, 3)
        if output is None:
            return
        for line in output.code:
            repl = Replacement(stmt.location, line.line)
            yield self.diagnosis.project.sources.replacements_to_diff([repl])

    def _generate_decrease_access(
        self,
        stmt: kaskara.statements.Statement,
        varname: str,
    ) -> t.Iterator[Diff]:
        # current statement is at the error location
        # set a read variable to 0, or itself -1
        # prepend to error location
        if self.index is None:
            logger.warning("Unexpected incomplete diagnosis in increase size template.")
            return

        new_code1 = TEMPLATE_DECREASE_VAR1.format(
            varname=varname,
            stmt_code=stmt.content,
        )
        new_code2 = TEMPLATE_DECREASE_VAR2.format(
            varname=varname,
            stmt_code=stmt.content,
        )
        repl1 = Replacement(stmt.location, new_code1)
        repl2 = Replacement(stmt.location, new_code2)
        yield self.diagnosis.project.sources.replacements_to_diff([repl1])
        yield self.diagnosis.project.sources.replacements_to_diff([repl2])

    @classmethod
    @overrides
    def applies(cls, diagnosis: Diagnosis) -> bool:
        match diagnosis.project.kind:
            case ProjectKind.JAVA:
                return False
            case _:
                pass
        match diagnosis.bug_type:
            case BugType.ARRAY_OOB:
                pass
            case BugType.OUT_OF_BOUNDS_READ:
                pass
            case BugType.OUT_OF_BOUNDS_WRITE:
                pass
            case _:
                return False
        location = cls._get_error_location(diagnosis)
        return location is not None

    @overrides
    def run(self) -> t.Iterator[Diff]:
        both_traces = list(self.report.alloc_stack_trace.frames) + list(self.report.call_stack_trace.frames)
        self._set_index(both_traces)

        if self.index is None:
            logger.warning("Unexpected failed index in IncreaseSize, skipping")
            return

        # either reallocate accessed/declared buffers
        for frame in self.diagnosis.sanitizer_report.alloc_stack_trace:
            if frame.file_line is None:
                continue
            stmts_at_alloc_frame = self.index.statements.at_line(frame.file_line)
            for stmt in stmts_at_alloc_frame:
                for varname in self._get_variables_written(stmt):
                    yield from self._generate_new_declarations(stmt, varname)

        # or decrease the access to a buffer
        for frame in self.diagnosis.sanitizer_report.call_stack_trace:
            if frame.file_line is None:
                continue
            stmts_at_call_frame = self.index.statements.at_line(frame.file_line)
            for stmt in stmts_at_call_frame:
                for varname in self._get_variables_read(stmt):
                    yield from self._generate_decrease_access(stmt, varname)
