import typing as t
from dataclasses import dataclass

from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.location import FileLocation

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.replacement import Replacement
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

TEMPLATE_SET_TO_MAX = """
if({varname} > 2147483647) {
    {varname} = 2147483647;
}
{stmt_code}
"""
# TODO: this is a very naive template, but we need to start somewhere


@dataclass
class IntegerOverflowStrategy(TemplateGenerationStrategy):
    llm: LLM

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    @overrides
    def applies(self) -> bool:
        match self.report.bug_type:
            case BugType.INTEGER_OVERFLOW_OR_WRAPAROUND:
                pass
            case BugType.UNSIGNED_INTEGER_OVERFLOW:
                pass
            case BugType.SIGNED_INTEGER_OVERFLOW:
                pass
            case _:
                return False
        location = self._get_error_location()
        return location is not None

    @overrides
    def run(self) -> list[Diff]:
        diffs: list[Diff] = []
        helper = CodeHelper(self.llm)
        location = self._get_error_location()
        head_index = self.diagnosis.index_at_head
        assert head_index is not None
        stmts = head_index.statements.at_line(location.file_line)
        for stmt in stmts:
            stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
            fn = head_index.functions.encloses(stmt_loc)
            if fn is None:
                continue
            fn_src = self._fn_to_text(fn)

            reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
            for varname in reads:  # would be super cool to know the type, but who has the time, honestly.
                # up cast
                output = helper.help_with_upcast_no_info(fn_src, stmt.content, varname)
                if output is not None:
                    for line in output.code:
                        repl_code = stmt.content + "\n" + line.line
                        repl = Replacement(stmt.location, repl_code)
                        diffs.append(self.diagnosis.project.sources.replacements_to_diff([repl]))

                # if the variable is > max, set to max
                # TODO: lots of other options here, but this is something
                new_code = TEMPLATE_SET_TO_MAX.format(
                    varname=varname,
                    code=stmt.content,
                )
                repl = Replacement(stmt.location, new_code)
                diffs.append(self.diagnosis.project.sources.replacements_to_diff([repl]))

        return diffs
