from __future__ import annotations

import difflib
import re
import typing as t
from dataclasses import dataclass

import openai
from loguru import logger

from repairchain.actions import commit_to_diff
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy
from repairchain.strategies.generation.llm.context import create_context_all_files_git_diff

__all__ = ("SimpleYolo",)

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis


@dataclass
class FileLines:
    begin: int
    end: int


@dataclass
class RepairedFileContents:
    filename: str
    function_name: str
    code: str


@dataclass
class SimpleYolo(PatchGenerationStrategy):
    diagnosis: Diagnosis
    model: str
    litellm_url: str
    master_key: str
    diff: Diff
    files: dict[str, str]

    @classmethod
    def build(
        cls,
        diagnosis: Diagnosis,
    ) -> SimpleYolo:
        # FIXME these are hardcoded!
        model = "oai-gpt-4o"
        # model = "oai-gpt-3.5-turbo"
        litellm_url = "http://0.0.0.0:4000"
        master_key = "sk-1234"

        diff = commit_to_diff.commit_to_diff(diagnosis.project.triggering_commit)

        # FIXME obtain the contents of relevant files
        files = commit_to_diff.commit_to_files(diagnosis.project.head, diff)

        return cls(
            diagnosis=diagnosis,
            model=model,
            files=files,
            diff=diff,
            litellm_url=litellm_url,
            master_key=master_key,
        )

    @classmethod
    def _extract_file_repairs(cls, output: str) -> list[RepairedFileContents]:
        """Extracts candidate file repairs from a given LLM output."""
        pattern = re.compile(
            r"BEGIN BUG FIX\n"              # Match "BEGIN BUG FIX" followed by a newline
            r"\d+\n"                        # Match one or more digits followed by a newline
            r"BEGIN MODIFIED FILENAME\n(.*?)\n"  # Match "BEGIN MODIFIED FILENAME" followed by any text and a newline
            r"END MODIFIED FILENAME\n"           # Match "END MODIFIED FILENAME" followed by a newline
            # Match "BEGIN MODIFIED FUNCTION NAME" followed by any text and a newline
            r"BEGIN MODIFIED FUNCTION NAME\n(.*?)\n"
            r"END MODIFIED FUNCTION NAME\n"           # Match "END MODIFIED FUNCTION NAME" followed by a newline
            r"BEGIN MODIFIED CODE\n(.*?)\n"           # Match "BEGIN MODIFIED CODE" followed by any text and a newline
            r"END MODIFIED CODE\n"                    # Match "END MODIFIED CODE" followed by a newline
            r"BEGIN DESCRIPTION\n(.*?)\n"             # Match "BEGIN DESCRIPTION" followed by any text and a newline
            r"END DESCRIPTION\n"                      # Match "END DESCRIPTION" followed by a newline
            r"END BUG FIX",                           # Match "END BUG FIX"
            re.DOTALL,
        )
        matches = pattern.findall(output)
        return [
            RepairedFileContents(
                filename=match[0].strip(),
                function_name=match[1].strip(),
                code=match[2].strip(),
            )
            for match in matches
        ]

    def _implied_functions_to_str(self) -> list[str]:
        assert self.diagnosis.implicated_functions_at_head is not None
        return [
            function_diagnosis.name for function_diagnosis in self.diagnosis.implicated_functions_at_head
        ]

    def _extract_begin_end_lines(self, function_name: str) -> FileLines | None:
        assert self.diagnosis.implicated_functions_at_head is not None
        for function_diagnosis in self.diagnosis.implicated_functions_at_head:
            if function_diagnosis.name == function_name:
                return FileLines(
                    function_diagnosis.location.location_range.start.line,
                    function_diagnosis.location.location_range.stop.line,
                )
        return None

    def _extract_patches(self, llm_output: str) -> list[Diff]:
        repaired_files: list[RepairedFileContents] = self._extract_file_repairs(llm_output)

        # Apply patches and generate diffs
        diffs: list[Diff] = []

        for patch in repaired_files:
            modified_code = patch.code
            filename = patch.filename
            function_name = patch.function_name

            lines = self.files[filename].split("\n")

            file_lines = self._extract_begin_end_lines(function_name)
            if file_lines is None:
                logger.info(f"did not find function {function_name}")
                continue

            logger.info(f"function: {function_name}, begin: {file_lines.begin}, end: {file_lines.end}")

            # Replace the lines in the range with the modified code
            modified_lines = lines[:file_lines.begin - 1] + modified_code.split("\n") + lines[file_lines.end + 1:]

            # Create the modified file content
            modified_file_content = "\n".join(modified_lines)

            # Generate the diff
            diff = difflib.unified_diff(
                self.files[filename].splitlines(keepends=True),
                modified_file_content.splitlines(keepends=True),
                fromfile=filename,
                tofile=filename,
            )

            # Convert the diff to a string and add to the diffs list
            diff_patch = "".join(diff)
            diffs.append(Diff.from_unidiff(diff_patch))

        return diffs

    def _call_llm(self, prompt: str) -> str:
        model = self.model
        client = openai.OpenAI(
            api_key=self.master_key,
            base_url=self.litellm_url,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert security analyst."},
                {"role": "system", "content": "You can find security vulnerabilities and suggest patches to fix them."},
                {"role": "system", "content": "You always do minimal changes to the code."},
                {"role": "user", "content": prompt},
            ],
        )

        llm_output = response.choices[0].message.content
        if llm_output is None:
            return ""

        return llm_output

    def run(self) -> list[Diff]:
        function_names = self._implied_functions_to_str()
        # FIXME obtain the minimized diff
        prompt = create_context_all_files_git_diff(self.files, self.diff, str(function_names))
        llm_output = self._call_llm(prompt)
        return self._extract_patches(llm_output)
