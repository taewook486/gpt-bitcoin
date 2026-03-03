"""
Trading Metrics.

This module provides domain-specific trading metrics including GLM API metrics,
Upbit API metrics, trading decision metrics, and portfolio metrics.
"""
from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from gpt_bitcoin.infrastructure.observability.prometheus_exporter import (
    get_metrics_server,
    PrometheusConfig,
)

if TYPE_CHECKING:
    from typing import ParamSpec

logger = logging.getLogger(__name__)

# Global trading metrics instance
_trading_metrics: TradingMetrics | None = None

# Type variables for decorator
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class TradingMetricsConfig:
    """Configuration for trading metrics.

    Attributes:
        enable_glm_metrics: Enable GLM API metrics (default: True)
        enable_upbit_metrics: Enable Upbit API metrics (default: True)
        enable_portfolio_metrics: Enable portfolio metrics (default: True)
        enable_trading_metrics: Enable trading decision metrics (default: True)
    """

    enable_glm_metrics: bool = True
    enable_upbit_metrics: bool = True
    enable_portfolio_metrics: bool = True
    enable_trading_metrics: bool = True


class TradingMetrics:
    """Domain-specific trading metrics for the GPT Bitcoin Auto-Trading System.

    This class provides metrics for monitoring:
    - GLM API usage (tokens, cost)
    - Upbit API requests
    - Trading decision performance
    - Portfolio value and P&L
    """

    def __init__(self, config: TradingMetricsConfig | None = None) -> None:
        """Initialize trading metrics.

        Args:
            config: Optional trading metrics configuration
        """
        self._config = config or TradingMetricsConfig()
        server = get_metrics_server()

        # GLM API metrics
        if self._config.enable_glm_metrics:
            self._glm_tokens_counter = server.register_counter(
                name="glm_tokens_used_total",
                description="Total number of GLM tokens used",
                labelnames=("model",),
            )

            self._glm_cost_gauge = server.register_gauge(
                name="glm_api_cost_krw",
                description="Current GLM API cost in KRW",
                labelnames=("model",),
            )
        else:
            self._glm_tokens_counter = None  # type: ignore
            self._glm_cost_gauge = None  # type: ignore

        # Upbit API metrics
        if self._config.enable_upbit_metrics:
            self._upbit_requests_counter = server.register_counter(
                name="upbit_api_requests_total",
                description="Total number of Upbit API requests",
                labelnames=("endpoint", "method", "status"),
            )
        else:
            self._upbit_requests_counter = None  # type: ignore

        # Trading decision metrics
        if self._config.enable_trading_metrics:
            self._trading_duration_histogram = server.register_histogram(
                name="trading_decision_duration_seconds",
                description="Duration of trading decision making in seconds",
                labelnames=("decision",),
                buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0, 10.0),
            )
        else:
            self._trading_duration_histogram = None  # type: ignore

        # Portfolio metrics
        if self._config.enable_portfolio_metrics:
            self._portfolio_value_gauge = server.register_gauge(
                name="portfolio_value_krw",
                description="Current portfolio value in KRW",
            )

            self._trading_pnl_gauge = server.register_gauge(
                name="trading_pnl_percentage",
                description="Current trading profit/loss percentage",
            )
        else:
            self._portfolio_value_gauge = None  # type: ignore
            self._trading_pnl_gauge = None  # type: ignore

        logger.info("Trading metrics initialized")

    def increment_glm_tokens(self, tokens: int, model: str = "glm-4") -> None:
        """Increment GLM token usage counter.

        Args:
            tokens: Number of tokens used
            model: GLM model name (default: glm-4)
        """
        if self._config.enable_glm_metrics and self._glm_tokens_counter:
            self._glm_tokens_counter.labels(model=model).inc(tokens)
            logger.debug(f"Incremented GLM tokens: {tokens} for model {model}")

    def set_glm_cost(self, cost_krw: float, model: str = "glm-4") -> None:
        """Set GLM API cost gauge.

        Args:
            cost_krw: Cost in KRW
            model: GLM model name (default: glm-4)
        """
        if self._config.enable_glm_metrics and self._glm_cost_gauge:
            self._glm_cost_gauge.labels(model=model).set(cost_krw)
            logger.debug(f"Set GLM cost: {cost_krw} KRW for model {model}")

    def increment_upbit_requests(
        self,
        endpoint: str,
        method: str = "GET",
        status: str = "200",
    ) -> None:
        """Increment Upbit API request counter.

        Args:
            endpoint: API endpoint path
            method: HTTP method (default: GET)
            status: HTTP status code (default: 200)
        """
        if self._config.enable_upbit_metrics and self._upbit_requests_counter:
            self._upbit_requests_counter.labels(
                endpoint=endpoint,
                method=method,
                status=status,
            ).inc()
            logger.debug(f"Incremented Upbit request: {method} {endpoint} ({status})")

    def observe_trading_decision_duration(
        self,
        duration_seconds: float,
        decision: str,
    ) -> None:
        """Observe trading decision duration.

        Args:
            duration_seconds: Duration in seconds
            decision: Trading decision (buy, sell, hold)
        """
        if self._config.enable_trading_metrics and self._trading_duration_histogram:
            self._trading_duration_histogram.labels(decision=decision).observe(
                duration_seconds
            )
            logger.debug(
                f"Observed trading decision duration: {duration_seconds}s for {decision}"
            )

    def set_portfolio_value(self, value_krw: float) -> None:
        """Set portfolio value gauge.

        Args:
            value_krw: Portfolio value in KRW
        """
        if self._config.enable_portfolio_metrics and self._portfolio_value_gauge:
            self._portfolio_value_gauge.set(value_krw)
            logger.debug(f"Set portfolio value: {value_krw} KRW")

    def set_trading_pnl(self, pnl_percentage: float) -> None:
        """Set trading P&L gauge.

        Args:
            pnl_percentage: Profit/loss percentage
        """
        if self._config.enable_portfolio_metrics and self._trading_pnl_gauge:
            self._trading_pnl_gauge.set(pnl_percentage)
            logger.debug(f"Set trading P&L: {pnl_percentage}%")

    def get_metrics_output(self) -> str:
        """Get metrics output in Prometheus text format.

        Returns:
            Metrics output as string
        """
        server = get_metrics_server()
        return server.get_metrics_output()


