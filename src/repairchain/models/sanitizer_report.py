from __future__ import annotations

__all__ = ("SanitizerReport",)

import typing as t
from dataclasses import dataclass
from enum import Enum

if t.TYPE_CHECKING:
    from pathlib import Path


class Sanitizer(Enum):
    UNKNOWN = 0
    KASAN = 1
    KFENCE = 2
    ASAN = 3
    MEMSAN = 4
    UBSAN = 5
    JAZZER = 6


@dataclass
class SanitizerReport:
    contents: str
    sanitizer: Sanitizer

    # assumes report_text has been lowercased
    @staticmethod
    def find_sanitizer(report_text: str) -> Sanitizer:
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
    def from_report_text(cls, text: str, is_java: bool) -> t.Self:
        # FIXME this is a placeholder for now
        lowercase = text.lower()
        sanitizer = Sanitizer.JAZZER if is_java else SanitizerReport.find_sanitizer(lowercase)
        return cls(
            contents=text,
            sanitizer=sanitizer,
        )

    @classmethod
    def load(cls, path: Path, is_java: bool) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents, is_java)
