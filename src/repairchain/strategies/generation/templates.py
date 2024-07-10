from __future__ import annotations

import abc
import difflib
import typing as t
from dataclasses import dataclass

from loguru import logger
from sourcelocation.fileline import FileLine

from repairchain.actions.commit_to_diff import get_file_contents_at_commit
from repairchain.models.bug_type import BugType
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.sanitizer_report import SanitizerReport, StackTrace


class TemplateGenerationStrategy(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        raise NotImplementedError

    @abc.abstractmethod
    def generate(self) -> list[Diff]:
        raise NotImplementedError


def function_in_trace(stack_trace: list[SanitizerReport.StackTrace], f: kaskara.functions.Function) -> bool:
    return any(stack_trace_ele.funcname == f.name for stack_trace_ele in stack_trace)


def trace_in_function(ele_name: str, funcs: list[kaskara.functions.Function]) -> bool:
    return any(ele_name == f.name for f in funcs)


@dataclass
class BoundsCheckStrategy(TemplateGenerationStrategy):
    funcs: list[kaskara.functions.Function]
    diagnosis: Diagnosis
    stack_info: list[StackTrace]

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        report = diagnosis.project.sanitizer_report
        implicated_functions = diagnosis.implicated_functions_at_head
        logger.debug(f"implicated_functions:{len(implicated_functions)}")

        localized_functions = [f for f in implicated_functions if function_in_trace(report.stack_trace, f)]
        logger.debug(f"localized_functions: {len(localized_functions)}")

        filtered_trace = [ele for ele in report.stack_trace if trace_in_function(ele.funcname, localized_functions)]
        logger.debug(f"filtered trace:{filtered_trace}")

        return cls(funcs=localized_functions,
                   diagnosis=diagnosis,
                   stack_info=filtered_trace)

    def generate(self) -> list[Diff]:
        head_index = self.diagnosis.index_at_head
        diffs = []
        for f in self.funcs:
            logger.debug(f"func: {f}")
            lines = [ele for ele in self.stack_info if ele.funcname == f.name]
            # K need to turn the line into a file-line
            # absolute vs. relative path here is going to be A Thing, but let's start with what we have
            # and see what happens

            # FIXME: if we don't have a line, we don't have a line

            for line in lines:
                fileline = FileLine(f.filename, line.lineno)
                stmts = head_index.statements.at_line(fileline)
                file_contents = get_file_contents_at_commit(
                                    self.diagnosis.project.repository.active_branch.commit,
                                    f.filename)

                for stmt in stmts:
                    # feeling uncomfy with this, but maybe it does what I'm hoping it does
                    reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
                    for varname in reads:  # would be super cool to know the type, but who has the time, honestly.
                        source = ["if( " + varname + " > 500) { return; }\n"]
                        file_lines = file_contents.split("\n")
                        modified_lines = file_lines[:stmt.location.start.line - 1] + source + file_lines[stmt.location.start.line:]  # noqa: E501
                        modified_file_content = "\n".join(modified_lines)
                        diff = difflib.unified_diff(
                            file_contents.splitlines(keepends=True),
                            modified_file_content.splitlines(keepends=True),
                            fromfile=line.filename,
                            tofile=line.filename,
                            )
                        diff_patch = "".join(diff)
                        diffs.append(Diff.from_unidiff(diff_patch))

        return diffs


@dataclass
class TemplateBasedRepair(PatchGenerationStrategy):
    diagnosis: Diagnosis
    generators: list[TemplateGenerationStrategy]

    @classmethod
    def build(
            cls,
            diagnosis: Diagnosis,
    ) -> TemplateBasedRepair:
        generators: list[TemplateGenerationStrategy] = []
        match diagnosis.bug_type:
            case BugType.OUT_OF_BOUNDS_READ | BugType.OUT_OF_BOUNDS_WRITE:
                generators.append(BoundsCheckStrategy.build(diagnosis))
            case _:
                raise NotImplementedError

        return cls(
            diagnosis=diagnosis,
            generators=generators,
        )

    def run(self) -> list[Diff]:
        diffs = []
        for g in self.generators:
            diffs += g.generate()
        return diffs
