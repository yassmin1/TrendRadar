"""Retry helpers for API requests."""

from __future__ import annotations

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class RateLimitError(RuntimeError):
    """Raised when an API rate limit is reached."""


class AccessDeniedError(RuntimeError):
    """Raised when API credentials lack access."""


def retry_api_call():
    """Retry transient request failures with exponential backoff."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, RateLimitError)),
    )
