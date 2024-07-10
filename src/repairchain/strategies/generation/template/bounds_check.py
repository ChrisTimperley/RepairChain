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
    from repairchain.models.sanitizer_report import StackTrace


@dataclass
class BoundsCheckStrategy(TemplateGenerationStrategy):
    diagnosis: Diagnosis
    functions_to_repair: list[kaskara.functions.Function]
    stack_trace: StackTrace

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        report = diagnosis.project.sanitizer_report

        implicated_functions = diagnosis.implicated_functions_at_head
        logger.debug(f"implicated_functions:{len(implicated_functions)}")

        # filter the stack trace to only those functions that are implicated
        assert report.stack_trace
        stack_trace = report.stack_trace
        stack_trace = stack_trace.restrict_to_functions(implicated_functions)
        logger.debug(f"filtered stack trace: {stack_trace}")

        # find the set of localized functions
        functions_in_trace = stack_trace.functions()
        localized_functions = [
            f for f in implicated_functions if f.name in functions_in_trace
        ]
        logger.debug(f"localized_functions: {len(localized_functions)}")

        return cls(
            diagnosis=diagnosis,
            functions_to_repair=list(localized_functions),
            stack_trace=stack_trace,
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
        lines = [element for element in self.stack_trace if element.funcname == function.name]

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
        for function in self.functions_to_repair:
            diffs += self._generate_for_function(function)
        return diffs