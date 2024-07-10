from __future__ import annotations

from loguru import logger

from repairchain.models.sanitizer_report import Sanitizer

__all__ = ("determine_bug_type",)

import typing as t

from repairchain.models.bug_type import BugType

if t.TYPE_CHECKING:
    from repairchain.models.sanitizer_report import SanitizerReport

ASAN_GLOBAL_BUFFER_OVERFLOW = "AddressSanitizer: global-buffer-overflow"
ASAN_HEAP_BUFFER_OVERFLOW = "AddressSanitizer: heap-buffer-overflow"
KASAN_SLAB_OUT_OF_BOUNDS = "KASAN: slab-out-of-bounds"
OS_COMMAND_INJECTION_TITLE = "== Java Exception: com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical: OS Command Injection"  # noqa: E501

# Why yes, CLG did ask GPT to tell her what all the text that goes with each type of error ubsan can report
ubsan_bug_type_map = {
    "runtime error: signed integer overflow:": BugType.SIGNED_INTEGER_OVERFLOW,  # 18 (1a)
    "runtime error: unsigned integer overflow:": BugType.UNSIGNED_INTEGER_OVERFLOW,  # 1
    "runtime error: division by zero": BugType.DIV_BY_ZERO,  # 2
    "runtime error: shift exponent": BugType.INVALID_SHIFT,  # 3, covers shift by negative, or shift exponent too large
    "runtime error: load of null pointer of type": BugType.NULL_DEREFERENCE,  # 4
    "out of bounds for type": BugType.ARRAY_OOB,  # 5
    "runtime error: load of misaligned address": BugType.MISALIGNED_PTR,  # 6
    "which is not a valid value for type": BugType.INVALID_BOOLEAN,  # 7
    "runtime error: pointer index expression with base": BugType.PTR_OVERFLOW,  # 8
    "runtime error: returning address of local variable": BugType.INVALID_RETURN,  # 9
    "through pointer to incorrect function type": BugType.INVALID_FUNCALL,  # 10
    "runtime error: variable length array bound evaluates to non-positive value": BugType.VLA_BOUND_NOT_POS,  # 11
    "through pointer to object of type": BugType.OBJ_SIZE_MISMATCH,  # 12
    "runtime error: execution reached an unreachable program point": BugType.UNREACHABLE_CODE,  # 13
    "is outside the range of representable values of type": BugType.FLOAT_CAST_OVERFLOW,  # 14
    "runtime error: misaligned address": BugType.ADDRESS_MISALIGNMENT,  # 15
    "runtime error: unaligned atomic operation": BugType.UNALIGNED_ATOMIC,  # 16
    "runtime error: type mismatch in pointer arithmetic or array indexing": BugType.TYPE_MISMATCH,  # 17
    "runtime error: implicit conversion from type": BugType.IMPLICIT_TYPE_CONVERSION,  # 19
    "runtime error: load of uninitialized value": BugType.LOAD_UNINIT_VALUE,  # 21
}


def determine_bug_type(report: SanitizerReport) -> BugType:
    report_text = report.contents
    if report.sanitizer == Sanitizer.UBSAN:
        for key, val in ubsan_bug_type_map.items():
            if key in report_text:
                return val
        logger.info("ubsan report, but didn't find an ubsan bug type")
    if ASAN_GLOBAL_BUFFER_OVERFLOW in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE
    if ASAN_HEAP_BUFFER_OVERFLOW in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE
    if KASAN_SLAB_OUT_OF_BOUNDS in report_text and "Write of size" in report_text:
        return BugType.OUT_OF_BOUNDS_WRITE
    if OS_COMMAND_INJECTION_TITLE in report_text:
        return BugType.OS_COMMAND_INJECTION

    return BugType.UNKNOWN
