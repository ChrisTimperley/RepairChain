from __future__ import annotations

import typing as t
from dataclasses import dataclass

import kaskara
from sourcelocation.fileline import FileLine


@dataclass
class StackFrame:
    funcname: str | None
    filename: str | None
    lineno: int | None
    offset: int | None
    bytes_offset: str | None

    def is_valid(self) -> bool:
        return self.lineno is not None and self.offset is not None

    @property
    def file_line(self) -> FileLine:
        assert self.lineno is not None
        assert self.filename is not None
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
        return {frame.funcname for frame in self.frames if frame.funcname is not None}

    def is_valid(self) -> bool:  # FIXME: Claire isn't sure we want to reject stack frames without lines/offsets
        """Determines if all stack frames are valid."""
        return all(frame.is_valid() for frame in self.frames)


def extract_location_symbolized(line: str) -> tuple[str, int | None, int | None]:
    filename = line
    lineno: int | None = None
    offset: int | None = None
    offsetstr = ""
    if ":" in line:
        filename, _, linenostr = line.partition(":")
        if ":" in linenostr:
            line, _, offsetstr = linenostr.partition(":")
    try:
        lineno = int(line)
    except ValueError:
        lineno = None

    try:
        if " " in offsetstr:
            offsetstr, _, _ = offsetstr.partition(" ")
        offset = int(offsetstr)
    except ValueError:
        offset = None
    return filename, lineno, offset


def extract_stack_frame_from_line_symbolized(line: str) -> StackFrame:
    _, _, restline = line.partition(" in ")
    if ")" in restline:
        funcname, _, restline = restline.partition("(")
        _, _, restline = restline.partition(") ")
    else:
        funcname, _, restline = restline.partition(" ")

    filename, lineno, offset = extract_location_symbolized(restline)

    return StackFrame(
        funcname=funcname,
        filename=filename,
        lineno=lineno,
        offset=offset,
        bytes_offset=None,
    )


def extract_location_not_symbolized(line: str) -> tuple[str, str | None]:
    # should return function name, byte offset
    raise NotImplementedError


def extract_stack_frame_from_line_not_symbolized(line: str) -> StackFrame:
    funcname: str | None = None
    bytes_offset: str | None = None

    if "]" in line:
        _, _, line = line.partition("] ")
    if "?" in line.lstrip():
        _, _, line = line.partition("?")
    line = line.lstrip()
    if "+" in line:
        funcname, _, bytes_offset = line.partition("+")

    return StackFrame(
        funcname=funcname,
        filename=None,
        lineno=None,
        offset=None,
        bytes_offset=bytes_offset)
