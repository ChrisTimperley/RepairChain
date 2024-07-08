from __future__ import annotations

__all__ = (
    "Sanitizer",
    "SanitizerReport",
)

import re
import enum
import typing as t
from dataclasses import dataclass, field

if t.TYPE_CHECKING:
    from pathlib import Path

@dataclass
class StackTrace:
    frame: int
    address: str
    function: str
    location: str


def parse_asan_output(asan_output: str) -> dict[str, list[StackTrace]]:
    # Regular expressions to match different parts of the ASan output
    error_regex = re.compile(r".*ERROR: AddressSanitizer: (.+)")
    stack_trace_regex = re.compile(r"\s*#(\d+)\s(0x[0-9a-fA-F]+)\s+in\s+([\w_]+)\s+([^:\s]+)(?::\d+:\d+)?")
    newline_regex = re.compile(r"^\n", re.MULTILINE)
    # Data structure to hold parsed information
    parsed_data: dict[str, list[StackTrace]] = {}

    current_error = ""
    current_stack_trace: list[StackTrace] = []

    for line in asan_output.splitlines():
        error_match = error_regex.match(line)
        stack_trace_match = stack_trace_regex.match(line)
        newline_match = newline_regex.match(line)

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
                frame_number = int(stack_trace_match.group(1))
                address = stack_trace_match.group(2)
                function = stack_trace_match.group(3)
                location = stack_trace_match.group(4)
                current_stack_trace.append(
                    StackTrace(frame_number,
                    address,
                    function,
                    location),
                )

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
