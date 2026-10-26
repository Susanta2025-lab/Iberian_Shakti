"""Safe execution errors: codes cross boundaries, chained causes stay diagnostic.

Never log causes, tracebacks, or library exception strings. ``reason`` is a
closed execution detail; ``code`` uses the shared Stage 2 error vocabulary.
"""

from enum import StrEnum

from iberian_shakti.contracts.ingestion import ErrorCode


class FailureReason(StrEnum):
    CONFIGURATION = "invalid_configuration"
    SOURCE_REQUEST = "invalid_source_request"
    SCHEME = "unsupported_scheme"
    LOCATOR = "invalid_locator"
    CONNECTION = "connection_failure"
    CONNECT_TIMEOUT = "connect_timeout"
    READ_TIMEOUT = "read_timeout"
    WRITE_TIMEOUT = "write_timeout"
    POOL_TIMEOUT = "pool_timeout"
    PROTOCOL = "incomplete_transport"
    TLS = "tls_verification_failure"
    HTTP = "http_failure"
    RATE_LIMIT = "rate_limited"
    DEADLINE = "deadline_exceeded"
    SIZE = "size_limit"
    ENCODING = "unsupported_encoding"
    MISSING = "file_missing"
    UNREADABLE = "file_unreadable"
    PERMISSION = "archive_permission"
    ARCHIVE_IO = "archive_io"
    INTEGRITY = "archive_integrity"
    METADATA = "metadata_persistence"
    PATH = "path_validation"
    REPLAY = "replay_integrity"


class ExecutionError(Exception):
    """Only controlled enum values appear in str/repr; causes are never formatted."""

    def __init__(self, code: ErrorCode, reason: FailureReason, *, retryable: bool = False):
        self.code = code
        self.reason = reason
        self.retryable = retryable
        super().__init__(f"{code.value}: {reason.value}")


class ArchiveError(ExecutionError):
    """Archive failure; outside every transport retry loop."""


class ReplayError(ExecutionError):
    """Verified replay failed; no replacement acquisition is attempted."""
