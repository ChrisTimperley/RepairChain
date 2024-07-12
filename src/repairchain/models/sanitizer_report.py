from __future__ import annotations

from functools import partial

from repairchain.models.bug_type import BugType, Sanitizer, determine_bug_type
from repairchain.models.stack_trace import (
    StackFrame,
    StackTrace,
    extract_location_not_symbolized,
    extract_location_symbolized,
    extract_stack_frame_from_line_not_symbolized,
    extract_stack_frame_from_line_symbolized,
)

__all__ = (
    "Sanitizer",
    "SanitizerReport",
    "parser_dict",
)

import re
import typing as t
from dataclasses import dataclass, field

from loguru import logger

if t.TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def parse_stack_frame_simple(line: str) -> StackFrame | None:
    stack_frame_regex = re.compile(
        r"\s*#(?P<frame>\d+) "
        r"0x(?P<address>[0-9a-f]+) in ",
    )
    stack_trace_match = stack_frame_regex.match(line)
    if stack_trace_match:
        return extract_stack_frame_from_line_symbolized(line)
    return None


def parse_stack_frame_kernel(line: str) -> StackFrame | None:
    kernel_pattern_timestamps = re.compile(
        r"^\[\s*\d+\.\d+\]\s*(\??\s*[a-zA-Z_]+\w*)")

    stack_trace_match = kernel_pattern_timestamps.match(line)
    if stack_trace_match and "+" in line:
        return extract_stack_frame_from_line_not_symbolized(line)
    stack_frame_regex = re.compile(
        r"\s*#(?P<frame>\d+) "
        r"0x(?P<address>[0-9a-f]+) in ",
    )
    if stack_frame_regex.match(line):
        return extract_stack_frame_from_line_symbolized(line)

    if "+" in line:
        line = line.strip()
        return extract_stack_frame_from_line_not_symbolized(line)
    return None


def easy_match_extra_info(find_extra_info: str, line: str) -> str | None:
    if find_extra_info in line:
        _, _, extra_info = line.partition(find_extra_info)
        return extra_info
    return None


def easy_find_loc(find_triggered_loc: str, line: str) -> StackFrame | None:
    if find_triggered_loc in line:
        funcname: str | None = None
        filename: str | None = None
        bytes_offset: str | None = None
        offset: int | None = None
        lineno: int | None = None
        _, _, rest_line = line.partition(find_triggered_loc)
        _, _, loc_line = rest_line.partition(" ")
        loc_str, _, funcname = loc_line.partition(" in ")
        if ":" in loc_str:
            filename, lineno, offset = extract_location_symbolized(loc_str)
        elif "+" in loc_str:
            funcname, bytes_offset = extract_location_not_symbolized(loc_str)
        return StackFrame(
            funcname=funcname,
            filename=filename,
            lineno=lineno,
            offset=offset,
            bytes_offset=bytes_offset,
        )
    return None


