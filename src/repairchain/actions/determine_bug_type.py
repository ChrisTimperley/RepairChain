from __future__ import annotations

__all__ = ("determine_bug_type",)

import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.bug_type import BugType
    from repairchain.models.sanitizer_report import SanitizerReport


def determine_bug_type(report: SanitizerReport) -> BugType:
    raise NotImplementedError
