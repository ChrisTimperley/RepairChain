from __future__ import annotations

import difflib
import re
import typing as t
from dataclasses import dataclass

import openai

from repairchain.actions import commit_to_diff
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy
from repairchain.strategies.llms.context import create_context_all_files_git_diff

__all__ = ("SimpleYolo",)

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis


@dataclass
class SimpleYolo(PatchGenerationStrategy):
    prompt: str
    model: str
    litellm_url: str
    files: dict[str, str]

    def __init__(self, diagnosis: Diagnosis, files: dict[str, str], prompt: str, model: str,
                 litellm_url: str) -> None:
        self.diagnosis = diagnosis
        self.prompt = prompt
        self.model = model
        self.litellm_url = litellm_url
        self.files = files

    @classmethod
    def build(cls, diagnosis: Diagnosis, model: str = "oai-gpt-4o",
              litellm_url: str = "http://0.0.0.0:4000") -> SimpleYolo:
        diff = commit_to_diff.commit_to_diff(diagnosis.project.triggering_commit)
        files = commit_to_diff.commit_to_files(diagnosis.project.head, diff)
        prompt = create_context_all_files_git_diff(files, diff)
        return cls(diagnosis, files, prompt, model, litellm_url)

    @classmethod
    def is_unified_diff(cls, diff: str) -> bool:
        lines = diff.split("\n")
        if not lines[0].startswith("--- ") or not lines[1].startswith("+++ "):
            return False

        try:
            for line in lines:
                if line.startswith("@@ "):
                    return True
        except (ValueError, IndexError):
            return False

        return False

    @classmethod
    # Function to extract modified codes from the output
    def extract_patches(cls, output: str) -> list[tuple[str, str, str]]:
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
            (
                match[0].strip(),  # modified filename
                match[1].strip(),  # modified function name
                match[2].strip(),  # modified code
            )
            for match in matches
        ]

    def create_diff_from_patches(self, output: str) -> list[Diff]:
        patches: list[tuple[str, str, str]] = self.extract_patches(output)

        # Apply patches and generate diffs
        diffs: list[Diff] = []

        for patch in patches:
            modified_code = patch[2]

            filename = patch[0]
            lines = self.files[filename].split("\n")
            function_name = patch[1]
            start_line = 0
            end_line = 0

            # NOTE: make this modular -- now just for testing mock cp
            if function_name == "func_a":
                start_line = 7
                end_line = 18

            if function_name == "func_b":
                start_line = 20
                end_line = 28

            # Replace the lines in the range with the modified code
            modified_lines = lines[:start_line - 1] + modified_code.split("\n") + lines[end_line + 1:]

            # Create the modified file content
            modified_file_content = "\n".join(modified_lines)

            print(modified_file_content)

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

    @classmethod
    def extract_git_diff(cls, llm_output: str) -> Diff:
        # Compile a regular expression pattern
        pattern = re.compile(re.escape("BEGIN GIT DIFF PATCH") +
                             "(.*?)" + re.escape("END GIT DIFF PATCH"))

        # Find all matches in the text
        matches = pattern.findall(llm_output)
        if cls.is_unified_diff("".join(matches)):
            return Diff.from_unidiff("".join(matches))

        return Diff.from_unidiff("")

    @classmethod
    def call_llm(cls, prompt: str, model: str, litellm_url: str) -> str:
        client = openai.OpenAI(api_key="anything", base_url=litellm_url)

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

    @classmethod
    def run(cls) -> list[Diff]:
        return []
