from __future__ import annotations

__all__ = ("determine_bug_type",)

import typing as t

from repairchain.models.bug_type import BugType

if t.TYPE_CHECKING:
    from repairchain.models.sanitizer_report import SanitizerReport


def determine_bug_type(report: SanitizerReport) -> BugType:
    report_text = report.contents
    if " global-buffer-overflow " in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE

    raise NotImplementedError
