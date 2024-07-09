from __future__ import annotations

from loguru import logger

__all__ = (
    "Sanitizer",
    "SanitizerReport",
)

import enum
import re
import typing as t
from dataclasses import dataclass, field

if t.TYPE_CHECKING:
    from pathlib import Path

@dataclass
class StackTrace:
    frame: int
    address: str
    funcname: str
    filename: str
    lineno: int
    offset: int


def parse_asan_output(asan_output: str) -> dict[str, list[StackTrace]]:
    # Regular expressions to match different parts of the ASan output
    error_regex = re.compile(r".*ERROR: AddressSanitizer: (.+)")
    stack_trace_regex = re.compile(r"\s*#(?P<frame>\d+) 0x(?P<address>[0-9a-f]+) in (?P<function>[^\s]+) (?P<filename>[\w/\.]+):(?P<line>\d+):(?P<offset>\d+)")
    # possible FIXME: error handling on this, possibly no offset for example

    memory_regex = re.compile(r".*is located (?P<bytes_after>\d+) bytes after (?P<size>\d+)-byte region.*")
    newline_regex = re.compile(r"^\n", re.MULTILINE)
    # Data structure to hold parsed information
    parsed_data: dict[str, list[StackTrace]] = {}

    current_error = ""
    current_stack_trace: list[StackTrace] = []

    for line in asan_output.splitlines():
        error_match = error_regex.match(line)
        stack_trace_match = stack_trace_regex.match(line)
        newline_match = newline_regex.match(line)
        memory_match = memory_regex.match(line)
        if error_match:
            if current_error:
                parsed_data[current_error] = current_stack_trace
            current_error = error_match.group(1)
            current_stack_trace = []
        elif newline_match:  # hopefully the end of the thread
            if current_error:
                parsed_data[current_error] = current_stack_trace
                current_error = ""
                current_stack_trace = []
        elif stack_trace_match:
            if current_error:
                frame = int(stack_trace_match.group("frame"))
                address = stack_trace_match.group("address")
                function = stack_trace_match.group("function")
                filename = stack_trace_match.group("filename")
                lineno = int(stack_trace_match.group("line"))
                offset = int(stack_trace_match.group("offset"))

                current_stack_trace.append(
                    StackTrace(frame,
                    address,
                    function,
                    filename,
                    lineno,
                    offset),
                )
        elif memory_match:
            break

    if current_error:
        parsed_data[current_error] = current_stack_trace

    return parsed_data


class Sanitizer(enum.StrEnum):
    UNKNOWN = "unknown"
    KASAN = "kasan"
    KFENCE = "kfence"
    ASAN = "asan"
    MEMSAN = "msan"
    UBSAN = "ubsan"
    JAZZER = "jazzer"


@dataclass
class SanitizerReport:
    contents: str = field(repr=False)
    sanitizer: Sanitizer
    stack_trace: dict[str, list[StackTrace]]

    @classmethod
    def _find_sanitizer(cls, report_text: str) -> Sanitizer:
        report_text.lower()
        if "java exception:" in report_text:
            return Sanitizer.JAZZER
        if "kasan" in report_text or "kerneladdresssanitizer" in report_text:
            return Sanitizer.KASAN
        if "kfence" in report_text:
            return Sanitizer.KFENCE
        if "addresssanitizer" in report_text or "asan" in report_text:
            return Sanitizer.ASAN
        if "memsan" in report_text:
            return Sanitizer.MEMSAN
        if "ubsan" in report_text:
            return Sanitizer.UBSAN

        return Sanitizer.UNKNOWN

    @classmethod
    def from_report_text(cls, text: str) -> t.Self:
        sanitizer = cls._find_sanitizer(text)
        logger.debug(f"from report text, sanitizer {sanitizer}")
        stack_trace = parse_asan_output(text)  # asan only for now
        return cls(
            contents=text,
            sanitizer=sanitizer,
            stack_trace=stack_trace
        )

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents)
