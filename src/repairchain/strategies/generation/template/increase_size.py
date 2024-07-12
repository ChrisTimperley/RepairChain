import itertools
import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.functions
from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.fileline import FileLine
from sourcelocation.location import FileLocation, Location

from repairchain.actions.commit_to_diff import get_file_contents_at_commit
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.replacement import Replacement
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy


@dataclass
class IncreaseSizeStrategy(TemplateGenerationStrategy):
    """Suitable for array oob, outofboundsread, out of bounds write.

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.

    KASAN has an allocated-stack
    KFENCE should have an allocated-stack
    ASAN does too --
    UBSAN does array OOB --- and it doesnt have the allocated stack but it does have the type
    """

    diagnosis: Diagnosis
    declarations_to_repair: list[tuple[kaskara.statements.Statement, kaskara.functions.Function, FileLine, str]]
    accesses_to_repair: list[tuple[kaskara.statements.Statement, kaskara.functions.Function, FileLine, str]]

    @classmethod
    def _get_variables(cls,
                        stmt: kaskara.statements.Statement,
                        diagnosis: Diagnosis) -> frozenset[str]:
        vars_read: frozenset[str] = frozenset([])
        head_index = diagnosis.index_at_head
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
        # or POSSIBLY decrease the size of the access.
        # So I need to know the thing that was accessed/where, and where it was declared.
        # then either modify the declaration, or
        # get the location of the out of bounds read/array access
        head_index = diagnosis.index_at_head
        assert head_index is not None
        report = diagnosis.sanitizer_report
        location = cls._get_error_location(report, diagnosis)
        vars_of_interest: frozenset[str] = frozenset([])
        for statement in head_index.statements.at_line(location.file_line):
            vars_of_interest = vars_of_interest.union(cls._get_variables(statement, diagnosis))
        stmts = cls._get_potential_declarations(vars_of_interest, report, diagnosis)

        assert location is not None
        assert location.lineno is not None
        assert location.filename is not None

        baseloc = Location(location.lineno, location.offset if location.offset is not None else 0)
        as_loc = FileLocation(location.filename, baseloc)
        fn = head_index.functions.encloses(as_loc)
        assert fn is not None
        file_contents = get_file_contents_at_commit(
                    diagnosis.project.repository.active_branch.commit,
                    fn.filename,
                )
        access = head_index.statements.at_line(location.file_line)
        accesses = [(stmt, fn, location.file_line, file_contents) for stmt in access]
        assert location is not None
        assert head_index is not None
        return cls(
            diagnosis=diagnosis,
            declarations_to_repair=stmts,
            accesses_to_repair=accesses,
        )

    def _fn_to_text(self, fn: kaskara.functions.Function) -> str:
        raise NotImplementedError

    def _generate_for_statement(
        self,
        stmt: kaskara.statements.Statement,
        llm: LLM,
        diagnosis: Diagnosis,
    ) -> list[Diff]:

        # this statement should be a declaration statement, so all we need to do
        # is get a new one and replace it
        helper = CodeHelper(llm)
        head_index = diagnosis.index_at_head
        assert head_index is not None

        stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
        fn = head_index.functions.encloses(stmt_loc)
        assert fn is not None
        fn_src = self._fn_to_text(fn)
        output = helper.help_with_memory_allocation(fn_src, stmt.content)
        repls: list[Replacement] = []
        for line in output.code:
            repl = Replacement(stmt.location, line.line)
            repls.append(repl)
        return [diagnosis.project.sources.replacements_to_diff([repl]) for repl in repls]

    @overrides
    def run(self) -> list[Diff]:
        llm = LLM.from_settings(self.diagnosis.project.settings)
        diffs = [self._generate_for_statement(stmt[0], llm, self.diagnosis) for stmt in self.declarations_to_repair]

        return list(itertools.chain(*diffs))
