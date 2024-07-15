import typing as t
from dataclasses import dataclass

import kaskara
from loguru import logger
from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.location import FileLocation

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.replacement import Replacement
from repairchain.models.stack_trace import StackFrame
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

# options:
# the above, set to dumb max, can maybe vary by type
# change declaration of integer that is overflowing
# downcast the expression that is overflowing
# UBSan gives information that can be parsed out, try to use it!


@dataclass
class OverflowHelper:
    problem_type: str
    problem_expr: str
    signed: bool
    unsigned: bool


upcast_dict = {
    "char": "int",
    "short": "int",
    "int": "long",
    "unsigned int": "unsigned long",
    "long": "long long",
}


@dataclass
class IntegerOverflowStrategy(TemplateGenerationStrategy):
    llm: LLM

    @classmethod
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            index=None,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    @classmethod
    @overrides
    def applies(cls, diagnosis: Diagnosis) -> bool:
        match diagnosis.sanitizer_report.bug_type:
            case BugType.INTEGER_OVERFLOW_OR_WRAPAROUND:
                pass
            case BugType.UNSIGNED_INTEGER_OVERFLOW:
                pass
            case BugType.SIGNED_INTEGER_OVERFLOW:
                pass
            case _:
                return True
        location = cls._get_error_location(diagnosis)
        return location is not None

    def _parse_extra_info(self, extra_info: str) -> OverflowHelper:
        # runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
        exp_str = ""
        type_str = ""
        signed = False
        unsigned = False
        if "unsigned" in extra_info:
            unsigned = True
        elif "signed" in extra_info:
            signed = True

        if ": " in extra_info:
            _, _, rhs = extra_info.partition(": ")  # rhs should start with overflowed expression
            if " cannot " in rhs:
                exp_str, _, rhs = rhs.partition(" cannot ")
                if "type " in rhs:
                    _, _, type_str = rhs.partition("type ")
                    type_str = type_str.replace("'", "")
        return OverflowHelper(
            problem_type=type_str,
            problem_expr=exp_str,
            signed=signed,
            unsigned=unsigned,
        )

    def _generate_diffs_for_decls(
        self,
        stmt: kaskara.statements.Statement,
        declared_var: str,
        info_helper: OverflowHelper,
        llm_helper: CodeHelper,
    ) -> t.Iterator[Diff]:
        new_type = upcast_dict[info_helper.problem_type]
        new_decl_code = llm_helper.help_with_upcast_decl(
            stmt.content,
            declared_var,
            info_helper.problem_type,
            new_type,
        )
        if new_decl_code is None:
            return

        for line in new_decl_code.code:
            complete_repl = llm_helper.help_with_upcast_expr(
                line.line,
                info_helper.problem_expr,
                info_helper.problem_type,
                new_type,
            )
            if complete_repl is None:
                continue
            for repl_line in complete_repl.code:
                repl = Replacement(stmt.location, repl_line.line)
                diff = self.diagnosis.project.sources.replacements_to_diff([repl])
                yield diff

    def _generate_diffs_for_not_decls(
        self,
        stmt: kaskara.statements.Statement,
        varname: str,
        error_location: StackFrame,
        info_helper: OverflowHelper,
        llm_helper: CodeHelper,
    ) -> t.Iterator[Diff]:
        new_type = upcast_dict[info_helper.problem_type]

        # step 1: get rewrites for the overflow
        new_expr_upcast = llm_helper.help_with_upcast_expr(
            stmt.content,
            info_helper.problem_expr,
            info_helper.problem_type,
            new_type,
        )

        if new_expr_upcast is None:
            return

        # step 2: get rewrites for the declarations
        for decl_stmt in self._get_potential_declarations(error_location, varname):
            new_decl_code = llm_helper.help_with_upcast_decl(
                decl_stmt.content,
                varname,
                info_helper.problem_type,
                new_type,
            )

            if new_decl_code is None:
                continue

            for new_expr in new_expr_upcast.code:
                for new_decl_stmt in new_decl_code.code:
                    combined_repl = [
                        Replacement(stmt.location, new_expr.line),
                        Replacement(decl_stmt.location, new_decl_stmt.line),
                    ]

                    diff = self.diagnosis.project.sources.replacements_to_diff(combined_repl)
                    yield diff

    def _handle_with_info(
        self,
        stmts: list[kaskara.statements.Statement],
        error_location: StackFrame,
        info_helper: OverflowHelper,
        llm_helper: CodeHelper,
    ) -> t.Iterator[Diff]:
        for stmt in stmts:
            # either the declaration itself overflows
            if not isinstance(stmt, kaskara.clang.analysis.ClangStatement):
                continue
            decls = frozenset(stmt.declares if hasattr(stmt, "declares") else [])
            if decls:  # ...so we just need to rewrite the one statement.
                for decl in decls:
                    yield from self._generate_diffs_for_decls(stmt, decl, info_helper, llm_helper)
            else:  # or we need to try to find the declaration that overflows, and rewrite two things
                writes = frozenset(stmt.writes if hasattr(stmt, "writes") else [])
                if not writes:
                    continue
                for written_var in writes:
                    yield from self._generate_diffs_for_not_decls(
                        stmt,
                        written_var,
                        error_location,
                        info_helper,
                        llm_helper,
                    )

    def _handle_without_info(
        self,
        stmts: list[kaskara.statements.Statement],
        llm_helper: CodeHelper,
    ) -> t.Iterator[Diff]:
        if self.index is None:
            logger.warning("aborting integer overflow templates, incomplete indexing.")
            return

        for stmt in stmts:
            stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
            fn = self.index.functions.encloses(stmt_loc)
            if fn is None:
                continue
            fn_src = self._fn_to_text(fn)

            writes = frozenset(stmt.writes if hasattr(stmt, "writes") else [])
            for varname in writes:  # would be super cool to know the type, but who has the time, honestly.
                # up cast
                output = llm_helper.help_with_upcast_no_info(fn_src, stmt.content, varname)
                if output is not None:
                    for line in output.code:
                        repl = Replacement(stmt.location, line.line)
                        diff = self.diagnosis.project.sources.replacements_to_diff([repl])
                        yield diff

                # if the variable is > max, set to max
                # TODO: lots of other options here, but this is something
                new_code = TEMPLATE_SET_TO_MAX.format(
                    varname=varname,
                    code=stmt.content,
                )
                repl = Replacement(stmt.location, stmt.content + "\n" + new_code)
                diff = self.diagnosis.project.sources.replacements_to_diff([repl])
                yield diff

    @overrides
    def run(self) -> t.Iterator[Diff]:
        llm_helper = CodeHelper(self.llm)
        location = self._get_error_location(self.diagnosis)
        if location is None or location.file_line is None:
            logger.warning("Inadequate location information in IntegerOverflowStrategy, skipping")
            return

        to_index = list(self.report.alloc_stack_trace.frames) + list(self.report.call_stack_trace.frames) + [location]
        self._set_index(to_index)

        if self.index is None:
            logger.warning("Unexpected failed index in IntegerOverflow, skipping")
            return

        stmts = self.index.statements.at_line(location.file_line)

        if self.report.extra_info is not None:
            info_helper = self._parse_extra_info(self.report.extra_info)
            # TODO: consider some validity checking, though this shouldn't crash at least
            yield from self._handle_with_info(list(stmts), location, info_helper, llm_helper)
        else:
            yield from self._handle_without_info(list(stmts), llm_helper)
