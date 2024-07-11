from __future__ import annotations

import contextlib
import typing as t
from dataclasses import dataclass

import kaskara
from sourcelocation.fileline import FileLine


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

    def is_valid(self) -> bool:  # FIXME: Claire isn't sure we want to reject stack frames without lines/offsets
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