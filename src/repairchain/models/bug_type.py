from __future__ import annotations

__all__ = ("BugType",)

from enum import Enum


class BugType(Enum):
    CODE_INJECTION = "CWE-94", "code-injection"
    COMMAND_INJECTION = "CWE-77", "command-injection"
    DESERIALIZATION_OF_UNTRUSTED_DATA = "CWE-502", "deserialization-of-untrusted-data"
    DOUBLE_FREE = "CWE-415", "double-free"
    IMPROPER_RESTRICTION_OF_OPERATIONS_WITHIN_THE_BOUNDS = (
    "CWE-119",
    "improper-restriction-of-operations-within-the-bounds",
    )
    INTEGER_OVERFLOW_OR_WRAPAROUND = "CWE-190", "integer-overflow-or-wraparound"
    NULL_DEREFERENCE = "CWE-476", "null-dereference"
    OS_COMMAND_INJECTION = "CWE-78", "os-command-injection"
    OUT_OF_BOUNDS_READ = "CWE-125", "out-of-bounds-read"
    OUT_OF_BOUNDS_WRITE = "CWE-787", "out-of-bounds-write"
    PATH_TRAVERSAL = "CWE-22", "path-traversal"
    SERVER_SIDE_REQUEST_FORGERY = "CWE-918", "server-side-request-forgery"
    UNKNOWN = "unknown", "unknown"
    UNRESTRICTED_UPLOAD_OF_FILE_WITH_DANGEROUS_TYPE = "CWE-434", "unrestricted-upload-of-file-with-dangerous-type"
    USE_AFTER_FREE = "CWE-416", "use-after-free"
