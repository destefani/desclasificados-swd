"""
Sliding window rate limiter for API calls.

Implements rate limiting for both requests per minute (RPM) and
tokens per minute (TPM) using a sliding window algorithm.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Tuple


logger = logging.getLogger(__name__)


@dataclass
class RateLimits:
    """Rate limit configuration."""

    requests_per_minute: int = 500
    tokens_per_minute: int = 200_000
    estimated_tokens_per_request: int = 6000


# Default rate limits for different providers
OPENAI_LIMITS = RateLimits(
    requests_per_minute=500,
    tokens_per_minute=200_000,
    estimated_tokens_per_request=6000,
)

CLAUDE_LIMITS = RateLimits(
    requests_per_minute=50,
    tokens_per_minute=400_000,
    estimated_tokens_per_request=4000,
)


class RateLimiter:
    """
    Sliding window rate limiter for API calls.

    Tracks requests and token usage over a 60-second sliding window
    to enforce RPM and TPM limits.

    Example:
        limiter = RateLimiter(RateLimits(requests_per_minute=100))

        for doc in documents:
            limiter.wait()  # Block until rate limit allows
            process(doc)

    Thread-safe for concurrent usage with ThreadPoolExecutor.
    """

    def __init__(self, limits: RateLimits | None = None):
        """
        Initialize rate limiter.

        Args:
            limits: Rate limit configuration. Defaults to OPENAI_LIMITS.
        """
        self.limits = limits or OPENAI_LIMITS
        self._request_times: Deque[float] = deque()
        self._token_usage: Deque[Tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def _cleanup_old_entries(self, now: float) -> None:
        """Remove entries older than 60 seconds from tracking."""
        while self._request_times and now - self._request_times[0] > 60:
            self._request_times.popleft()
        while self._token_usage and now - self._token_usage[0][0] > 60:
            self._token_usage.popleft()

    def _check_rpm_capacity(self, now: float) -> float | None:
        """
        Check if we have RPM capacity.

        Returns:
            None if we have capacity, otherwise seconds to wait.
        """
        if len(self._request_times) >= self.limits.requests_per_minute:
            return 60 - (now - self._request_times[0]) + 0.1
        return None

    def _check_tpm_capacity(self, now: float) -> float | None:
        """
        Check if we have TPM capacity.

        Returns:
            None if we have capacity, otherwise seconds to wait.
        """
        used_tokens = sum(tokens for _, tokens in self._token_usage)
        if used_tokens + self.limits.estimated_tokens_per_request > self.limits.tokens_per_minute:
            if self._token_usage:
                return 60 - (now - self._token_usage[0][0]) + 0.1
        return None

    def wait(self) -> None:
        """
        Wait until we have capacity within rate limits.

        Blocks the calling thread until both RPM and TPM limits allow
        for a new request. Uses exponential backoff when rate limited.
        """
        while True:
            with self._lock:
                now = time.time()
                self._cleanup_old_entries(now)

                # Check RPM
                rpm_wait = self._check_rpm_capacity(now)
                if rpm_wait is not None and rpm_wait > 0:
                    logger.debug(f"Rate limit (RPM): waiting {rpm_wait:.1f}s")
                    time.sleep(rpm_wait)
                    continue

                # Check TPM
                tpm_wait = self._check_tpm_capacity(now)
                if tpm_wait is not None and tpm_wait > 0:
                    logger.debug(f"Rate limit (TPM): waiting {tpm_wait:.1f}s")
                    time.sleep(tpm_wait)
                    continue

                # Record this request
                self._request_times.append(now)
                self._token_usage.append(
                    (now, self.limits.estimated_tokens_per_request)
                )
                return

    def record_usage(self, tokens: int) -> None:
        """
        Record actual token usage (optional, for more accurate tracking).

        Args:
            tokens: Actual tokens used in the request
        """
        with self._lock:
            if self._token_usage:
                # Update the last entry with actual usage
                timestamp, _ = self._token_usage.pop()
                self._token_usage.append((timestamp, tokens))

    def get_current_usage(self) -> dict:
        """
        Get current usage statistics.

        Returns:
            Dict with current RPM, TPM, and capacity remaining
        """
        with self._lock:
            now = time.time()
            self._cleanup_old_entries(now)

            current_rpm = len(self._request_times)
            current_tpm = sum(tokens for _, tokens in self._token_usage)

            return {
                "current_rpm": current_rpm,
                "max_rpm": self.limits.requests_per_minute,
                "rpm_remaining": self.limits.requests_per_minute - current_rpm,
                "current_tpm": current_tpm,
                "max_tpm": self.limits.tokens_per_minute,
                "tpm_remaining": self.limits.tokens_per_minute - current_tpm,
            }

    def reset(self) -> None:
        """Reset all tracking data."""
        with self._lock:
            self._request_times.clear()
            self._token_usage.clear()
