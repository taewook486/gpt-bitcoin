"""
Circuit breaker pattern implementation.

The circuit breaker prevents cascading failures by temporarily blocking
calls to a failing service, allowing it time to recover.

States:
- CLOSED: Normal operation, calls pass through
- OPEN: Failing state, calls are blocked immediately
- HALF_OPEN: Recovery state, allows test calls to check if service recovered

Example:
    ```python
    circuit = CircuitBreaker("upbit-api", failure_threshold=5, recovery_timeout=60)

    @circuit.protect
    async def call_upbit():
        async with upbit_client as client:
            return await client.get_balances()
    ```
"""

from __future__ import annotations

import asyncio
import functools
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

from typing_extensions import ParamSpec

from gpt_bitcoin.infrastructure.exceptions import CircuitBreakerOpenError
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, calls blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: float | None = None
    last_state_change: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Circuit breaker for protecting external service calls.

    Implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Calls blocked, service marked as unhealthy
    - HALF_OPEN: Testing if service has recovered

    Args:
        name: Identifier for this circuit breaker (for logging)
        failure_threshold: Number of consecutive failures to trigger OPEN
        recovery_timeout: Seconds to wait before trying HALF_OPEN
        success_threshold: Consecutive successes in HALF_OPEN to close
        half_open_max_calls: Max test calls allowed in HALF_OPEN

    Example:
        ```python
        circuit = CircuitBreaker("glm-api", failure_threshold=5)

        # As decorator
        @circuit.protect
        async def call_glm():
            return await glm_client.analyze_text(...)

        # As context manager
        async with circuit:
            result = await glm_client.analyze_text(...)
        ```
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        logger.info(
            "Circuit breaker initialized",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        """Current circuit breaker state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Circuit breaker statistics."""
        return self._stats

    @property
    def is_closed(self) -> bool:
        """Check if circuit is in normal operation."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is blocking calls."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is testing recovery."""
        return self._state == CircuitState.HALF_OPEN

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on state."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._stats.last_failure_time is None:
                return False

            elapsed = time.time() - self._stats.last_failure_time
            if elapsed >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            # Allow limited test calls
            return self._half_open_calls < self.half_open_max_calls

        return False

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        self._stats.last_state_change = time.time()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

        logger.warning(
            "Circuit breaker state changed",
            name=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
        )

    def record_success(self) -> None:
        """Record a successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.consecutive_failures = 0

        if self._state == CircuitState.HALF_OPEN:
            if self._stats.successful_calls >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                logger.info(
                    "Circuit breaker recovered",
                    name=self.name,
                )

        logger.debug(
            "Circuit breaker recorded success",
            name=self.name,
            state=self._state.value,
        )

    def record_failure(self) -> None:
        """Record a failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.consecutive_failures += 1
        self._stats.last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                "Circuit breaker reopened after failure in HALF_OPEN",
                name=self.name,
            )
        elif self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
                logger.error(
                    "Circuit breaker opened after consecutive failures",
                    name=self.name,
                    consecutive_failures=self._stats.consecutive_failures,
                )

    def protect(self, func: Callable[P, T]) -> Callable[P, T]:
        """
        Decorator to protect a function with circuit breaker.

        Args:
            func: Function to protect

        Returns:
            Protected function

        Example:
            ```python
            circuit = CircuitBreaker("api")

            @circuit.protect
            async def call_api():
                return await client.get("/")
            ```
        """
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return await self._async_call(func, *args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return self._sync_call(func, *args, **kwargs)

            return sync_wrapper

    async def _async_call(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute async function with circuit breaker protection."""
        async with self._lock:
            if not self._should_allow_request():
                raise CircuitBreakerOpenError(
                    service_name=self.name,
                    recovery_time=self._stats.last_failure_time + self.recovery_timeout
                    if self._stats.last_failure_time
                    else None,
                )

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self.record_success()
            return result
        except Exception as e:
            async with self._lock:
                self.record_failure()
            raise

    def _sync_call(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute sync function with circuit breaker protection."""
        if not self._should_allow_request():
            raise CircuitBreakerOpenError(
                service_name=self.name,
                recovery_time=self._stats.last_failure_time + self.recovery_timeout
                if self._stats.last_failure_time
                else None,
            )

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    async def __aenter__(self) -> "CircuitBreaker":
        """Async context manager entry."""
        async with self._lock:
            if not self._should_allow_request():
                raise CircuitBreakerOpenError(
                    service_name=self.name,
                    recovery_time=self._stats.last_failure_time + self.recovery_timeout
                    if self._stats.last_failure_time
                    else None,
                )

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        async with self._lock:
            if exc_type is None:
                self.record_success()
            else:
                self.record_failure()

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        logger.info("Circuit breaker reset", name=self.name)


# =============================================================================
# Pre-configured Circuit Breakers
# =============================================================================

# Circuit breaker for GLM API
glm_circuit = CircuitBreaker(
    name="glm-api",
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=2,
)

# Circuit breaker for Upbit API
upbit_circuit = CircuitBreaker(
    name="upbit-api",
    failure_threshold=5,
    recovery_timeout=30.0,
    success_threshold=2,
)

# Circuit breaker for SerpApi
serpapi_circuit = CircuitBreaker(
    name="serpapi",
    failure_threshold=3,
    recovery_timeout=120.0,
    success_threshold=1,
)
