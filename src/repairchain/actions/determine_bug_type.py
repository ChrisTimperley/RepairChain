from __future__ import annotations

__all__ = ("determine_bug_type",)

import typing as t

from repairchain.models.bug_type import BugType

if t.TYPE_CHECKING:
    from repairchain.models.sanitizer_report import SanitizerReport

OS_COMMAND_INJECTION_TITLE = "== Java Exception: com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical: OS Command Injection"  # noqa: E501


def determine_bug_type(report: SanitizerReport) -> BugType:
    report_text = report.contents
    if " global-buffer-overflow " in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE

    if OS_COMMAND_INJECTION_TITLE in report_text:
        return BugType.OS_COMMAND_INJECTION

    raise NotImplementedError
