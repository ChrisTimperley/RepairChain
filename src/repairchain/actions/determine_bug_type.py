from __future__ import annotations

__all__ = ("determine_bug_type",)

import typing as t

from repairchain.models.bug_type import BugType

if t.TYPE_CHECKING:
    from repairchain.models.sanitizer_report import SanitizerReport

ASAN_GLOBAL_BUFFER_OVERFLOW = "AddressSanitizer: global-buffer-overflow"
ASAN_HEAP_BUFFER_OVERFLOW = "AddressSanitizer: heap-buffer-overflow"
OS_COMMAND_INJECTION_TITLE = "== Java Exception: com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical: OS Command Injection"  # noqa: E501


def determine_bug_type(report: SanitizerReport) -> BugType:
    report_text = report.contents
    if ASAN_GLOBAL_BUFFER_OVERFLOW in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE
    if ASAN_HEAP_BUFFER_OVERFLOW in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE
    if OS_COMMAND_INJECTION_TITLE in report_text:
        return BugType.OS_COMMAND_INJECTION

    raise NotImplementedError
