"""Finite typed acquisition budgets; one retry layer, no scheduling policy."""

import math
from dataclasses import dataclass

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.config import IngestionSettings
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_cap_seconds: float = 4.0
    phase_timeout_seconds: float = 10.0
    attempt_timeout_seconds: float = 30.0
    operation_timeout_seconds: float = 93.0

    def __post_init__(self) -> None:
        positive = (
            self.phase_timeout_seconds,
            self.attempt_timeout_seconds,
            self.operation_timeout_seconds,
            self.backoff_cap_seconds,
        )
        if (
            type(self.max_attempts) is not int
            or self.max_attempts < 1
            or any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 for v in positive)
            or type(self.backoff_seconds) not in (float, int)
            or not math.isfinite(self.backoff_seconds)
            or self.backoff_seconds < 0
        ):
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)

    @classmethod
    def from_settings(cls, settings: IngestionSettings) -> "RetryPolicy":
        return cls(
            max_attempts=settings.max_attempts,
            backoff_seconds=settings.backoff_seconds,
            phase_timeout_seconds=settings.timeout_seconds,
        )

    def delay(self, failed_attempt: int) -> float:
        # Saturating multiplication avoids enormous exponents for user settings.
        delay = min(self.backoff_seconds, self.backoff_cap_seconds)
        for _ in range(failed_attempt - 1):
            delay = min(delay * 2, self.backoff_cap_seconds)
            if delay == self.backoff_cap_seconds or delay == 0:
                break
        return delay
