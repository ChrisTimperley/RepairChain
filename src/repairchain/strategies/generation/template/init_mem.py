
import typing as t
from dataclasses import dataclass

from loguru import logger
from overrides import overrides
from sourcelocation.diff import Diff
from sourcelocation.fileline import FileLine
from sourcelocation.location import FileLocation

from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.project import ProjectKind
from repairchain.models.replacement import Replacement
from repairchain.strategies.generation.llm.helper_code import CodeHelper
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.template.base import TemplateGenerationStrategy


@dataclass
class InitializeMemoryStrategy(TemplateGenerationStrategy):
    llm: LLM

    @classmethod
    @overrides
    def build(cls, diagnosis: Diagnosis) -> t.Self:
        # insert call to memset, check header to make sure memset is there
        # doing this at the access for now, expediency
        return cls(
            diagnosis=diagnosis,
            report=diagnosis.sanitizer_report,
            index=None,
            llm=LLM.from_settings(diagnosis.project.settings),
        )

    @classmethod
    @overrides
    def applies(cls, diagnosis: Diagnosis) -> bool:
        match diagnosis.project.kind:
            case ProjectKind.JAVA:
                return False
            case _:
                pass
        match diagnosis.sanitizer_report.bug_type:
            case BugType.INVALID_FREE:
                pass
            case BugType.LOAD_UNINIT_VALUE:
                pass
            case _:
                return False
        location = cls._get_error_location(diagnosis)
        return location is not None

    def _generate_for_one_frame(self,
                                error_stmt_str: str,
                                fn_src: str,
                                frame_line: FileLine,
                                helper: CodeHelper) -> t.Iterator[Diff]:
        """Generate replacements for one frame in the allocation stack.

        error_stmt_str refers to the statement at the error location.
        """
        if self.index is None:
            return

        stmts_at_frame = self.index.statements.at_line(frame_line)
        for alloc_stmt in stmts_at_frame:
            output = helper.help_with_memory_initialization(fn_src, error_stmt_str, alloc_stmt.content, 2)

            if output is None:
                continue
            for line in output.code:
                replacement_str = alloc_stmt.content + "\n" + line.line
                repl = Replacement(alloc_stmt.location, replacement_str)
                yield self.diagnosis.project.sources.replacements_to_diff([repl])

    @overrides
    def run(self) -> t.Iterator[Diff]:
        location = self._get_error_location(self.diagnosis)

        if location is None or location.file_line is None:
            logger.warning("Skipping InitMemTemplate, cannot index empty location.")
            return

        frames_to_consider = list(self.report.alloc_stack_trace.frames)
        frames_to_consider.append(location)
        self._set_index(frames_to_consider)
        if self.index is None:
            logger.warning("Skipping InitMemTemplate, failed to index.")
            return

        helper = CodeHelper(self.llm)

        stmts_at_error_location = self.index.statements.at_line(location.file_line)

        for stmt in stmts_at_error_location:
            stmt_loc = FileLocation(stmt.location.filename, stmt.location.start)
            fn = self.index.functions.encloses(stmt_loc)
            if fn is None:
                continue
            fn_src = self._fn_to_text(fn)
            for frame in frames_to_consider:
                if frame.file_line is None:
                    continue
                yield from self._generate_for_one_frame(stmt.content, fn_src, frame.file_line, helper)
