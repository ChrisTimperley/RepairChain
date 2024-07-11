from __future__ import annotations

__all__ = ("BugType",)

import enum


class Sanitizer(enum.StrEnum):
    UNKNOWN = "unknown"
    KASAN = "kasan"
    KFENCE = "kfence"
    ASAN = "asan"
    MEMSAN = "msan"
    UBSAN = "ubsan"
    JAZZER = "jazzer"


class BugType(enum.StrEnum):
    ADDRESS_MISALIGNMENT = "address-misalignment"
    ARRAY_OOB = "array-out-of-bounds-access"
    ASSERTION_ERROR = "assertion-error"
    CLASS_CAST = "class-cast-exception"
    CODE_INJECTION = "code-injection"
    COMMAND_INJECTION = "command-injection"
    DESERIALIZATION_OF_UNTRUSTED_DATA = "deserialization-of-untrusted-data"
    DIV_BY_ZERO = "division-by-zero"
    DOUBLE_FREE = "double-free"
    FLOAT_CAST_OVERFLOW = "floating-point-cast-overflow"
    ILLEGAL_ARGUMENT = "illegal-argument-exception"
    ILLEGAL_STATE = "illegal-state-exception"
    IMPROPER_RESTRICTION_OF_OPERATIONS_WITHIN_THE_BOUNDS = "improper-restriction-of-operations-within-the-bounds"
    IMPLICIT_TYPE_CONVERSION = "implicit-type-conversion"
    INCORRECT_ALLOC_SIZE = "incorrect-allocation-size"
    INIT_ORDER_FIASCO = "initialization-order-fiasco"
    INTEGER_OVERFLOW_OR_WRAPAROUND = "integer-overflow-or-wraparound"
    INVALID_BOOLEAN = "invalid-boolean-value"
    INVALID_FREE = "invalid-free"  # free of uninitialized memory, not double-free
    INVALID_FUNCALL = "invalid-function-call"
    INVALID_RETURN = "invalid-return-addr-local-variable"
    INVALID_SHIFT = "invalid-shift"
    IOEXCEPTION = "IOException"
    LOAD_UNINIT_VALUE = "load-uninitialized-value"
    MEMORY_CORRUPTION = "memory-corruption"
    MEMORY_LEAK = "memory-leak"
    MISALIGNED_PTR = "load-of-misaligned-ptr-address"
    NULL_DEREFERENCE = "null-dereference"
    NUMBER_FORMAT = "number-format-exception"
    OBJ_SIZE_MISMATCH = "object-size-mismatch"
    OS_COMMAND_INJECTION = "os-command-injection"
    OUT_OF_BOUNDS_READ = "out-of-bounds-read"
    OUT_OF_BOUNDS_WRITE = "out-of-bounds-write"
    PATH_TRAVERSAL = "path-traversal"
    PTR_OVERFLOW = "pointer-overflow"
    SERVER_SIDE_REQUEST_FORGERY = "server-side-request-forgery"
    SIGNED_INTEGER_OVERFLOW = "signed-integer-overflow"
    TYPE_MISMATCH = "type-mismatch"  # Pointer arithmetic or array indexing
    UNALIGNED_ATOMIC = "unaligned-atomic-operation"
    UNKNOWN = "unknown"
    UNREACHABLE_CODE = "unreachable-point-reached"
    UNRESTRICTED_UPLOAD_OF_FILE_WITH_DANGEROUS_TYPE = "unrestricted-upload-of-file-with-dangerous-type"
    USE_AFTER_FREE = "use-after-free"
    USE_AFTER_RETURN_OR_SCOPE = "use-after-return-or-scope"
    UNSIGNED_INTEGER_OVERFLOW = "unsigned-integer-overflow"
    VLA_BOUND_NOT_POS = "variable-length-array-bound-not-positive"
    WILD_ACCESS = "wild-memory-access"

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
    "File read/write hook path": BugType.PATH_TRAVERSAL,
    "Integer Overflow(addition) detected": BugType.INTEGER_OVERFLOW_OR_WRAPAROUND,
    "Server Side Request Forgery (SSRF)": BugType.SERVER_SIDE_REQUEST_FORGERY,
 }

# FIXME: The above is the generic stuff Jazzer can find
# The Actual Jazzer CWEs per the competition are below; don't know how to
# grok them from the sanitizer report
# CWE-22 ("Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')"): BugType.PATH_TRAVERSAL
# CWE-77 ("Improper Neutralization of Special Elements used in a Command ('Command Injection')"): BugType.COMMAND_INJECTION  # noqa: E501
# CWE-94 ("Improper Control of Generation of Code ('Code Injection')"): BugType.CODE_INJECTION
# CWE-434 ("Unrestricted Upload of File with Dangerous Type"): BugType.UNRESTRICTED_UPLOAD_OF_FILE_WITH_DANGEROUS_TYPE
# CWE-502 ("Deserialization of Untrusted Data") : BugType.DESERIALIZATION_OF_UNTRUSTED_DATA

sanitizer_type_maps = {
    Sanitizer.KASAN: kasan_bug_map,
    Sanitizer.KFENCE: kfence_bug_map,
    Sanitizer.ASAN: asan_bug_map,
    Sanitizer.MEMSAN: memsan_bug_map,
    Sanitizer.UBSAN: ubsan_bug_map,
    Sanitizer.JAZZER: jazzer_bug_map,
}


def _find_bug_type_for_sanitizer(
    report_text: str,
    sanitizer: Sanitizer,
) -> BugType:
    if sanitizer not in sanitizer_type_maps:
        return BugType.UNKNOWN

    sanitizer_map = sanitizer_type_maps[sanitizer]
    for key, val in sanitizer_map.items():
        if key in report_text:
            return val

    return BugType.UNKNOWN


def determine_bug_type(report_text: str, sanitizer: Sanitizer) -> BugType:
    bug_type = _find_bug_type_for_sanitizer(report_text, sanitizer)

    #  Special casing things that don't work exactly with string matching
    if sanitizer == Sanitizer.KASAN and bug_type == BugType.OUT_OF_BOUNDS_WRITE:
        return bug_type if "Write of size" in report_text else BugType.UNKNOWN  # likely FIXME

    return bug_type
