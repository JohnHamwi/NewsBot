"""
Circuit Breaker Pattern for NewsBot

This module provides circuit breaker functionality to protect against cascading failures
when integrating with external services like Telegram and APIs.
"""

import asyncio
import datetime
import enum
import time
from typing import Any, Callable, Optional

from src.utils.base_logger import base_logger as logger


class CircuitState(enum.Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Service calls blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service is healthy


class CircuitBreaker:
    """
    Implements the circuit breaker pattern for external service calls.

    This pattern helps prevent cascading failures by failing fast when a service
    is experiencing problems. After a threshold of failures, the circuit opens
    and prevents further calls until a timeout period has passed.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_success_threshold: int = 1,
        reset_timeout: int = 300,
    ):
        """
        Initialize a new circuit breaker.

        Args:
            name: Name of the protected service
            failure_threshold: Number of failures before circuit opens
            recovery_timeout: Seconds to wait before testing recovery
            half_open_success_threshold: Successful calls needed to close circuit
            reset_timeout: Maximum time in seconds before auto-reset
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self.reset_timeout = reset_timeout

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[datetime.datetime] = None
        self.last_state_change: datetime.datetime = datetime.datetime.now()

        # Statistics
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.last_error = None

        logger.debug(f"Circuit breaker for {self.name} initialized")

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed based on circuit state.

        Returns:
            bool: Whether request should be allowed
        """
        now = datetime.datetime.now()

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            elapsed = (now - self.last_state_change).total_seconds()
            if elapsed > self.recovery_timeout:
                self._transition_to_half_open()
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # In half-open state, we only allow a limited number of test requests
            return True

        return True

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.datetime.now()
        logger.warning(f"Circuit breaker for {self.name} transitioned to OPEN state")

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.datetime.now()
        self.failures = 0
        logger.info(f"Circuit breaker for {self.name} transitioned to HALF_OPEN state")

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.datetime.now()
        self.failures = 0
        logger.info(f"Circuit breaker for {self.name} transitioned to CLOSED state")

    def record_success(self) -> None:
        """Record a successful service call."""
        self.successful_calls += 1
        self.total_calls += 1

        if self.state == CircuitState.HALF_OPEN:
            # If we've had enough successful calls in half-open state, close the circuit
            if self.successful_calls >= self.half_open_success_threshold:
                self._transition_to_closed()

    def record_failure(self, error: Exception) -> None:
        """Record a failed service call."""
        self.failures += 1
        self.failed_calls += 1
        self.total_calls += 1
        self.last_failure_time = datetime.datetime.now()
        self.last_error = error

        if self.state == CircuitState.CLOSED:
            # If we've hit the failure threshold, open the circuit
            if self.failures >= self.failure_threshold:
                self._transition_to_open()

        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state returns us to open state
            self._transition_to_open()

    def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function call

        Raises:
            CircuitOpenError: If the circuit is open
            Exception: Any exception from the function
        """
        if not self.allow_request():
            raise CircuitOpenError(f"Circuit for {self.name} is open")

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    async def execute_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute an async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the async function call

        Raises:
            CircuitOpenError: If the circuit is open
            Exception: Any exception from the function
        """
        if not self.allow_request():
            raise CircuitOpenError(f"Circuit for {self.name} is open")

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    def reset(self) -> None:
        """Reset the circuit breaker to closed state and clear statistics."""
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = None
        self.last_state_change = datetime.datetime.now()
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.last_error = None
        logger.info(f"Circuit breaker for {self.name} has been reset")

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            dict: Statistics about circuit breaker
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "last_state_change": self.last_state_change,
            "last_failure_time": self.last_failure_time,
            "last_error": str(self.last_error) if self.last_error else None,
        }


class CircuitOpenError(Exception):
    """Exception raised when a circuit is open and a request is attempted."""
