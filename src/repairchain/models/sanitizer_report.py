from __future__ import annotations

__all__ = (
    "Sanitizer",
    "SanitizerReport",
)

import contextlib
import enum
import re
import typing as t
from dataclasses import dataclass, field

from loguru import logger
from sourcelocation.fileline import FileLine

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class StackFrame:
    funcname: str
    filename: str
    lineno: int
    offset: int

    @property
    def file_line(self) -> FileLine:
        return FileLine(self.filename, self.lineno)


@dataclass
class StackTrace(t.Sequence[StackFrame]):
    frames: t.Sequence[StackFrame]

    @t.overload
    def __getitem__(self, index_or_slice: int) -> StackFrame:
        ...

    @t.overload
    def __getitem__(self, index_or_slice: slice) -> t.Sequence[StackFrame]:
        ...

    def __getitem__(self, index_or_slice: int | slice) -> t.Sequence[StackFrame] | StackFrame:
        return self.frames[index_or_slice]

    def __len__(self) -> int:
        return len(self.frames)

    def __iter__(self) -> t.Iterator[StackFrame]:
        yield from self.frames


def extract_stack_frame_from_line(line: str) -> StackFrame:
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

    return StackFrame(
        funcname,
        filename,
        lineno,
        offset,
    )


def parse_asan_output(asan_output: str) -> tuple[str, list[StackFrame]]:
    # Regular expressions to match different parts of the ASan output
    error_regex = re.compile(r".*ERROR: AddressSanitizer: (.+)")
    stack_frame_regex = re.compile(
        r"\s*#(?P<frame>\d+) "
        r"0x(?P<address>[0-9a-f]+) in ",
    )
    memory_regex = re.compile(r".*is located (?P<bytes_after>\d+) bytes after (?P<size>\d+)-byte region.*")

    error_name = ""
    stack_trace: list[StackFrame] = []
    processing_stack_trace = False

    for line in asan_output.splitlines():
        error_match = error_regex.match(line)
        stack_trace_match = stack_frame_regex.match(line)
        memory_match = memory_regex.match(line)
        if error_match:
            error_name = error_match.group(1)
        elif memory_match or "__libc_start_main" in line:
            break
        elif stack_trace_match:
            processing_stack_trace = True
        if processing_stack_trace:
            stack_trace.append(extract_stack_frame_from_line(line))

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
    stack_trace: list[StackFrame]

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