def get_trading_metrics(
    config: TradingMetricsConfig | None = None,
) -> TradingMetrics:
    """Get or create the global trading metrics instance.

    Args:
        config: Optional trading metrics configuration

    Returns:
        Global TradingMetrics instance
    """
    global _trading_metrics
    if _trading_metrics is None:
        _trading_metrics = TradingMetrics(config)
    return _trading_metrics


def track_glm_api_call(model: str = "glm-4") -> Callable[[F], F]:
    """Decorator to track GLM API call metrics.

    Args:
        model: GLM model name (default: glm-4)

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            metrics = get_trading_metrics()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Estimate tokens if not provided
                # In production, this would extract actual token count from response
                duration = time.time() - start_time
                estimated_tokens = int(duration * 100)  # Rough estimate
                metrics.increment_glm_tokens(tokens=estimated_tokens, model=model)

                return result

            except Exception as e:
                logger.error(f"GLM API call failed: {e}")
                raise

        return wrapper  # type: ignore

    return decorator


def track_upbit_api_call(endpoint: str, method: str = "GET") -> Callable[[F], F]:
    """Decorator to track Upbit API call metrics.

    Args:
        endpoint: API endpoint path
        method: HTTP method (default: GET)

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            metrics = get_trading_metrics()

            try:
                result = func(*args, **kwargs)
                metrics.increment_upbit_requests(
                    endpoint=endpoint,
                    method=method,
                    status="200",
                )
                return result

            except Exception as e:
                metrics.increment_upbit_requests(
                    endpoint=endpoint,
                    method=method,
                    status="500",
                )
                logger.error(f"Upbit API call failed: {e}")
                raise

        return wrapper  # type: ignore

    return decorator


def track_trading_decision(decision: str) -> Callable[[F], F]:
    """Decorator to track trading decision duration.

    Args:
        decision: Trading decision (buy, sell, hold)

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            metrics = get_trading_metrics()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                metrics.observe_trading_decision_duration(
                    duration_seconds=duration,
                    decision=decision,
                )

                return result

            except Exception as e:
                logger.error(f"Trading decision failed: {e}")
                raise

        return wrapper  # type: ignore

    return decorator


def update_portfolio_value(value_krw: float) -> None:
    """Update portfolio value metric.

    Args:
        value_krw: Portfolio value in KRW
    """
    metrics = get_trading_metrics()
    metrics.set_portfolio_value(value_krw=value_krw)


__all__ = [
    "TradingMetrics",
    "TradingMetricsConfig",
    "get_trading_metrics",
    "track_glm_api_call",
    "track_upbit_api_call",
    "track_trading_decision",
    "update_portfolio_value",
]
