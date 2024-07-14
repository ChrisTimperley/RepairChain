import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.functions
from loguru import logger
from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.location import FileLocation, Location

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.replacement import Replacement
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.indexer import KaskaraIndexer

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

    These can come from: KASAN, KFENCE, ASAN, UBSAN, though UBSAN is only array oob.
    Template options are to (1) increase the size at declaration, (2) decrease the access.

    Note for review: a better version is coming this evening.
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
        if isinstance(stmt, kaskara.clang.analysis.ClangStatement):
            vars_read.union(frozenset(stmt.reads if hasattr(stmt, "reads") else []))
        if isinstance(stmt, kaskara.clang.analysis.ClangStatement) and len(vars_read) == 0:
            vars_read.union(frozenset(stmt.writes if hasattr(stmt, "writes") else []))
        return vars_read

    @classmethod
    @overrides
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # for these, we want to try to increase the size of the thing
        # or POSSIBLY decrease the size of the access; focusing on the first for now
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            index=None,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    def _generate_new_declarations(
        self,
        stmt: kaskara.statements.Statement,
    ) -> list[Diff]:
        repls: list[Diff] = []

        # this statement should be a declaration statement, so all we need to do
        # is get a new one and replace it
        helper = CodeHelper(self.llm)
        if self.index is None:
            logger.warning("Unexpected incomplete diagnosis in bounds check template.")
            return []

        stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
        fn = self.index.functions.encloses(stmt_loc)
        if fn is not None:  # I believe this is possible for global decls
            fn_src = self._fn_to_text(fn)
            output = helper.help_with_memory_allocation(fn_src, stmt.content)
            if output is not None:
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

        if self.index is None:
            logger.warning("Unexpected incomplete diagnosis in bounds check template.")
            return []

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

    @classmethod
    @overrides
    def applies(cls, diagnosis: Diagnosis) -> bool:
        match diagnosis.bug_type:
            case BugType.ARRAY_OOB:
                pass
            case BugType.OUT_OF_BOUNDS_READ:
                pass
            case BugType.OUT_OF_BOUNDS_WRITE:
                pass
            case _:
                return False
        location = cls._get_error_location(diagnosis)
        if location is None:
            return False
        if location.lineno is None or location.filename is None:
            return False
        head_index = diagnosis.index_at_head
        return head_index is not None  # sanity check

    @overrides
    def run(self) -> list[Diff]:
        location = self._get_error_location(self.diagnosis)
        if location is None or location.lineno is None or location.filename is None or location.file_line is None:
            return []
        files_to_index = [location.filename]
        files_to_index.extend(self.report.alloc_stack_trace.filenames())
        indexer: KaskaraIndexer = self.diagnosis.project.indexer
        self.index = indexer.run(version=self.diagnosis.project.head,
                                     restrict_to_files=files_to_index)

        baseloc = Location(location.lineno, location.offset if location.offset is not None else 0)
        as_loc = FileLocation(location.filename, baseloc)
        fn = self.index.functions.encloses(as_loc)
        if fn is None:
            return []

        vars_of_interest: frozenset[str] = frozenset([])
        stmts_at_error_location = self.index.statements.at_line(location.file_line)
        for statement in stmts_at_error_location:
            vars_of_interest = vars_of_interest.union(self._get_variables(statement))

        # increase size of declaration
        stmts = [stmt[0] for stmt in self._get_potential_declarations(vars_of_interest)]
        diffs: list[Diff] = []
        for stmt in stmts:
            diffs += self._generate_new_declarations(stmt)
            diffs += self._generate_decrease_access(stmt, vars_of_interest)
        # decrease potential accesses
        # this is actually kind of a wasteful way to do this, should just go one statement, var
        # at a time instead of unioning them.  But, will fix later.

        return diffs
