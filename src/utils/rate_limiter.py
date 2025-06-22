# =============================================================================
# NewsBot Rate Limiter Module
# =============================================================================
# This module provides rate limiting functionality for API calls and commands.
# Features token bucket algorithm, per-endpoint rate limits, automatic waiting
# when rate limited, and configurable retry behavior.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger as logger

# =============================================================================
# Type Variables
# =============================================================================
T = TypeVar("T")


# =============================================================================
# Rate Limiter Main Class
# =============================================================================
class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    
    Features:
    - Token bucket implementation for smooth rate limiting
    - Configurable calls per second and burst limits
    - Automatic waiting when rate limited
    - Comprehensive statistics tracking
    """

    def __init__(
        self,
        name: str,
        calls_per_second: float = 1.0,
        burst_limit: int = 5,
        auto_wait: bool = True,
    ):
        """
        Initialize a rate limiter.

        Args:
            name: Name for this rate limiter
            calls_per_second: Maximum calls per second
            burst_limit: Maximum burst of calls allowed
            auto_wait: Whether to automatically wait when rate limited
        """
        self.name = name
        self.calls_per_second = calls_per_second
        self.burst_limit = burst_limit
        self.auto_wait = auto_wait

        # Token bucket implementation
        self.tokens = burst_limit
        self.last_refill = time.time()

        # Stats
        self.total_calls = 0
        self.waited_calls = 0
        self.total_wait_time = 0.0

        logger.debug(
            f"Rate limiter '{name}' initialized: {calls_per_second} calls/sec, burst: {burst_limit}"
        )

    # =========================================================================
    # Token Acquisition Methods
    # =========================================================================
    async def acquire(self) -> float:
        """
        Acquire a token from the bucket.

        Returns:
            Time waited in seconds
        """
        self.total_calls += 1

        # Refill tokens based on time elapsed
        now = time.time()
        time_elapsed = now - self.last_refill
        self.last_refill = now

        # Calculate tokens to add
        new_tokens = time_elapsed * self.calls_per_second
        self.tokens = min(self.burst_limit, self.tokens + new_tokens)

        # If we have a token, consume it
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0

        # Calculate time to wait
        wait_time = (1.0 - self.tokens) / self.calls_per_second

        # Update stats
        self.waited_calls += 1
        self.total_wait_time += wait_time

        if not self.auto_wait:
            # Just return the wait time, let caller handle it
            return wait_time

        # Wait for next token
        logger.debug(f"Rate limiter '{self.name}' waiting for {wait_time:.2f}s")
        await asyncio.sleep(wait_time)
        self.tokens = 0.0  # We've consumed the token we waited for
        return wait_time

    # =========================================================================
    # Statistics Methods
    # =========================================================================
    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary of stats
        """
        return {
            "name": self.name,
            "calls_per_second": self.calls_per_second,
            "burst_limit": self.burst_limit,
            "total_calls": self.total_calls,
            "waited_calls": self.waited_calls,
            "total_wait_time": round(self.total_wait_time, 2),
            "wait_percentage": round(
                100 * self.waited_calls / max(1, self.total_calls), 2
            ),
            "current_tokens": round(self.tokens, 2),
        }


# =============================================================================
# Rate Limiter Manager Class
# =============================================================================
class RateLimiterManager:
    """
    Manages multiple rate limiters for different API endpoints.
    
    Features:
    - Centralized management of multiple rate limiters
    - Default limiters for common APIs (Telegram, Discord)
    - Statistics collection across all limiters
    """

    def __init__(self):
        """Initialize the rate limiter manager."""
        self.limiters: Dict[str, RateLimiter] = {}

        # Default limiters for common APIs
        self._add_default_limiters()

    def _add_default_limiters(self):
        """Add default rate limiters for common APIs."""
        # Telegram API (30 requests per second, but we'll be conservative)
        self.add_limiter("telegram", calls_per_second=20.0, burst_limit=30)

        # Discord API (50 requests per second, but we'll be conservative)
        self.add_limiter("discord", calls_per_second=30.0, burst_limit=50)

        # General API for other services
        self.add_limiter("default", calls_per_second=5.0, burst_limit=10)

    # =========================================================================
    # Limiter Management Methods
    # =========================================================================
    def add_limiter(
        self,
        name: str,
        calls_per_second: float = 1.0,
        burst_limit: int = 5,
        auto_wait: bool = True,
    ) -> RateLimiter:
        """
        Add a new rate limiter.

        Args:
            name: Name for the rate limiter
            calls_per_second: Maximum calls per second
            burst_limit: Maximum burst of calls allowed
            auto_wait: Whether to automatically wait when rate limited

        Returns:
            The created rate limiter
        """
        limiter = RateLimiter(name, calls_per_second, burst_limit, auto_wait)
        self.limiters[name] = limiter
        return limiter

    def get_limiter(self, name: str) -> RateLimiter:
        """
        Get a rate limiter by name.

        Args:
            name: Name of the rate limiter

        Returns:
            The rate limiter
        """
        if name not in self.limiters:
            logger.warning(f"Rate limiter '{name}' not found, using default")
            return self.limiters["default"]
        return self.limiters[name]

    async def acquire(self, name: str) -> float:
        """
        Acquire a token from a rate limiter.

        Args:
            name: Name of the rate limiter

        Returns:
            Time waited in seconds
        """
        limiter = self.get_limiter(name)
        return await limiter.acquire()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all rate limiters.

        Returns:
            Dictionary of rate limiter stats
        """
        return {name: limiter.get_stats() for name, limiter in self.limiters.items()}


def rate_limited(limiter_name: str):
    """
    Decorator to apply rate limiting to a function.

    Args:
        limiter_name: Name of the rate limiter to use

    Returns:
        Decorated function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get global rate limiter manager
            from src.utils.rate_limiter import rate_limiter_manager

            # Acquire token
            await rate_limiter_manager.acquire(limiter_name)

            # Call the function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Global instance
rate_limiter_manager = RateLimiterManager()
