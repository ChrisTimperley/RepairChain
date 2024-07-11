from __future__ import annotations

import difflib

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
        return json.dumps(asdict(self), indent=4)


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
        return [function_diagnosis.name for function_diagnosis in diagnosis.implicated_functions_at_head]

    @staticmethod
    def extract_begin_end_lines(diagnosis: Diagnosis, function_name: str) -> FileLines | None:
        for function_diagnosis in diagnosis.implicated_functions_at_head:
            if function_diagnosis.name == function_name:
                return FileLines(
                    function_diagnosis.location.location_range.start.line,
                    function_diagnosis.location.location_range.stop.line,
                )
        return None

    @staticmethod
    def function_to_filename(diagnosis: Diagnosis, function_name: str) -> str | None:
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
