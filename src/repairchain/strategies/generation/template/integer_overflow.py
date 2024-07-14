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
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy

if t.TYPE_CHECKING:
    from repairchain.indexer import KaskaraIndexer

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
                return False
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
            type_str,
            exp_str,
            signed,
            unsigned,
        )

    def _handle_with_info(self,
                          stmts: list[kaskara.statements.Statement],
                          info_helper: OverflowHelper,
                          llm_helper: CodeHelper) -> list[Diff]:
        diffs: list[Diff] = []

        new_type = upcast_dict[info_helper.problem_type]

        for stmt in stmts:  # noqa: PLR1702
            # either the declaration itself overflows
            decls = frozenset(stmt.declares if hasattr(stmt, "declares") else [])
            if decls:  # We just need to rewrite the one statement.
                for decl in decls:
                    new_decl_code = llm_helper.help_with_upcast_decl(stmt.content,
                                                                     decl,
                                                                     info_helper.problem_type,
                                                                     new_type)
                    if new_decl_code is not None:
                        for line in new_decl_code.code:
                            complete_repl = llm_helper.help_with_upcast_expr(line.line,
                                                                             info_helper.problem_expr,
                                                                             info_helper.problem_type,
                                                                             new_type)
                            if complete_repl is not None:
                                for repl_line in complete_repl.code:
                                    repl = Replacement(stmt.location, repl_line.line)
                                    diffs.append(self.diagnosis.project.sources.replacements_to_diff([repl]))
            else:  # or we need to try to find the declaration that overflows, and rewrite two things
                writes = frozenset(stmt.writes if hasattr(stmt, "writes") else [])
                if not writes:
                    return diffs
                # step 1: rewrite the statement with the overflow
                this_repls = []
                new_overflow = llm_helper.help_with_upcast_expr(stmt.content,
                                                                info_helper.problem_expr,
                                                                info_helper.problem_type,
                                                                new_type)
                if new_overflow is not None:
                    for repl_line in new_overflow.code:
                        this_repls = [Replacement(stmt.location, repl_line.line)]

                # step 2: rewrite declarations
                decls_to_upcast = self._get_potential_declarations(writes)
                for (decl_stmt, _, _, _) in decls_to_upcast:
                    new_decl_code = llm_helper.help_with_upcast_decl(decl_stmt.content,
                                                                     decl,  # FIXME: what's the varname
                                                                     info_helper.problem_type, new_type)

                    if new_decl_code is not None:
                        for repl_line in new_decl_code.code:
                            this_repls += [Replacement(decl_stmt.location, repl_line.line)]
                diffs.append(self.diagnosis.project.sources.replacements_to_diff(this_repls))
        return diffs

    def _handle_without_info(self,
                            stmts: list[kaskara.statements.Statement],
                            llm_helper: CodeHelper) -> list[Diff]:
        if self.index is None:
            logger.warning("aborting integer overflow templates, incomplete indexing.")
            return []
        diffs: list[Diff] = []

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
                        diffs.append(self.diagnosis.project.sources.replacements_to_diff([repl]))

                # if the variable is > max, set to max
                # TODO: lots of other options here, but this is something
                new_code = TEMPLATE_SET_TO_MAX.format(
                    varname=varname,
                    code=stmt.content,
                )
                repl = Replacement(stmt.location, stmt.content + "\n" + new_code)
                diffs.append(self.diagnosis.project.sources.replacements_to_diff([repl]))
        return diffs

    @overrides
    def run(self) -> list[Diff]:
        llm_helper = CodeHelper(self.llm)
        location = self._get_error_location(self.diagnosis)
        if location is None or location.filename is None or location.file_line is None:
            return []

        files_to_index = [location.filename]
        files_to_index.extend(self.diagnosis.project.report.call_stack_trace.filenames())
        indexer: KaskaraIndexer = self.diagnosis.project.indexer
        self.index = indexer.run(version=self.diagnosis.project.head,
                                     restrict_to_files=files_to_index)

        stmts = self.index.statements.at_line(location.file_line)

        if self.diagnosis.project.report.extra_info is not None:
            info_helper = self._parse_extra_info(self.diagnosis.project.report.extra_info)
            # TODO: consider some validity checking, though this shouldn't crash
            return self._handle_with_info(list(stmts), info_helper, llm_helper)
        return self._handle_without_info(list(stmts), llm_helper)
