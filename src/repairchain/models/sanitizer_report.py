from __future__ import annotations

from loguru import logger

__all__ = (
    "Sanitizer",
    "SanitizerReport",
)

import contextlib
import enum
import re
import typing as t
from dataclasses import dataclass, field

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class StackTrace:
    funcname: str
    filename: str
    lineno: int
    offset: int


def process_stack_trace_line(line: str) -> StackTrace:
    split_index = line.find(" in ")  # FIXME: error handle
    rhs = line[split_index + 4:]
    sig_index = rhs.find(")") if "(" in rhs else rhs.find(" ")

    funcname = rhs[:sig_index]
    filename_part = rhs[sig_index + 1:]

    line_index = filename_part.find(":")
    filename = filename_part
    lineno = -1
    offset = -1
    if line_index != -1:
        filename = filename_part[:line_index]
        linenostr = filename_part[line_index + 1:]
        offset_index = linenostr.find(":")
        if offset_index != -1:
            offset = int(linenostr[offset_index + 1:])
            lineno = int(linenostr[:offset_index])
        else:
            with contextlib.suppress(ValueError):
                lineno = int(linenostr)

    return StackTrace(funcname,
                    filename,
                    lineno,
                    offset)


def parse_asan_output(asan_output: str) -> tuple[str, list[StackTrace]]:
    # Regular expressions to match different parts of the ASan output
    error_regex = re.compile(r".*ERROR: AddressSanitizer: (.+)")

    stack_trace_regex = re.compile(r"\s*#(?P<frame>\d+) "
                                   r"0x(?P<address>[0-9a-f]+) in ")
#                                   r"(?P<function>[^\s]+"
#                                   r"|[a-zA-Z_][a-zA-Z0-9_]*(::[a-zA-Z_][a-zA-Z0-9_]*)*\(.*\)) "
#                                   r"(?P<filename>[\w/\.]+):"
#                                   r"(?P<line>\d+):"
#                                   r"(?P<offset>\d+)\s*")
    # possible FIXME: error handling on this, possibly no offset for example

    memory_regex = re.compile(r".*is located (?P<bytes_after>\d+) bytes after (?P<size>\d+)-byte region.*")

    error_name = ""
    stack_trace: list[StackTrace] = []
    processing_stack_trace = False

    for line in asan_output.splitlines():
        error_match = error_regex.match(line)
        stack_trace_match = stack_trace_regex.match(line)
        memory_match = memory_regex.match(line)
        if error_match:
            error_name = error_match.group(1)
        elif memory_match or "__libc_start_main" in line:
            break
        elif stack_trace_match:
            processing_stack_trace = True
        if processing_stack_trace:
            stack_trace.append(process_stack_trace_line(line))

    return (error_name, stack_trace)


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
    error_type: str
    stack_trace: list[StackTrace]

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
        error_type, stack_trace = parse_asan_output(text)  # asan only for now
        return cls(
            contents=text,
            sanitizer=sanitizer,
            error_type=error_type,
            stack_trace=stack_trace,
        )

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents)
