from __future__ import annotations

from sourcelocation.location import FileLocation

from repairchain.models.bug_type import BugType
from repairchain.models.project import ProjectKind
from repairchain.models.replacement import Replacement
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM

__all__ = ("BoundsCheckStrategy",)

import typing as t
from dataclasses import dataclass

from loguru import logger
from overrides import overrides

from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff
    from repairchain.models.sanitizer_report import StackTrace


@dataclass
class BoundsCheckStrategy(TemplateGenerationStrategy):
    llm: LLM

    @classmethod
    @overrides
    def applies(cls, diagnosis: Diagnosis) -> bool:
        match diagnosis.project.kind:
            case ProjectKind.JAVA:
                return False
            case _:
                pass
        match diagnosis.bug_type:
            case BugType.OUT_OF_BOUNDS_READ:
                pass
            case BugType.OUT_OF_BOUNDS_WRITE:
                pass
            case _:
                return False
        if diagnosis.implicated_functions_at_head is None:
            logger.warning("skipping template repair strategy (diagnosis is incomplete)")
            return False
        if not diagnosis.sanitizer_report.call_stack_trace:
            logger.warning("skipping template repair strategy (no call stack)")
            return False
        return True

    @classmethod
    @overrides
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            llm=LLM.from_settings(diagnosis.project.settings),
            index=None,
        )

    def _generate_for_statement(
        self,
        stmt: kaskara.statements.Statement,
    ) -> t.Iterator[Diff]:
        if self.index is None:
            logger.warning("Unexpected incomplete diagnosis in bounds check template.")
            return

        helper = CodeHelper(self.llm)

        stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
        fn = self.index.functions.encloses(stmt_loc)
        if fn is None:
            return
        fn_src = self._fn_to_text(fn)

        reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
        for varname in reads:  # TODO: consider type info when available
            output = helper.help_with_bounds_check(fn_src, stmt.content, varname, 5)
            if output is None:
                continue
            for line in output.code:
                repl = Replacement(stmt.location, line.line)
                diff = self.diagnosis.project.sources.replacements_to_diff([repl])
                yield diff

    def _generate_for_function(
        self,
        function: kaskara.functions.Function,
        stack_trace: StackTrace,
    ) -> t.Iterator[Diff]:
        if self.index is None:
            logger.warning("Unexpected incomplete diagnosis in bounds check template.")
            return

        for frame in stack_trace.restrict_to_function(function):
            if frame is None or frame.file_line is None:
                continue
            for statement in self.index.statements.at_line(frame.file_line):
                yield from self._generate_for_statement(statement)

    @overrides
    def run(self) -> t.Iterator[Diff]:
        both_traces = list(self.report.alloc_stack_trace.frames) + list(self.report.call_stack_trace.frames)
        self._set_index(both_traces)

        implicated_functions = self.diagnosis.implicated_functions_at_head

        if implicated_functions is None or len(self.report.call_stack_trace) == 0:
            logger.warning("incomplete diagnosis info in bounds check strategy, skipping")
            return

        logger.debug(f"implicated_functions: {len(implicated_functions)}")

        # filter the stack trace to only those functions that are implicated
        stack_trace = self.report.call_stack_trace
        stack_trace = stack_trace.restrict_to_functions(implicated_functions)

        # find the set of localized functions in the call stack trace
        functions_to_repair = [
            f for f in implicated_functions if f.name in stack_trace.functions()
        ]

        for function in functions_to_repair:
            yield from self._generate_for_function(function, stack_trace)
