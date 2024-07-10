from __future__ import annotations

__all__ = ("BoundsCheckStrategy",)

import difflib
import typing as t
from dataclasses import dataclass

from loguru import logger
from overrides import overrides
from sourcelocation.fileline import FileLine

from repairchain.actions.commit_to_diff import get_file_contents_at_commit
from repairchain.models.diff import Diff
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.sanitizer_report import StackFrame


def function_in_trace(stack_trace: list[StackFrame], f: kaskara.functions.Function) -> bool:
    return any(stack_trace_ele.funcname == f.name for stack_trace_ele in stack_trace)


def trace_in_function(ele_name: str, funcs: list[kaskara.functions.Function]) -> bool:
    return any(ele_name == f.name for f in funcs)


@dataclass
class BoundsCheckStrategy(TemplateGenerationStrategy):
    funcs: list[kaskara.functions.Function]
    diagnosis: Diagnosis
    stack_info: list[StackFrame]

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        report = diagnosis.project.sanitizer_report
        implicated_functions = diagnosis.implicated_functions_at_head
        logger.debug(f"implicated_functions:{len(implicated_functions)}")

        localized_functions = [f for f in implicated_functions if function_in_trace(report.stack_trace, f)]
        logger.debug(f"localized_functions: {len(localized_functions)}")

        # filter the trace to only those lines that relate to the localized functions
        filtered_trace = [
            element for element in report.stack_trace if trace_in_function(element.funcname, localized_functions)
        ]
        logger.debug(f"filtered trace:{filtered_trace}")

        return cls(
            funcs=localized_functions,
            diagnosis=diagnosis,
            stack_info=filtered_trace,
        )

    def _generate_for_statement(
        self,
        stmt: kaskara.statements.Statement,
        line: FileLine,
        file_contents: str,
    ) -> list[Diff]:
        diffs: list[Diff] = []

        # feeling uncomfy with this, but maybe it does what I'm hoping it does
        reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
        for varname in reads:  # would be super cool to know the type, but who has the time, honestly.
            source = ["if( " + varname + " > 500) { return; }\n"]
            file_lines = file_contents.split("\n")
            modified_lines = file_lines[:stmt.location.start.line - 1] + source + file_lines[stmt.location.start.line:]
            modified_file_content = "\n".join(modified_lines)
            unidiff = "".join(difflib.unified_diff(
                file_contents.splitlines(keepends=True),
                modified_file_content.splitlines(keepends=True),
                fromfile=line.filename,
                tofile=line.filename,
            ))
            diff = Diff.from_unidiff(unidiff)
            diffs.append(diff)

        return diffs

    def _generate_for_function(self, function: kaskara.functions.Function) -> list[Diff]:
        diffs: list[Diff] = []
        logger.debug(f"generating bounds check repairs in function: {function}")
        head_index = self.diagnosis.index_at_head
        lines = [element for element in self.stack_info if element.funcname == function.name]

        file_contents = get_file_contents_at_commit(
            self.diagnosis.project.repository.active_branch.commit,
            function.filename,
        )

        # K need to turn the line into a file-line
        # absolute vs. relative path here is going to be A Thing, but let's start with what we have
        # and see what happens
        #
        # FIXME: if we don't have a line, we don't have a line
        for line in lines:
            fileline = FileLine(function.filename, line.lineno)
            for statement in head_index.statements.at_line(fileline):
                diffs += self._generate_for_statement(statement, fileline, file_contents)

        return diffs

    @overrides
    def run(self) -> list[Diff]:
        diffs: list[Diff] = []
        for function in self.funcs:
            diffs += self._generate_for_function(function)
        return diffs
