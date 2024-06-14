from __future__ import annotations

__all__ = ("BugType",)

import enum


class BugType(str, enum.Enum):
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
    PATH_TRAVERSAL = "path-traversal"
    SERVER_SIDE_REQUEST_FORGERY = "server-side-request-forgery"
    UNKNOWN = "unknown"
    UNRESTRICTED_UPLOAD_OF_FILE_WITH_DANGEROUS_TYPE = "unrestricted-upload-of-file-with-dangerous-type"
    USE_AFTER_FREE = "use-after-free"
