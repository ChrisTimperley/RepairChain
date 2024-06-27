from __future__ import annotations

__all__ = ("PatchOutcome",)

import enum


class PatchOutcome(str, enum.Enum):
    """Reports the outcome of evaluating a single candidate patch.

    FAILED_TO_BUILD indicates that the patch did not compile; all other statuses imply that the patch compiled.
    PASSED indicates that the patch passed all tests and the sanitizer did not report any issues.
    FAILED indicates that the patch failed one or more tests.
    """
    PASSED = "passed"
    FAILED = "failed"
    FAILED_TO_BUILD = "failed-to-build"
