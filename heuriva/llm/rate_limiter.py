"""
Rate limiting for LLM API calls.

This module provides thread-safe rate limiting to prevent exceeding API quotas.

## Configuration

Set these environment variables in your .env file:

    # Maximum calls per minute (rolling 60-second window)
    LLM_MAX_CALLS_PER_MINUTE=15

    # Minimum seconds between consecutive calls
    LLM_MIN_DELAY_BETWEEN_CALLS=0

## Usage

The rate limiter is automatically used by LLM providers:

    from heuriva.llm import get_llm_provider

    provider = get_llm_provider()
    # Rate limiting is automatically applied
    result = provider.analyze_page(html, heuristics)

## How It Works

1. **Calls Per Minute (CPM)**: Tracks all calls in a rolling 60-second window
   - If at limit, waits until oldest call expires (falls out of window)
   - Example: 15 CPM allows bursts of 15, then waits

2. **Minimum Delay**: Enforces fixed delay between consecutive calls
   - Simpler but less bursty than CPM
   - Example: 4s delay = max 15 calls/minute, evenly spaced

3. **Combined**: Both limits can be active simultaneously
   - The stricter limit applies
   - Example: 60 CPM + 1s delay = max 60 calls/min, minimum 1s apart

## Examples

**Gemini Free Tier (15 RPM):**
    LLM_MAX_CALLS_PER_MINUTE=15
    LLM_MIN_DELAY_BETWEEN_CALLS=0

**Gemini Pay-as-you-go (60+ RPM):**
    LLM_MAX_CALLS_PER_MINUTE=60
    LLM_MIN_DELAY_BETWEEN_CALLS=0

**Conservative approach (15 RPM, evenly spaced):**
    LLM_MAX_CALLS_PER_MINUTE=0
    LLM_MIN_DELAY_BETWEEN_CALLS=4.0

**Hybrid (burst allowed, but rate-limited):**
    LLM_MAX_CALLS_PER_MINUTE=60
    LLM_MIN_DELAY_BETWEEN_CALLS=1.0
"""

import time
from collections import deque
from threading import Lock

from django.conf import settings


class RateLimiter:
    """
    Thread-safe rate limiter for LLM API calls.

    Supports two modes:
    1. Calls per minute limit: Ensures max N calls per rolling minute window
    2. Minimum delay: Ensures minimum delay between consecutive calls
    """

    def __init__(
        self,
        max_calls_per_minute: int | None = None,
        min_delay_between_calls: float | None = None,
    ):
        """
        Initialize rate limiter.

        Args:
            max_calls_per_minute: Maximum number of calls allowed per minute (rolling window)
            min_delay_between_calls: Minimum delay in seconds between consecutive calls
        """
        self.max_calls_per_minute = (
            max_calls_per_minute or settings.LLM_MAX_CALLS_PER_MINUTE
        )
        self.min_delay = min_delay_between_calls or settings.LLM_MIN_DELAY_BETWEEN_CALLS

        # Thread-safe queue to track call timestamps
        self._call_times: deque[float] = deque()
        self._lock = Lock()
        self._last_call_time: float | None = None

    def wait_if_needed(self) -> None:
        """
        Block until it's safe to make another API call.

        This method is thread-safe and will block if rate limits would be exceeded.
        """
        with self._lock:
            current_time = time.time()

            # Apply minimum delay between calls
            if self.min_delay > 0 and self._last_call_time is not None:
                time_since_last_call = current_time - self._last_call_time
                if time_since_last_call < self.min_delay:
                    sleep_time = self.min_delay - time_since_last_call
                    time.sleep(sleep_time)
                    current_time = time.time()

            # Apply calls per minute limit (rolling window)
            if self.max_calls_per_minute > 0:
                # Remove calls older than 1 minute
                cutoff_time = current_time - 60.0
                while self._call_times and self._call_times[0] < cutoff_time:
                    self._call_times.popleft()

                # If we've hit the limit, wait until the oldest call expires
                if len(self._call_times) >= self.max_calls_per_minute:
                    oldest_call = self._call_times[0]
                    sleep_time = 60.0 - (current_time - oldest_call)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        current_time = time.time()

                    # Clean up again after sleeping
                    cutoff_time = current_time - 60.0
                    while self._call_times and self._call_times[0] < cutoff_time:
                        self._call_times.popleft()

            # Record this call
            self._call_times.append(current_time)
            self._last_call_time = current_time

    def reset(self) -> None:
        """Reset the rate limiter state."""
        with self._lock:
            self._call_times.clear()
            self._last_call_time = None

    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.

        Returns:
            Dictionary with calls in last minute and time until next available slot
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - 60.0

            # Clean old calls
            while self._call_times and self._call_times[0] < cutoff_time:
                self._call_times.popleft()

            calls_in_last_minute = len(self._call_times)

            # Calculate wait time
            wait_time = 0.0
            if self._last_call_time and self.min_delay > 0:
                time_since_last = current_time - self._last_call_time
                if time_since_last < self.min_delay:
                    wait_time = max(wait_time, self.min_delay - time_since_last)

            if (
                self.max_calls_per_minute > 0
                and calls_in_last_minute >= self.max_calls_per_minute
                and self._call_times
            ):
                oldest_call = self._call_times[0]
                time_until_oldest_expires = 60.0 - (current_time - oldest_call)
                wait_time = max(wait_time, time_until_oldest_expires)

            return {
                "calls_in_last_minute": calls_in_last_minute,
                "max_calls_per_minute": self.max_calls_per_minute,
                "min_delay_between_calls": self.min_delay,
                "wait_time_seconds": max(0, wait_time),
                "can_call_now": wait_time <= 0,
            }
