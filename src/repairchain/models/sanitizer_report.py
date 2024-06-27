from __future__ import annotations

__all__ = ("SanitizerReport",)

import typing as t
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class SanitizerReport:
    sanitizer: str  # FIXME: use an enum (is this even possible given the most recent DARPA example?)

    @classmethod
    def load(cls, path: Path) -> t.Self:
        if not path.exists():
            message = f"sanitizer report not found at {path}"
            raise FileNotFoundError(message)

        # FIXME this is a placeholder for now
        return cls(sanitizer="ASAN")
