import typing as t
from dataclasses import dataclass

from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.location import FileLocation

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
            fn_src = self._fn_to_text(fn) if fn is not None else ""

            reads = frozenset(stmt.reads if hasattr(stmt, "reads") else [])
            for varname in reads:  # would be super cool to know the type, but who has the time, honestly.
                # up cast
                if fn is not None:
                    output = helper.help_with_upcast(fn_src, stmt.content, varname)
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
