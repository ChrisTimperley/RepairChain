from __future__ import annotations

from sourcelocation.location import FileLocation

from repairchain.models.bug_type import BugType, Sanitizer
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

    @overrides
    def applies(self) -> bool:
        # Caveat: CLG THINKS this is all the conditions
        if self.diagnosis.implicated_functions_at_head is None:
            return False
        if not self.diagnosis.sanitizer_report.call_stack_trace:
            return False
        match self.diagnosis.sanitizer_report.sanitizer:
            case Sanitizer.MEMSAN:
                return False
            case Sanitizer.JAZZER:
                return False
            case Sanitizer.UBSAN:
                return False
            case _:
                pass
        match self.diagnosis.bug_type:
            case BugType.OUT_OF_BOUNDS_READ:
                return True
            case BugType.OUT_OF_BOUNDS_WRITE:
                return True
            case _:
                return False

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.project.sanitizer_report,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    def _generate_for_statement(
        self,
        stmt: kaskara.statements.Statement,
    ) -> list[Diff]:
        diffs: list[Diff] = []
        helper = CodeHelper(self.llm)

        head_index = self.diagnosis.index_at_head
        assert head_index is not None

        stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
        fn = head_index.functions.encloses(stmt_loc)
        if fn is not None:
            fn_src = self._fn_to_text(fn)

            reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
            for varname in reads:  # would be super cool to know the type, but who has the time, honestly.
                output = helper.help_with_bounds_check(fn_src, stmt.content, varname)
                for line in output.code:
                    repl = Replacement(stmt.location, line.line)
                    diffs.append(self.diagnosis.project.sources.replacements_to_diff([repl]))
        return diffs

    def _generate_for_function(self, function: kaskara.functions.Function, stack_trace: StackTrace) -> list[Diff]:
        diffs: list[Diff] = []
        logger.debug(f"generating bounds check repairs in function: {function}")
        head_index = self.diagnosis.index_at_head
        assert head_index is not None

        for frame in stack_trace.restrict_to_function(function):
            for statement in head_index.statements.at_line(frame.file_line):
                diffs += self._generate_for_statement(statement)

        return diffs

    @overrides
    def run(self) -> list[Diff]:
        if not self.applies():
            return []
        implicated_functions = self.diagnosis.implicated_functions_at_head
        assert implicated_functions is not None
        assert self.report.call_stack_trace

        logger.debug(f"implicated_functions: {len(implicated_functions)}")

        # filter the stack trace to only those functions that are implicated
        stack_trace = self.report.call_stack_trace
        stack_trace = stack_trace.restrict_to_functions(implicated_functions)
        logger.debug(f"filtered stack trace: {stack_trace}")

        # find the set of localized functions
        functions_in_trace = stack_trace.functions()
        functions_to_repair = [
            f for f in implicated_functions if f.name in functions_in_trace
        ]
        logger.debug(f"localized_functions: {len(functions_to_repair)}")

        diffs: list[Diff] = []
        for function in functions_to_repair:
            diffs += self._generate_for_function(function, stack_trace)
        return diffs
