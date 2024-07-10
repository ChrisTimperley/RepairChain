from __future__ import annotations

from repairchain.models.sanitizer_report import Sanitizer

__all__ = ("determine_bug_type",)

import typing as t

from repairchain.models.bug_type import BugType

if t.TYPE_CHECKING:
    from repairchain.models.sanitizer_report import SanitizerReport

# Why yes, CLG did ask GPT to tell her what all the text that goes with each type of error
# each sanitizer can report

# NOTE: for consideration, I am not distinguishing between the different types of
# out of bounds accesses here (global, stack, etc).  Can revisit if given appropriate
# guidance from securit yfolks.
kasan_bug_map = {
    "KASan: use-after-free in": BugType.USE_AFTER_FREE,
    "KASAN: slab-out-of-bounds": BugType.OUT_OF_BOUNDS_WRITE,
    "KASan: stack-out-of-bounds": BugType.OUT_OF_BOUNDS_WRITE,
    "KASan: global-out-of-bounds": BugType.OUT_OF_BOUNDS_WRITE,
    "KASan: stack-use-after-return": BugType.USE_AFTER_RETURN_OR_SCOPE,
    "KASan: invalid-free": BugType.INVALID_FREE,
    "KASan: double-free": BugType.DOUBLE_FREE,
    "KASan: use-after-scope": BugType.USE_AFTER_RETURN_OR_SCOPE,
    "KASan: uninit-value": BugType.LOAD_UNINIT_VALUE,
    "KASan: wild-access": BugType.WILD_ACCESS,
}


kfence_bug_map = {
    "KFENCE: use-after-free": BugType.USE_AFTER_FREE,
    "KFENCE: out-of-bounds access": BugType.OUT_OF_BOUNDS_WRITE,
    "KFENCE: memory corruption detected": BugType.MEMORY_CORRUPTION,
    "KFENCE: double-free detected": BugType.DOUBLE_FREE,
    "KFENCE: invalid-free detected": BugType.INVALID_FREE,
}


asan_bug_map = {
    "AddressSanitizer: heap-buffer-overflow": BugType.OUT_OF_BOUNDS_WRITE,
    "AddressSanitizer: global-buffer-overflow": BugType.OUT_OF_BOUNDS_WRITE,
    "AddressSanitizer: stack-buffer-overflow": BugType.OUT_OF_BOUNDS_WRITE,
    "AddressSanitizer: use-after-free on address": BugType.USE_AFTER_FREE,
    "AddressSanitizer: stack-use-after-return": BugType.USE_AFTER_RETURN_OR_SCOPE,
    "AddressSanitizer: stack-use-after-scope": BugType.USE_AFTER_RETURN_OR_SCOPE,
    "AddressSanitizer: initialization-order-fiasco": BugType.INIT_ORDER_FIASCO,
    "LeakSanitizer: detected memory leaks": BugType.MEMORY_LEAK,
    "AddressSanitizer: attempting double-free": BugType.DOUBLE_FREE,
    "AddressSanitizer: attempting free on address which": BugType.INVALID_FREE,
    "AddressSanitizer: incorrect allocation size": BugType.INCORRECT_ALLOC_SIZE,
    "AddressSanitizer: use-after-memory-pool-return": BugType.USE_AFTER_RETURN_OR_SCOPE,
}


# NOTE: not distinguishing between different types of uninitialized memory
# can revisit if appropriate.
memsan_bug_map = { 
    "WARNING: MemorySanitizer: use-of-uninitialized-value": BugType.LOAD_UNINIT_VALUE,
    "WARNING: MemorySanitizer: conditional jump or move": BugType.LOAD_UNINIT_VALUE,
    "WARNING: MemorySanitizer: uninitialized memory read": BugType.LOAD_UNINIT_VALUE,
    "WARNING: MemorySanitizer: use-of-uninitialized-stack-memory": BugType.LOAD_UNINIT_VALUE,
    "WARNING: MemorySanitizer: use-of-uninitialized-heap-memory": BugType.LOAD_UNINIT_VALUE,
    "WARNING: MemorySanitizer: use-of-uninitialized-global-memory": BugType.LOAD_UNINIT_VALUE,
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
    "SEVERE: NullPointerException": BugType.NULL_DEREFERENCE,
    "SEVERE: ArrayIndexOutOfBoundsException": BugType.ARRAY_OOB,
    "SEVERE: ClassCastException": BugType.CLASS_CAST,
    "SEVERE: NumberFormatException": BugType.NUMBER_FORMAT,
    "SEVERE: IllegalArgumentException": BugType.ILLEGAL_ARGUMENT,
    "SEVERE: IllegalStateException": BugType.ILLEGAL_STATE,
    "SEVERE: IOException": BugType.IOEXCEPTION,
    "SEVERE: AssertionError": BugType.ASSERTION_ERROR,
    "com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical: OS Command Injection": BugType.OS_COMMAND_INJECTION,
 }

# FIXME: The above is the generic stuff Jazzer can find
# The Actual Jazzer CWEs per the competition are below; don't know how to 
# grok them from the sanitizer report
# CWE-22 ("Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')"): BugType.PATH_TRAVERSAL
# CWE-77 ("Improper Neutralization of Special Elements used in a Command ('Command Injection')"): BugType.COMMAND_INJECTION  # noqa: E501
# CWE-78 ("Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')"): BugType.OS_COMMAND_INJECTION,  # noqa: E501
# CWE-94 ("Improper Control of Generation of Code ('Code Injection')"): BugType.CODE_INJECTION
# CWE-190 ("Integer Overflow or Wraparound"): BugType.INTEGER_OVERFLOW_OR_WRAPAROUND
# CWE-434 ("Unrestricted Upload of File with Dangerous Type"): BugType.UNRESTRICTED_UPLOAD_OF_FILE_WITH_DANGEROUS_TYPE
# CWE-502 ("Deserialization of Untrusted Data") : BugType.DESERIALIZATION_OF_UNTRUSTED_DATA
# CWE-918 ("Server-Side Request Forgery (SSRF)"): BugType.SERVER_SIDE_REQUEST_FORGERY

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