def parse_report_generic(sanitizer_output: str,  # noqa: PLR0917
                extra_info_find: Callable[[str], str | None],
                find_triggered_loc: Callable[[str], StackFrame | None],
                parse_trace_ele: Callable[[str], StackFrame | None],
                start_call_trace: str,
                start_alloc_trace: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    """Parse generic report info.

    Takes a substring indicating where to start parsing the extra info, call trace, and allocated trace.

    Returns the extra bug info, frame describing location error triggered, and call trace
    and allocated trace as available.
    """
    extra_info: str | None = None
    loc_triggered: StackFrame | None = None

    call_trace: list[StackFrame] = []
    allocated_trace: list[StackFrame] = []

    processing_call_trace = False
    processing_allocated = False

    for line in sanitizer_output.splitlines():
        extra_info = extra_info_find(line) if extra_info is None else extra_info
        loc_triggered = find_triggered_loc(line) if loc_triggered is None else loc_triggered

        # FIXME: do I care to break early?  Possibly unimportant
        if processing_call_trace:
            stack_frame = parse_trace_ele(line)
            if stack_frame is not None:
                call_trace.append(stack_frame)
        if processing_allocated:
            stack_frame = parse_trace_ele(line)
            if stack_frame is not None:
                allocated_trace.append(stack_frame)
        if start_call_trace in line:
            processing_call_trace = True
            processing_allocated = False
        if start_alloc_trace in line:
            processing_allocated = True
            processing_call_trace = False
    info = "" if extra_info is None else extra_info

    return (info, loc_triggered, StackTrace(call_trace), StackTrace(allocated_trace))


# FIXME: this is substantially similar to parse_kfence, consider condensing.
# except kasan may not have timestamps?
# similarly, too, there may be extra info of note if we want it in the
# line after the one we're currently grabbing the info from
def parse_kasan(kasan_output: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    """Parse kasan reports.

    Returns the extra bug info, frame describing location error triggered, and call trace
    and allocated trace as available.
    """
    def kasan_extra_info(info_line: str) ->  str | None:
        if "BUG: KASAN: " in info_line:
            _, _, second_part = info_line.partition("BUG: KASAN: ")
            error_info, _, _ = second_part.partition(" in ")
            return error_info
        return None

    def kasan_location(info_line: str) -> StackFrame | None:
        funcname: str | None = None
        filename: str | None = None
        bytes_offset: str | None = None
        offset: int | None = None
        lineno: int | None = None

        if "BUG: KASAN: " in info_line:
            _, _, loc_str = info_line.partition(" in ")
            if "+" in loc_str:  # byte offset
                funcname, _, bytes_offset = loc_str.partition("+")
            elif ":" in loc_str:  # symbolized
                filename, lineno, offset = extract_location_symbolized(loc_str)
            else:
                # got nothing, probably a functionname?
                _, _, funcname = info_line.partition("BUG: KFENCE: ")
            return StackFrame(
            funcname=funcname,
            filename=filename,
            lineno=lineno,
            offset=offset,
            bytes_offset=bytes_offset,
            )
        return None
    return parse_report_generic(kasan_output,
                                kasan_extra_info,
                                kasan_location,
                                parse_stack_frame_kernel,
                                "Call Trace:",
                                "Allocated by",
                            )


# possible TODO: there is additional potentially useful extra info in the line after
# the line we're currently getting "error info" from, but the complexities of getting it
# outweigh the benefit at this time.
def parse_kfence(kfence_output: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    """Parse kfence info.

    Returns the extra bug info, frame describing location error triggered, and call trace
    and allocated trace as available.
    """
    def kfence_extra_info(info_line: str) ->  str | None:
        if "BUG: KFENCE: " in info_line:
            _, _, second_part = info_line.partition("BUG: KFENCE: ")
            error_info, _, _ = second_part.partition(" in ")
            return error_info
        return None

    def kfence_location(info_line: str) -> StackFrame | None:
        funcname: str | None = None
        filename: str | None = None
        bytes_offset: str | None = None
        offset: int | None = None
        lineno: int | None = None

        if "BUG: KFENCE: " in info_line:
            _, _, loc_str = info_line.partition(" in ")
            if "+" in loc_str:  # byte offset
                funcname, _, bytes_offset = loc_str.partition("+")
            elif ":" in loc_str:  # symbolized
                filename, lineno, offset = extract_location_symbolized(loc_str)
            else:
                # got nothing, probably a functionname?
                _, _, funcname = info_line.partition("BUG: KFENCE: ")
            return StackFrame(
            funcname=funcname,
            filename=filename,
            lineno=lineno,
            offset=offset,
            bytes_offset=bytes_offset,
            )
        return None
    # possible fixme:if "Memory state" in line: break

    return parse_report_generic(kfence_output,
                                kfence_extra_info,
                                kfence_location,
                                parse_stack_frame_kernel,
                                "Call Trace:",
                                "Allocated by",
                            )


def parse_asan(asan_output: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    """Parse asan info.

    Returns the extra bug info, frame describing location error triggered, and call trace
    and allocated trace as available.
    """
    find_extra_info = partial(easy_match_extra_info, "ERROR: AddressSanitizer: ")
    find_triggering_loc = partial(easy_find_loc, "SUMMARY: AddressSanitizer: ")
    return parse_report_generic(asan_output,
                            find_extra_info,
                            find_triggering_loc,
                            parse_stack_frame_simple,
                            "ERROR: AddressSanitizer: ",
                            "allocated by thread ",
                            )


def parse_memsan(memsan_output: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    """Parse memsan info.

    Returns the extra bug info, frame describing location error triggered, and call trace
    and allocated trace as available.
    """
    find_extra_info = partial(easy_match_extra_info, "WARNING: Memory Sanitizer: ")
    find_triggering_loc = partial(easy_find_loc, "SUMMARY: AddressSanitizer: ")

    return parse_report_generic(memsan_output,
                        find_extra_info,
                        find_triggering_loc,
                        parse_stack_frame_simple,
                        "WARNING: Memory Sanitizer: ",
                        "value was created by",
                        )


def parse_ubsan(ubsan_output: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    """Parse ubsan info.

    Returns the extra bug info, frame describing location error triggered.
    """
    # runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
    # SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior file.cpp:7:21

    filename: str | None = None
    lineno: int | None = None
    offset: int | None = None
    extra_information = ""

    for line in ubsan_output.splitlines():
        stripped = line.strip()
        if "SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior" in stripped:
            _, _, location = stripped.partition("undefined-behavior ")
            filename, lineno, offset = extract_location_symbolized(location)
        if "runtime error:" in stripped:
            _, _, extra_information = stripped.partition("error: ")
    frame = StackFrame(
        funcname=None,
        filename=filename,
        lineno=lineno,
        offset=offset,
        bytes_offset=None,
    )

    return (extra_information, frame, StackTrace([]), StackTrace([]))


def parse_java_stack_trace(line: str) -> StackFrame:
    funcname = None
    filename = None
    lineno = None
    if "(" in line:
        funcname, _, filenamepart = line.partition("(")
        if filenamepart.endswith(")"):
            filenamepart = filenamepart[:-1]
        if ":" in filenamepart:
            filename, _, lineno = filenamepart.partition(":")
    else:
        funcname = line
    lineno_int = int(lineno) if lineno is not None else None
    return StackFrame(
            funcname=funcname,
            filename=filename,
            lineno=lineno_int,
            offset=None,
            bytes_offset=None,
    )


# FIXME: we really need more jazzer examples for the types of bugs it's actually
# supposed to find, because this will be undertested by what we have
def parse_jazzer(jazzer_output: str) -> tuple[str, StackFrame | None, StackTrace, StackTrace]:
    extra_info = ""
    stack_trace: list[StackFrame] = []
    location: StackFrame | None = None
    for line in jazzer_output.splitlines():
        if "Java Exception:" in line:
            _, _, extra_info = line.partition("Java Exception: ")
        if "at " in line:
            _, _, restline = line.partition("at ")
            stack_trace.append(parse_java_stack_trace(restline))
    if len(stack_trace) > 0:
        location = stack_trace[0]

    return extra_info, location, StackTrace(stack_trace), StackTrace([])


parser_dict: dict[Sanitizer, Callable[[str], tuple[str, StackFrame | None, StackTrace, StackTrace]]] = {
    Sanitizer.KASAN: parse_kasan,
    Sanitizer.KFENCE: parse_kfence,
    Sanitizer.ASAN: parse_asan,
    Sanitizer.MEMSAN: parse_memsan,
    Sanitizer.UBSAN: parse_ubsan,
    Sanitizer.JAZZER: parse_jazzer,
}


@dataclass
class SanitizerReport:
    contents: str = field(repr=False)
    sanitizer: Sanitizer
    bug_type: BugType = BugType.UNKNOWN
    # FIXME move this into a separate subclass
    # possible thought: this information might vary by sanitizer, bug type
    # possibly condition on that?
    call_stack_trace: StackTrace | None = field(default=None)
    alloc_stack_trace: StackTrace | None = field(default=None)
    error_location: StackFrame | None = field(default=None)
    extra_info: str | None = field(default=None)

    @classmethod
    def _find_sanitizer(cls, report_text: str) -> Sanitizer:
        report_text = report_text.lower()
        for line in report_text.splitlines():
            if "java exception:" in line:
                return Sanitizer.JAZZER
            if "kasan" in line or "kerneladdresssanitizer" in line:
                return Sanitizer.KASAN
            if "kfence" in line:
                return Sanitizer.KFENCE
            if "addresssanitizer" in line or "asan" in line:
                return Sanitizer.ASAN
            if "memsan" in report_text or "memorysanitizer" in report_text:
                return Sanitizer.MEMSAN
            if "ubsan" in report_text or "undefinedbehaviorsanitizer" in report_text:
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
        # FIXME: this will choke on unknown, sort of on purpose for testing
        parser_func = parser_dict[sanitizer]

        (report.extra_info,
        report.error_location,
        report.call_stack_trace,
        report.alloc_stack_trace) = parser_func(text)
        return report

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents)
