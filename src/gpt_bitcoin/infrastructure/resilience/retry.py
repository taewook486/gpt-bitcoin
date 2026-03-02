"""
Tenacity-based retry utilities.

This module provides configurable retry decorators for both sync and async
functions, with exponential backoff and comprehensive logging.

Example:
    ```python
    @async_retry(max_attempts=3, base_delay=1.0)
    async def fetch_data():
        response = await api_client.get("/data")
        return response
    ```
"""

from __future__ import annotations

import asyncio
import functools
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    Retrying,
    RetryError,
    before_sleep_log,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_random,
    retry_if_exception_type,
    after_log,
)
from typing_extensions import ParamSpec

from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds between retries
        exponential_multiplier: Multiplier for exponential backoff
        jitter: Whether to add random jitter to delays
        timeout: Maximum total time for all attempts (None for no limit)
        retryable_exceptions: Tuple of exception types to retry on
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_multiplier: float = 2.0
    jitter: bool = True
    timeout: float | None = None
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )


def _create_wait_strategy(config: RetryConfig):
    """Create wait strategy from config."""
    wait = wait_exponential(
        multiplier=config.exponential_multiplier,
        min=config.base_delay,
        max=config.max_delay,
    )
    if config.jitter:
        wait = wait + wait_random(0, 1)
    return wait


def _create_stop_strategy(config: RetryConfig):
    """Create stop strategy from config."""
    stop = stop_after_attempt(config.max_attempts)
    if config.timeout is not None:
        stop = stop | stop_after_delay(config.timeout)
    return stop


def sync_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_multiplier: float = 2.0,
    jitter: bool = True,
    timeout: float | None = None,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for sync functions with retry logic.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay between retries
        exponential_multiplier: Multiplier for exponential backoff
        jitter: Whether to add random jitter
        timeout: Maximum total time for all attempts
        retryable_exceptions: Exception types to retry on
        config: RetryConfig object (overrides other params if provided)

    Returns:
        Decorated function with retry logic

    Example:
        ```python
        @sync_retry(max_attempts=5, base_delay=2.0)
        def fetch_data():
            return requests.get("https://api.example.com/data")
        ```
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_multiplier=exponential_multiplier,
            jitter=jitter,
            timeout=timeout,
            retryable_exceptions=retryable_exceptions or (
                ConnectionError,
                TimeoutError,
                OSError,
            ),
        )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            retryer = Retrying(
                stop=_create_stop_strategy(config),
                wait=_create_wait_strategy(config),
                retry=retry_if_exception_type(config.retryable_exceptions),
                before_sleep=before_sleep_log(logger, logger.level),
                reraise=True,
            )

            try:
                for attempt in retryer:
                    with attempt:
                        logger.debug(
                            "Retry attempt",
                            function=func.__name__,
                            attempt=attempt.retry_state.attempt_number,
                        )
                        return func(*args, **kwargs)
            except RetryError as e:
                logger.error(
                    "All retry attempts failed",
                    function=func.__name__,
                    attempts=attempt.retry_state.attempt_number,
                    error=str(e),
                )
                raise

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_multiplier: float = 2.0,
    jitter: bool = True,
    timeout: float | None = None,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for async functions with retry logic.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay between retries
        exponential_multiplier: Multiplier for exponential backoff
        jitter: Whether to add random jitter
        timeout: Maximum total time for all attempts
        retryable_exceptions: Exception types to retry on
        config: RetryConfig object (overrides other params if provided)

    Returns:
        Decorated async function with retry logic

    Example:
        ```python
        @async_retry(max_attempts=5, base_delay=2.0)
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com") as resp:
                    return await resp.json()
        ```
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_multiplier=exponential_multiplier,
            jitter=jitter,
            timeout=timeout,
            retryable_exceptions=retryable_exceptions or (
                ConnectionError,
                TimeoutError,
                OSError,
            ),
        )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            retryer = AsyncRetrying(
                stop=_create_stop_strategy(config),
                wait=_create_wait_strategy(config),
                retry=retry_if_exception_type(config.retryable_exceptions),
                before_sleep=before_sleep_log(logger, logger.level),
                reraise=True,
            )

            try:
                async for attempt in retryer:
                    with attempt:
                        logger.debug(
                            "Async retry attempt",
                            function=func.__name__,
                            attempt=attempt.retry_state.attempt_number,
                        )
                        return await func(*args, **kwargs)
            except RetryError as e:
                logger.error(
                    "All async retry attempts failed",
                    function=func.__name__,
                    attempts=attempt.retry_state.attempt_number,
                    error=str(e),
                )
                raise

        return wrapper

    return decorator
