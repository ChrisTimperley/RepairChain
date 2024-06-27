from __future__ import annotations

__all__ = ("SanitizerReport",)

import typing as t
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class SanitizerReport:
    contents: str
    sanitizer: str  # FIXME: use an enum (is this even possible given the most recent DARPA example?)

    @classmethod
    def from_report_text(cls, text: str) -> t.Self:
        # FIXME this is a placeholder for now
        return cls(
            contents=text,
            sanitizer="ASAN",
        )

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        contents = path.read_text()
        return cls.from_report_text(contents)
