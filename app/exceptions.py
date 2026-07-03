class AutomationError(Exception):
    """Base application error."""


class NonRetriableError(AutomationError):
    """Raised when retrying is not useful."""


class RetryExhaustedError(AutomationError):
    """Raised when retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int, last_error: Exception) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error
