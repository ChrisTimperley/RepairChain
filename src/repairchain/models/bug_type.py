from __future__ import annotations

__all__ = ("BugType",)

import enum


class BugType(str, enum.Enum):
    USE_AFTER_FREE = "use-after-free"
