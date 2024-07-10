from __future__ import annotations

__all__ = ("BugType",)

import enum


class BugType(enum.StrEnum):
    CODE_INJECTION = "code-injection"
    COMMAND_INJECTION = "command-injection"
    DESERIALIZATION_OF_UNTRUSTED_DATA = "deserialization-of-untrusted-data"
    DOUBLE_FREE = "double-free"
    IMPROPER_RESTRICTION_OF_OPERATIONS_WITHIN_THE_BOUNDS = "improper-restriction-of-operations-within-the-bounds"
    INTEGER_OVERFLOW_OR_WRAPAROUND = "integer-overflow-or-wraparound"
    NULL_DEREFERENCE = "null-dereference"
    OS_COMMAND_INJECTION = "os-command-injection"
    OUT_OF_BOUNDS_READ = "out-of-bounds-read"
    OUT_OF_BOUNDS_WRITE = "out-of-bounds-write"
    ARRAY_OOB = "array-out-of-bounds-access"
    PATH_TRAVERSAL = "path-traversal"
    SERVER_SIDE_REQUEST_FORGERY = "server-side-request-forgery"
    UNKNOWN = "unknown"
    UNRESTRICTED_UPLOAD_OF_FILE_WITH_DANGEROUS_TYPE = "unrestricted-upload-of-file-with-dangerous-type"
    USE_AFTER_FREE = "use-after-free"
    SIGNED_INTEGER_OVERFLOW = "signed-integer-overflow"
    UNSIGNED_INTEGER_OVERFLOW = "unsigned-integer-overflow"
    DIV_BY_ZERO = "division-by-zero"
    INVALID_SHIFT = "invalid-shift"
    MISALIGNED_PTR = "load-of-misaligned-ptr-address"
    INVALID_BOOLEAN = "invalid-boolean-value"
    PTR_OVERFLOW = "pointer-overflow"
    INVALID_RETURN = "invalid-return-addr-local-variable"
    INVALID_FUNCALL = "invalid-function-call"
    VLA_BOUND_NOT_POS = "variable-length-array-bound-not-positive"
    OBJ_SIZE_MISMATCH = "object-size-mismatch"
    UNREACHABLE_CODE = "unreachable-point-reached"
    FLOAT_CAST_OVERFLOW = "floating-point-cast-overflow"
    ADDRESS_MISALIGNMENT = "address-misalignment"
    UNALIGNED_ATOMIC = "unaligned-atomic-operation"
    TYPE_MISMATCH = "type-mismatch"  # Pointer arithmetic or array indexing
    IMPLICIT_TYPE_CONVERSION = "implicit-type-conversion"
    LOAD_UNINIT_VALUE = "load-uninitialized-value"
