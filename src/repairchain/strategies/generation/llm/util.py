from __future__ import annotations

import difflib
import unicodedata

__all__ = ("Util",)

import json
import typing as t
from dataclasses import asdict, dataclass, field

import tiktoken
from loguru import logger
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from repairchain.models.diff import Diff

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis

# Define the composite message type
MessageType = (ChatCompletionSystemMessageParam |
               ChatCompletionUserMessageParam |
               ChatCompletionAssistantMessageParam |
               ChatCompletionToolMessageParam |
               ChatCompletionFunctionMessageParam)

# Define the iterable of the composite message type
MessagesIterable = list[MessageType]

SIZE_DIFF = 5


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
class PatchFile:
    patch: list[RepairedFileContents]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1)


@dataclass
class Util:
    retry_attempts: int = field(default=5)
    short_sleep: int = field(default=5)
    long_sleep: int = field(default=30)
    sanitizer_report_size: int = field(default=50000)
    number_patches: int = field(default=10)
    limit_llm_output: int = field(default=4096)

    @staticmethod
    def implied_functions_to_str(diagnosis: Diagnosis) -> list[str]:
        assert diagnosis.implicated_functions_at_head is not None
        return [function_diagnosis.name for function_diagnosis in diagnosis.implicated_functions_at_head]

    @staticmethod
    def extract_begin_end_lines(diagnosis: Diagnosis, function_name: str) -> FileLines | None:
        assert diagnosis.implicated_functions_at_head is not None
        for function_diagnosis in diagnosis.implicated_functions_at_head:
            if function_diagnosis.name == function_name:
                return FileLines(
                    function_diagnosis.location.location_range.start.line,
                    function_diagnosis.location.location_range.stop.line,
                )
        return None

    @staticmethod
    def function_to_filename(diagnosis: Diagnosis, function_name: str) -> str | None:
        assert diagnosis.implicated_functions_at_head is not None
        for function_diagnosis in diagnosis.implicated_functions_at_head:
            if function_diagnosis.name == function_name:
                return function_diagnosis.location.filename
        return None

    @staticmethod
    def extract_lines_between_indices(text: str, start_line: int, end_line: int) -> str | None:
        # Split the string into lines
        lines = text.split("\n")

        # Check if the provided line indices are within the bounds of the list
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            logger.info("Lines not in range for function extraction")
            return None

        # Extract lines between start_line and end_line, inclusive (1-based index)
        return "\n".join(lines[start_line - 1:end_line])

    @staticmethod
    def extract_patches(diagnosis: Diagnosis, files: dict[str, str],
                        repaired_files: list[RepairedFileContents]) -> list[Diff]:
        # Apply patches and generate diffs
        diffs: list[Diff] = []

        for patch in repaired_files:
            modified_code = patch.code
            filename = patch.filename
            function_name = patch.function_name

            lines = files[filename].split("\n")

            file_lines = Util.extract_begin_end_lines(diagnosis, function_name)
            if file_lines is None:
                logger.info(f"did not find function {function_name}")
                continue

            # TODO: create some test cases to check if there are one by off error
            # Replace the lines in the range with the modified code
            modified_lines = lines[:file_lines.begin - 1] + modified_code.split("\n") + lines[file_lines.end + 1:]

            # Create the modified file content
            modified_file_content = "\n".join(modified_lines)

            # Generate the diff
            diff = difflib.unified_diff(
                files[filename].splitlines(keepends=True),
                modified_file_content.splitlines(keepends=True),
                fromfile=filename,
                tofile=filename,
            )

            # Convert the diff to a string and add to the diffs list
            diff_patch = "".join(diff)
            diffs.append(Diff.from_unidiff(diff_patch))

        return diffs

    @staticmethod
    def count_tokens(text: str, model: str) -> int:
        try:
            # Explicitly use the cl100k_base encoder
            encoding = tiktoken.get_encoding("cl100k_base")
        except KeyError as e:
            error_message = f"Failed to get encoding for the model {model}."
            raise ValueError(error_message) from e

        tokens = encoding.encode(text)
        return len(tokens)

    @staticmethod
    def strip_diff(line: str, prefix: str) -> str:
        if line.startswith(prefix):
            prefix_length = len(prefix)
            return line[prefix_length:]
        return line

    @staticmethod
    def remove_last_newline(string: str) -> str:
        if string.endswith("\n"):
            return string[:-1]
        return string

    @staticmethod
    def check_patch_format(diff_lines: list[str]) -> bool:
        # diff has <code>\n+++\n---\n@@ ... @@\n(code)</code>
        if len(diff_lines) < SIZE_DIFF:
            return False

        if not diff_lines[1].startswith("---"):
            logger.debug(f"Unexpected patch format {diff_lines}")
            return False
        if not diff_lines[2].startswith("+++"):
            logger.debug(f"Unexpected patch format {diff_lines}")
            return False
        if not diff_lines[3].startswith("@@"):
            logger.debug(f"Unexpected patch format {diff_lines}")
            return False

        return True

    @staticmethod
    def apply_patch(original: str, diff: str) -> str:
        original_lines = original.split("\n")
        diff_lines = diff.split("\n")

        # Remove empty lines at the end
        while diff_lines and not diff_lines[-1]:
            diff_lines.pop()

        if not Util.check_patch_format(diff_lines):
            return ""

        diff_lines = diff_lines[4:len(diff_lines) - 1]

        patch_original_lines: list[str] = []
        for line in diff_lines:
            if line.startswith("-"):
                patch_original_lines.append(Util.strip_diff(line, "-"))
            elif line.startswith("+"):
                continue
            else:
                patch_original_lines.append(line)

        patch_original_lines_stripped = [s.replace(" ", "") for s in patch_original_lines]
        original_lines_stripped = [s.replace(" ", "") for s in original_lines]

        # not sure if this normalization is needed
        patch_original_lines_stripped = [unicodedata.normalize("NFKD", s) for s in patch_original_lines_stripped]
        original_lines_stripped = [unicodedata.normalize("NFKD", s) for s in original_lines_stripped]

        len_patch_original_lines_stripped = len(patch_original_lines_stripped)
        len_original_lines_stripped = len(original_lines_stripped)

        hunk_position = -1
        if len_patch_original_lines_stripped < len_original_lines_stripped:
            for i in range(len_original_lines_stripped - len_patch_original_lines_stripped + 1):
                if original_lines_stripped[i:i + len_patch_original_lines_stripped] == patch_original_lines_stripped:
                    hunk_position = i
                    break

        patch_lines: list[str] = []
        pos = 0
        pos_orig = hunk_position
        if hunk_position > -1:
            patch_lines = original_lines[0:hunk_position]
            while pos < len(diff_lines):
                if diff_lines[pos].startswith("+"):
                    patch_lines.append(Util.strip_diff(diff_lines[pos], "+"))
                elif diff_lines[pos].startswith("-"):
                    pos_orig += 1
                else:
                    patch_lines.append(diff_lines[pos])
                    pos_orig += 1
                pos += 1

            patch_lines.extend(original_lines[pos_orig:len(original_lines)])
        else:
            logger.debug(f"Unified diff contents do not match original file:\n {diff}\n")
            # logger.debug(f"Original file:\n {original}\n")

        if patch_lines:
            patch_str = "\n".join(patch_lines[:-1]) + (
                "\n" + patch_lines[-1] if len(patch_lines) > 1 else patch_lines[-1])
        else:
            patch_str = ""

        logger.debug(patch_str)

        return patch_str
