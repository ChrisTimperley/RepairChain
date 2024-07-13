
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


@dataclass
class InitializeMemoryStrategy(TemplateGenerationStrategy):
    llm: LLM

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # insert call to memset, check header to make sure memset is there
        # doing this at the access for now, expediency
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    @overrides
    def run(self) -> list[Diff]:
        location = self._get_error_location()

        helper = CodeHelper(self.llm)
        head_index = self.diagnosis.index_at_head
        assert head_index is not None
        assert location is not None
        stmts_at_error_location = head_index.statements.at_line(location.file_line)
        repls: list[Diff] = []

        for stmt in stmts_at_error_location:
            stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
            fn = head_index.functions.encloses(stmt_loc)
            if fn is not None:
                fn_src = self._fn_to_text(fn)
                output = helper.help_with_memory_initialization(fn_src, stmt.content)
                for line in output.code:
                    combine = line.line + "\n" + stmt.content
                    repl = Replacement(stmt.location, combine)
                    repls.append(self.diagnosis.project.sources.replacements_to_diff([repl]))

        return repls
