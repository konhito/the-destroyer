from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from app.exceptions import NonRetriableError, RetryExhaustedError

T = TypeVar("T")


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int = 6
    initial_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 300.0


@dataclass(slots=True)
class RetryOutcome(Generic[T]):
    value: T
    attempts: int


def run_with_retry(
    operation: Callable[[], T],
    config: RetryConfig,
    *,
    should_retry: Callable[[Exception], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> RetryOutcome[T]:
    delay = config.initial_delay_seconds
    attempt = 0
    should_retry = should_retry or (lambda exc: not isinstance(exc, NonRetriableError))

    while True:
        attempt += 1
        try:
            return RetryOutcome(value=operation(), attempts=attempt)
        except NonRetriableError:
            raise
        except Exception as exc:
            if attempt >= config.max_attempts or not should_retry(exc):
                raise RetryExhaustedError(
                    f"Operation failed after {attempt} attempts",
                    attempts=attempt,
                    last_error=exc,
                ) from exc
            sleep(delay)
            delay = min(delay * config.backoff_multiplier, config.max_delay_seconds)
