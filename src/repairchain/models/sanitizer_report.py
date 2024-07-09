from __future__ import annotations

__all__ = (
    "Sanitizer",
    "SanitizerReport",
)

import enum
import typing as t
from dataclasses import dataclass, field

if t.TYPE_CHECKING:
    from pathlib import Path


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
        return cls(
            contents=text,
            sanitizer=sanitizer,
        )

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents)
