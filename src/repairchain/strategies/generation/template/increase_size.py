import itertools
import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.functions
from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.location import FileLocation, Location

from repairchain.models.diagnosis import Diagnosis
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

    Array handling is poor.

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.

    KASAN has an allocated-stack
    KFENCE should have an allocated-stack
    ASAN does too --
    UBSAN does array OOB --- and it doesnt have the allocated stack but it does have the type
    """
    llm: LLM

    def _get_variables(self,
                        stmt: kaskara.statements.Statement,
                       ) -> frozenset[str]:
        vars_read: frozenset[str] = frozenset([])
        head_index = self.diagnosis.index_at_head
        assert head_index is not None
        # TODO: filter variables by type to cut it down
        if isinstance(stmt, kaskara.clang.analysis.ClangStatement):
            vars_read.union(frozenset(stmt.reads if hasattr(stmt, "reads") else []))
        if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and len(vars_read) == 0:
            vars_read.union(frozenset(stmt.writes if hasattr(stmt, "writes") else []))
        return vars_read

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # for these, we want to try to increase the size of the thing
        # or POSSIBLY decrease the size of the access; focusing on the first for now
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    def _generate_new_declarations(
        self,
        stmt: kaskara.statements.Statement,
    ) -> list[Diff]:

        # this statement should be a declaration statement, so all we need to do
        # is get a new one and replace it
        helper = CodeHelper(self.llm)
        head_index = self.diagnosis.index_at_head
        assert head_index is not None

        stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
        fn = head_index.functions.encloses(stmt_loc)
        assert fn is not None
        fn_src = self._fn_to_text(fn)
        output = helper.help_with_memory_allocation(fn_src, stmt.content)
        repls: list[Diff] = []
        for line in output.code:
            repl = Replacement(stmt.location, line.line)
            repls.append(self.diagnosis.project.sources.replacements_to_diff([repl]))
        return repls

    def _generate_decrease_access(
        self,
        stmt: kaskara.statements.Statement,
        vars_of_interest: frozenset[str],
    ) -> list[Diff]:
        # current statement is at the error location
        # set a read variable to 0, or itself -1
        # prepend to error location
        repls: list[Diff] = []

        head_index = self.diagnosis.index_at_head
        assert head_index is not None
        for varname in vars_of_interest:
            new_code1 = TEMPLATE_DECREASE_VAR1.format(
                        varname=varname,
                        code=stmt.content,
                    )
            new_code2 = TEMPLATE_DECREASE_VAR2.format(
                        varname=varname,
                        code=stmt.content,
                    )
            repl1 = Replacement(stmt.location, new_code1)
            repl2 = Replacement(stmt.location, new_code2)
            repls.append(self.diagnosis.project.sources.replacements_to_diff([repl1]))  # noqa: FURB113
            repls.append(self.diagnosis.project.sources.replacements_to_diff([repl2]))
        return repls

    @overrides
    def run(self) -> list[Diff]:
        location = self._get_error_location()
        head_index = self.diagnosis.index_at_head
        assert head_index is not None

        assert location is not None
        assert location.lineno is not None
        assert location.filename is not None

        baseloc = Location(location.lineno, location.offset if location.offset is not None else 0)
        as_loc = FileLocation(location.filename, baseloc)
        fn = head_index.functions.encloses(as_loc)
        assert fn is not None
        # access = head_index.statements.at_line(location.file_line)
        # accesses = [(stmt, fn, location.file_line, file_contents) for stmt in access]

        vars_of_interest: frozenset[str] = frozenset([])
        stmts_at_error_location = head_index.statements.at_line(location.file_line)
        for statement in stmts_at_error_location:
            vars_of_interest = vars_of_interest.union(self._get_variables(statement))

        # increase size of declaration
        stmts = [stmt[0] for stmt in self._get_potential_declarations(vars_of_interest)]
        diffs = [self._generate_new_declarations(stmt) for stmt in stmts]
        # decrease potential accesses
        # this is actually kind of a wasteful way to do this, should just go one statement, var
        # at a time instead of unioning them.  But, will fix later.

        diffs += [self._generate_decrease_access(stmt, vars_of_interest) for stmt in stmts]
        return list(itertools.chain(*diffs))
