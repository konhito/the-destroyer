from app.exceptions import NonRetriableError, RetryExhaustedError
from app.retry import RetryConfig, run_with_retry


def test_run_with_retry_retries_then_succeeds() -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("retry me")
        return "ok"

    result = run_with_retry(flaky, RetryConfig(max_attempts=3), sleep=sleeps.append)

    assert result.value == "ok"
    assert result.attempts == 3
    assert sleeps == [5.0, 10.0]


def test_run_with_retry_stops_on_non_retriable_error() -> None:
    def boom() -> str:
        raise NonRetriableError("stop")

    try:
        run_with_retry(boom, RetryConfig(max_attempts=6))
    except NonRetriableError as exc:
        assert str(exc) == "stop"
    else:
        raise AssertionError("Expected NonRetriableError")


def test_run_with_retry_raises_retry_exhausted() -> None:
    def boom() -> str:
        raise RuntimeError("keep failing")

    try:
        run_with_retry(boom, RetryConfig(max_attempts=2), sleep=lambda _: None)
    except RetryExhaustedError as exc:
        assert exc.attempts == 2
        assert "keep failing" in str(exc.last_error)
    else:
        raise AssertionError("Expected RetryExhaustedError")
