from __future__ import annotations

from repairchain.models.bug_type import BugType, Sanitizer, determine_bug_type

__all__ = (
    "Sanitizer",
    "SanitizerReport",
)

import contextlib
import re
import typing as t
from dataclasses import dataclass, field

import kaskara.functions
from loguru import logger
from sourcelocation.fileline import FileLine

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class StackFrame:
    funcname: str
    filename: str
    lineno: int | None
    offset: int | None

    def is_valid(self) -> bool:
        return self.lineno is not None and self.offset is not None

    @property
    def file_line(self) -> FileLine:
        assert self.lineno is not None
        return FileLine(self.filename, self.lineno)

    def is_in_function(self, function: kaskara.functions.Function | str) -> bool:
        """Determines if the stack frame is in the given function."""
        if isinstance(function, kaskara.functions.Function):
            function = function.name
        return self.funcname == function


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

    def restrict_to_functions(self, functions: list[str] | list[kaskara.functions.Function]) -> StackTrace:
        """Filter the stack trace to only include frames in the given functions."""
        function_names: list[str] = []
        for function in functions:
            if isinstance(function, kaskara.functions.Function):
                function_names.append(function.name)
            else:
                function_names.append(function)
        frames = [frame for frame in self.frames if frame.funcname in function_names]
        return StackTrace(frames)

    def restrict_to_function(self, function: kaskara.functions.Function | str) -> StackTrace:
        """Filter the stack trace to only include frames in the given function."""
        if isinstance(function, kaskara.functions.Function):
            function = function.name
        frames = [frame for frame in self.frames if frame.funcname == function]
        return StackTrace(frames)

    def functions(self) -> set[str]:
        """Returns the set of function names in the stack trace."""
        return {frame.funcname for frame in self.frames}

    def is_valid(self) -> bool:
        """Determines if all stack frames are valid."""
        return all(frame.is_valid() for frame in self.frames)


def extract_location(line: str) -> tuple[str, int | None, int | None]:
    filename = line
    lineno: int | None = None
    offset: int | None = None
    line_index = line.find(":")

    if line_index != -1:
        filename = line[:line_index]
        linenostr = line[line_index + 1:]
        filename, lineno, offset = extract_location(linenostr)
        offset_index = linenostr.find(":")
        if offset_index != -1:
            offset = int(linenostr[offset_index + 1:])
            lineno = int(linenostr[:offset_index])
        else:
            with contextlib.suppress(ValueError):
                lineno = int(linenostr)
    return filename, lineno, offset


def extract_stack_frame_from_line(line: str) -> StackFrame:
    # TODO prefer partition
    split_index = line.find(" in ")  # FIXME: error handle
    rhs = line[split_index + 4:]
    sig_index = rhs.find(")") if "(" in rhs else rhs.find(" ")

    funcname = rhs[:sig_index]
    filename_part = rhs[sig_index + 1:]
    filename, lineno, offset = extract_location(filename_part)

    return StackFrame(
        funcname=funcname,
        filename=filename,
        lineno=lineno,
        offset=offset,
    )


def parse_report(report_text: str,
                 error_regex: re.Pattern[str],
                 end_regex: re.Pattern[str]) -> tuple[str, StackTrace]:
    stack_frame_regex = re.compile(
        r"\s*#(?P<frame>\d+) "
        r"0x(?P<address>[0-9a-f]+) in ",
    )

    error_name = ""
    stack_frames: list[StackFrame] = []
    processing_stack_trace = False

    for line in report_text.splitlines():
        error_match = error_regex.match(line)
        stack_trace_match = stack_frame_regex.match(line)
        end_match = end_regex.match(line)
        if error_match:
            error_name = error_match.group(1)
        elif end_match or "__libc_start_main" in line:
            break
        elif stack_trace_match:
            processing_stack_trace = True
        if processing_stack_trace:
            stack_frames.append(extract_stack_frame_from_line(line))
    stack_trace = StackTrace(stack_frames)
    return error_name, stack_trace


def parse_kasan(kasan_output: str) -> tuple[str, StackTrace]:
    raise NotImplementedError


def parse_kfence(kfence_output: str) -> tuple[str, StackTrace]:
    raise NotImplementedError


def parse_asan(asan_output: str) -> tuple[str, StackTrace]:
    return parse_report(asan_output,
                        re.compile(r".*ERROR: AddressSanitizer: (.+)"),
                        re.compile(r".*is located (?P<bytes_after>\d+) bytes after (?P<size>\d+)-byte region.*"),
                        )


def parse_memsan(memsan_output: str) -> tuple[str, StackTrace]:
    return parse_report(memsan_output,
                        re.compile(r".*WARNING: MemorySanitizer: (.+)"),
                        re.compile(r".*SUMMARY: MemorySanitizer:.*"),
                        )


def parse_ubsan(ubsan_output: str) -> tuple[str, StackTrace]:
    # runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
    # SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior file.cpp:7:21

    filename = ""
    lineno = None
    offset = None
    extra_information = ""

    for line in ubsan_output:
        stripped = line.strip()
        if "SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior" in stripped:
            _, _, location = stripped.partition("undefined-behavior ")
            filename, lineno, offset = extract_location(location)
        if "runtime error:" in stripped:
            _, _, extra_information = stripped.partition("error:")
    frame = StackFrame(
        funcname="",  # FIXME: bad idea, and need to get the function eventually
        filename=filename,
        lineno=lineno,
        offset=offset,
    )

    return (extra_information, StackTrace([frame]))


def parse_jazzer(jazzer_output: str) -> tuple[str, StackTrace]:
    raise NotImplementedError


@dataclass
class SanitizerReport:
    contents: str = field(repr=False)
    sanitizer: Sanitizer
    error_info: str | None = field(default=None)
    bug_type: BugType = BugType.UNKNOWN
    # FIXME move this into a separate subclass
    stack_trace: StackTrace | None = field(default=None)

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
        bug_type = determine_bug_type(text, sanitizer)
        logger.debug(f"from report text, sanitizer {sanitizer}")
        report = cls(
            contents=text,
            sanitizer=sanitizer,
            bug_type=bug_type,
        )
        # TODO need to deal with stack traces that may contain a mix of relative
        # and absolute paths
        match sanitizer:
            case Sanitizer.KASAN:
                report.error_info, report.stack_trace = parse_kasan(text)
            case Sanitizer.KFENCE:
                report.error_info, report.stack_trace = parse_kfence(text)
            case Sanitizer.ASAN:
                report.error_info, report.stack_trace = parse_asan(text)
            case Sanitizer.MEMSAN:
                report.error_info, report.stack_trace = parse_memsan(text)
            case Sanitizer.UBSAN:
                report.error_info, report.stack_trace = parse_ubsan(text)
            case Sanitizer.JAZZER:
                report.error_info, report.stack_trace = parse_jazzer(text)

        return report

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents)
