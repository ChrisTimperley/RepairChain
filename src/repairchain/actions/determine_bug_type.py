from __future__ import annotations

from loguru import logger

from repairchain.models.sanitizer_report import Sanitizer

__all__ = ("determine_bug_type",)

import typing as t

from repairchain.models.bug_type import BugType

if t.TYPE_CHECKING:
    from repairchain.models.sanitizer_report import SanitizerReport

# Why yes, CLG did ask GPT to tell her what all the text that goes with each type of error
# each sanitizer can report

kasan_bug_map = {
    "KASan: use-after-free in": BugType.USE_AFTER_FREE,
    "KASAN: slab-out-of-bounds": BugType.OUT_OF_BOUNDS_WRITE,  #  FIXME: heap, right? 
    "KASan: stack-out-of-bounds": BugType.UNKNOWN,  # FIXME: fix
    "KASan: global-out-of-bounds": BugType.UNKNOWN,  # FIXME: fix
    "KASan: stack-use-after-return": BugType.UNKNOWN,  # FIXME: fix
    "KASan: invalid-free": BugType.UNKNOWN,  # FIXME: fix
    "KASan: double-free": BugType.DOUBLE_FREE,
    "KASan: use-after-scope": BugType.UNKNOWN,  # FIXME: fix
    "KASan: uninit-value": BugType.UNKNOWN,  # FIXME: fix
    "KASan: wild-access": BugType.UNKNOWN,  # FIXME: fix
}


kfence_bug_map = {
    "KFENCE: use-after-free": BugType.USE_AFTER_FREE,
    "KFENCE: out-of-bounds access": BugType.UNKNOWN,  # FIXME: fix
    "KFENCE: memory corruption detected": BugType.UNKNOWN,  # FIXME: fix
    "KFENCE: double-free detected": BugType.DOUBLE_FREE,
    "KFENCE: invalid-free detected": BugType.UNKNOWN,  # FIXME: use after free or never allocated
}


asan_bug_map = {
    "AddressSanitizer: heap-buffer-overflow": BugType.OUT_OF_BOUNDS_WRITE,
    "AddressSanitizer: global-buffer-overflow": BugType.OUT_OF_BOUNDS_WRITE,
    "AddressSanitizer: stack-buffer-overflow": BugType.UNKNOWN,  # FIXME: fix
    "AddressSanitizer: use-after-free on address": BugType.USE_AFTER_FREE,
    "AddressSanitizer: stack-use-after-return": BugType.UNKNOWN,  # FIXME: fix
    "AddressSanitizer: stack-use-after-scope": BugType.UNKNOWN,  # FIXME: fix
    "AddressSanitizer: initialization-order-fiasco": BugType.UNKNOWN,  # FIXME: fix
    "LeakSanitizer: detected memory leaks": BugType.UNKNOWN,  # FIXME: fix
    "AddressSanitizer: attempting double-free": BugType.DOUBLE_FREE,
    "AddressSanitizer: attempting free on address which": BugType.UNKNOWN,  # FIXME: fix
    "AddressSanitizer: incorrect allocation size": BugType.UNKNOWN,  # FIXME: fix
    "AddressSanitizer: use-after-memory-pool-return": BugType.UNKNOWN,  # FIXME: fix
}


memsan_bug_map = { 
    "WARNING: MemorySanitizer: use-of-uninitialized-value": BugType.UNKNOWN,  # FIXME: fix
    "WARNING: MemorySanitizer: conditional jump or move": BugType.UNKNOWN,  # FIXME: fix
    "WARNING: MemorySanitizer: uninitialized memory read": BugType.UNKNOWN,  # FIXME: fix
    "WARNING: MemorySanitizer: use-of-uninitialized-stack-memory": BugType.UNKNOWN,  # FIXME: fix
    "WARNING: MemorySanitizer: use-of-uninitialized-heap-memory": BugType.UNKNOWN,  # FIXME: fix
    "WARNING: MemorySanitizer: use-of-uninitialized-global-memory": BugType.UNKNOWN,  # FIXME: fix
}


ubsan_bug_map = {
    "runtime error: signed integer overflow:": BugType.SIGNED_INTEGER_OVERFLOW,
    "runtime error: unsigned integer overflow:": BugType.UNSIGNED_INTEGER_OVERFLOW,
    "runtime error: division by zero": BugType.DIV_BY_ZERO,
    "runtime error: shift exponent": BugType.INVALID_SHIFT,  # 3, covers shift by negative, or shift exponent too large
    "runtime error: load of null pointer of type": BugType.NULL_DEREFERENCE,
    "out of bounds for type": BugType.ARRAY_OOB,
    "runtime error: load of misaligned address": BugType.MISALIGNED_PTR,
    "which is not a valid value for type": BugType.INVALID_BOOLEAN,
    "runtime error: pointer index expression with base": BugType.PTR_OVERFLOW,
    "runtime error: returning address of local variable": BugType.INVALID_RETURN,
    "through pointer to incorrect function type": BugType.INVALID_FUNCALL,
    "runtime error: variable length array bound evaluates to non-positive value": BugType.VLA_BOUND_NOT_POS,
    "through pointer to object of type": BugType.OBJ_SIZE_MISMATCH,
    "runtime error: execution reached an unreachable program point": BugType.UNREACHABLE_CODE,
    "is outside the range of representable values of type": BugType.FLOAT_CAST_OVERFLOW,
    "runtime error: misaligned address": BugType.ADDRESS_MISALIGNMENT,
    "runtime error: unaligned atomic operation": BugType.UNALIGNED_ATOMIC,
    "runtime error: type mismatch in pointer arithmetic or array indexing": BugType.TYPE_MISMATCH,
    "runtime error: implicit conversion from type": BugType.IMPLICIT_TYPE_CONVERSION,
    "runtime error: load of uninitialized value": BugType.LOAD_UNINIT_VALUE,
}


jazzer_bug_map = {
    "SEVERE: NullPointerException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: ArrayIndexOutOfBoundsException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: ClassCastException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: NumberFormatException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: IllegalArgumentException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: IllegalStateException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: IOException": BugType.UNKNOWN,  # FIXME: fix
    "SEVERE: AssertionError": BugType.UNKNOWN,  # FIXME: fix
    "== Java Exception: com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical: OS Command Injection": BugType.OS_COMMAND_INJECTION,
 }


sanitizer_type_maps = {
    Sanitizer.KASAN: kasan_bug_map,
    Sanitizer.KFENCE: kfence_bug_map,
    Sanitizer.ASAN: asan_bug_map,
    Sanitizer.MEMSAN: memsan_bug_map,
    Sanitizer.UBSAN: ubsan_bug_map,
    Sanitizer.JAZZER: jazzer_bug_map
}


def find_bug_type_for_sanitizer(sanitizer_map: dict[str, BugType], report_text: str) -> BugType:
    for key, val in sanitizer_map.items():
        if key in report_text:
            return val
    return BugType.UNKNOWN


def determine_bug_type(report: SanitizerReport) -> BugType:
    report_text = report.contents
    #  FIXME: error handling here, if something isn't found that we expect

    bug_map = sanitizer_type_maps[report.sanitizer]
    bt = find_bug_type_for_sanitizer(bug_map, report_text)

    #  Special casing things that don't work exactly with string matching
    if report.sanitizer == Sanitizer.KASAN and bt == BugType.OUT_OF_BOUNDS_WRITE:
        return bt if "Write of size" in report_text else BugType.UNKNOWN  # likely FIXME
    return bt
